"""Strict engineering and delivery gates for rendered episodes.

A technically valid MP4 is not automatically an approved episode. Every expected
frame is decoded and checked; final delivery additionally requires a real audio mix
and an explicit human visual sign-off.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import wave
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageStat

from .models import read_json, validate_episode
from .continuity import validate_continuity


def _read_approval(project_dir: Path, episode_id: str) -> tuple[bool, str]:
    path = project_dir / "production" / "human_visual_approval.json"
    if not path.is_file():
        return False, "Human visual approval file is missing"
    try:
        approval = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"Human visual approval file is invalid: {exc}"
    valid = (
        approval.get("approved") is True
        and approval.get("episode_id") == episode_id
        and isinstance(approval.get("reviewer"), str)
        and bool(approval["reviewer"].strip())
        and isinstance(approval.get("notes"), str)
        and bool(approval["notes"].strip())
    )
    return (True, "") if valid else (False, "Human visual approval does not match this episode or lacks reviewer notes")


def inspect_audio_mix(path: Path, expected_duration: float) -> tuple[bool, str]:
    """Validate the final PCM WAV structurally and against the episode duration."""
    if not path.is_file():
        return False, "Final audio mix is missing"
    try:
        with wave.open(str(path), "rb") as audio:
            channels = audio.getnchannels()
            sample_rate = audio.getframerate()
            sample_width = audio.getsampwidth()
            frames = audio.getnframes()
            duration = frames / float(sample_rate) if sample_rate else 0.0
            payload = audio.readframes(frames)
        if channels != 2:
            return False, f"Final audio must be stereo; found {channels} channel(s)"
        if sample_rate != 48000:
            return False, f"Final audio must be 48000 Hz; found {sample_rate} Hz"
        if sample_width != 3:
            return False, f"Final audio must be 24-bit PCM; found {sample_width * 8}-bit"
        if frames <= 0 or len(payload) != frames * channels * sample_width:
            return False, "Final audio WAV is empty or truncated"
        tolerance = max(0.15, 2.0 / 30.0)
        if abs(duration - float(expected_duration)) > tolerance:
            return False, (
                f"Final audio duration mismatch: {duration:.3f}s; "
                f"expected {float(expected_duration):.3f}s"
            )
        return True, ""
    except (OSError, EOFError, wave.Error) as exc:
        return False, f"Final audio WAV cannot be decoded: {exc}"


def audit_episode(project_dir: Path, sample_limit: int = 24) -> dict:
    """Decode and validate every expected frame, not a sparse sample."""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        episode = read_json(project_dir / "episode.json")
        errors.extend(validate_episode(project_dir))
        errors.extend(validate_continuity(project_dir, episode))
    except Exception as exc:
        episode = {}
        errors.append(f"Project validation error: {exc}")

    try:
        from .script_qc import audit_dialogue
        script_report = audit_dialogue(project_dir)
        errors.extend(script_report.get("errors", []))
        warnings.extend(script_report.get("warnings", []))
    except Exception as exc:
        script_report = {"status": "failed", "errors": [str(exc)]}
        errors.append(f"Script QA failed: {exc}")

    fmt = episode.get("format", {})
    try:
        width, height = int(fmt["width"]), int(fmt["height"])
        fps = int(fmt["fps"])
        expected = int(round(float(fmt["duration_seconds"]) * fps))
    except (KeyError, TypeError, ValueError):
        width = height = fps = expected = 0
        errors.append("Invalid or incomplete video format settings")

    frames_dir = project_dir / "renders" / "frames"
    missing: list[int] = []
    corrupt: list[str] = []
    wrong_size: list[str] = []
    tiny: list[str] = []
    blank: list[str] = []
    exact_hashes: dict[str, int] = {}
    brightness: list[float] = []

    if expected <= 0:
        errors.append("Invalid expected frame count")
    else:
        for number in range(expected):
            path = frames_dir / f"frame_{number:06d}.png"
            if not path.is_file():
                missing.append(number)
                continue
            try:
                if path.stat().st_size < 128:
                    tiny.append(path.name)
                    continue
                with Image.open(path) as image:
                    image.verify()
                with Image.open(path) as image:
                    image = image.convert("RGB")
                    if image.size != (width, height):
                        wrong_size.append(f"{path.name}: {image.size}")
                        continue
                    stats = ImageStat.Stat(image.resize((96, 96)))
                    mean = sum(stats.mean) / 3.0
                    variance = sum(stats.stddev) / 3.0
                    brightness.append(mean)
                    if variance < 1.15 or mean < 1.0 or mean > 254.0:
                        blank.append(path.name)
                import hashlib
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                exact_hashes[digest] = exact_hashes.get(digest, 0) + 1
            except Exception as exc:
                corrupt.append(f"{path.name}: {exc}")

    duplicates = sum(count - 1 for count in exact_hashes.values() if count > 1)
    if missing:
        errors.append(f"Incomplete render: {len(missing)} of {expected} frames missing")
    if tiny:
        errors.append(f"{len(tiny)} frame files are empty or too small")
    if corrupt:
        errors.append(f"{len(corrupt)} expected frames cannot be decoded")
    if wrong_size:
        errors.append(f"{len(wrong_size)} expected frames have incorrect dimensions")
    if blank:
        errors.append(f"{len(blank)} expected frames are blank or near-blank")
    if duplicates:
        warnings.append(f"{duplicates} exact duplicate frame(s) detected; review possible frozen motion")

    dialogue = [line for shot in episode.get("shots", []) for line in shot.get("dialogue", [])]
    dialogue_dir = project_dir / "audio" / "dialogue"
    audio_files = [p for p in dialogue_dir.glob("*") if p.is_file()] if dialogue_dir.is_dir() else []
    mix_path = project_dir / "audio" / "final_mix.wav"
    has_mix = mix_path.is_file()
    audio_ok = False
    if has_mix:
        audio_ok, audio_error = inspect_audio_mix(
            mix_path, float(fmt.get("duration_seconds", 0.0))
        )
        if not audio_ok:
            errors.append(audio_error)
    elif dialogue:
        errors.append("Script contains dialogue but audio/final_mix.wav is missing")
    else:
        warnings.append("No final audio mix supplied; delivery will be blocked until one is added")

    approval_ok, approval_message = _read_approval(project_dir, str(episode.get("id", "")))
    if not approval_ok:
        warnings.append(approval_message + "; delivery is not approved")

    report = {
        "schema_version": 2,
        "episode_id": episode.get("id", project_dir.name),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else ("passed_with_warnings" if warnings else "passed"),
        "delivery_eligible": not errors and has_mix and audio_ok and approval_ok,
        "summary": {
            "expected_frames": expected,
            "verified_frames": expected - len(missing) - len(tiny) - len(corrupt) - len(wrong_size) - len(blank),
            "missing_frames": len(missing),
            "tiny_frames": len(tiny),
            "corrupt_frames": len(corrupt),
            "wrong_dimension_frames": len(wrong_size),
            "blank_frames": len(blank),
            "exact_duplicate_frames": duplicates,
            "errors": len(errors),
            "warnings": len(warnings),
        },
        "errors": errors,
        "warnings": warnings,
        "checks": {
            "episode_and_continuity": "passed" if not errors else "review",
            "all_frame_integrity": "passed" if expected and not (missing or tiny or corrupt or wrong_size or blank) else "failed",
            "audio": "passed" if audio_ok else ("invalid" if has_mix else "missing"),
            "human_visual_approval": "approved" if approval_ok else "missing_or_invalid",
            "script_qa": script_report.get("status", "not_run"),
        },
    }
    out = project_dir / "production" / "quality_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def certify_delivery(project_dir: Path) -> Path:
    """Encode only after every frame, audio, and human-review gate passes."""
    report = audit_episode(project_dir)
    if not report["delivery_eligible"]:
        reasons = report["errors"] + report["warnings"]
        raise RuntimeError("Delivery blocked: " + "; ".join(reasons))
    from .media import encode_video

    episode = read_json(project_dir / "episode.json")
    output = encode_video(project_dir, int(episode["format"]["fps"]))
    if not output.is_file() or output.stat().st_size < 1024:
        raise RuntimeError("Encoded video missing or unexpectedly small")

    verification = "encoded file exists; ffprobe unavailable"
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries",
             "format=duration:stream=codec_name,width,height", "-of", "json", str(output)],
            capture_output=True, text=True,
        )
        if result.returncode:
            raise RuntimeError("MP4 verification failed: " + result.stderr[-1000:])
        data = json.loads(result.stdout)
        streams = [s for s in data.get("streams", []) if s.get("codec_name") == "h264"]
        if not streams:
            raise RuntimeError("Final video has no H.264 stream")
        stream = streams[0]
        if (stream.get("width"), stream.get("height")) != (episode["format"]["width"], episode["format"]["height"]):
            raise RuntimeError("Final video dimensions do not match episode settings")
        actual = float(data.get("format", {}).get("duration", 0))
        expected = float(episode["format"]["duration_seconds"])
        if abs(actual - expected) > 0.15:
            raise RuntimeError(f"Video duration mismatch: {actual:.3f}s vs {expected:.3f}s")
        verification = "H.264, dimensions and duration verified"

    manifest = {
        "episode_id": episode["id"],
        "status": "delivered",
        "delivered_at": datetime.now(timezone.utc).isoformat(),
        "video": str(output.relative_to(project_dir)),
        "bytes": output.stat().st_size,
        "quality_report": "production/quality_report.json",
        "verification": verification,
        "human_visual_approval": "production/human_visual_approval.json",
    }
    path = project_dir / "production" / "delivery_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output
