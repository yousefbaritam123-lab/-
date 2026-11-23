"""Automated quality gates and delivery certification."""
from __future__ import annotations
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
from .models import read_json, validate_episode
from .continuity import validate_continuity

def audit_episode(project_dir: Path, sample_limit: int = 24) -> dict:
    errors, warnings = [], []
    try:
        episode = read_json(project_dir / "episode.json")
        errors.extend(validate_episode(project_dir))
        errors.extend(validate_continuity(project_dir, episode))
    except Exception as exc:
        episode = {}
        errors.append(f"Project validation error: {exc}")
    fmt = episode.get("format", {})
    fps = int(fmt.get("fps", 30))
    expected = int(round(float(fmt.get("duration_seconds", 0)) * fps))
    frames_dir = project_dir / "renders" / "frames"
    found = sorted(frames_dir.glob("frame_*.png")) if frames_dir.is_dir() else []
    missing = [n for n in range(expected) if not (frames_dir / f"frame_{n:06d}.png").is_file()]
    if expected <= 0:
        errors.append("Invalid expected frame count")
    if missing:
        errors.append(f"Incomplete render: {len(missing)} of {expected} frames missing")
    tiny = [p.name for p in found if p.stat().st_size < 128]
    if tiny:
        errors.append(f"{len(tiny)} empty or tiny frame files")
    corrupt = []
    stride = max(1, len(found) // max(1, sample_limit))
    for path in found[::stride][:sample_limit]:
        try:
            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:
                if im.size != (fmt.get("width"), fmt.get("height")):
                    errors.append(f"{path.name} has wrong dimensions {im.size}")
        except Exception as exc:
            corrupt.append(f"{path.name}: {exc}")
    if corrupt:
        errors.append(f"{len(corrupt)} sampled frames are corrupt")
    if found and len(found) != expected:
        warnings.append(f"Found {len(found)} frame files; expected {expected}")
    dialogue = [line for shot in episode.get("shots", []) for line in shot.get("dialogue", [])]
    dialogue_dir = project_dir / "audio" / "dialogue"
    audio_files = list(dialogue_dir.glob("*")) if dialogue_dir.is_dir() else []
    has_mix = (project_dir / "audio" / "final_mix.wav").is_file()
    if not has_mix and not audio_files:
        warnings.append("No audio supplied; export will be silent")
    if dialogue and not has_mix and not audio_files:
        warnings.append("Script contains dialogue but dialogue audio is missing")
    report = {
        "schema_version": 1,
        "episode_id": episode.get("id", project_dir.name),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else ("passed_with_warnings" if warnings else "passed"),
        "delivery_eligible": not errors,
        "summary": {"expected_frames": expected, "found_frames": len(found),
                    "missing_frames": len(missing), "corrupt_sampled_frames": len(corrupt),
                    "errors": len(errors), "warnings": len(warnings)},
        "errors": errors, "warnings": warnings,
        "checks": {"episode_and_continuity": "passed" if not errors else "review",
                   "frame_coverage": "passed" if expected and not missing and not tiny else "failed",
                   "sampled_image_integrity": "passed" if found and not corrupt else "failed",
                   "audio": "present" if has_mix or audio_files else "missing"}
    }
    out = project_dir / "production" / "quality_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report

def certify_delivery(project_dir: Path) -> Path:
    report = audit_episode(project_dir)
    if not report["delivery_eligible"]:
        raise RuntimeError("Delivery blocked. Review production/quality_report.json")
    from .media import encode_video
    episode = read_json(project_dir / "episode.json")
    output = encode_video(project_dir, int(episode["format"]["fps"]))
    if not output.is_file() or output.stat().st_size < 1024:
        raise RuntimeError("Encoded video missing or unexpectedly small")
    verification = "encoded file exists; ffprobe unavailable"
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        result = subprocess.run([ffprobe, "-v", "error", "-show_entries",
            "format=duration:stream=codec_name,width,height", "-of", "json", str(output)],
            capture_output=True, text=True)
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
    manifest = {"episode_id": episode["id"], "status": "delivered",
        "delivered_at": datetime.now(timezone.utc).isoformat(),
        "video": str(output.relative_to(project_dir)), "bytes": output.stat().st_size,
        "quality_report": "production/quality_report.json", "verification": verification}
    path = project_dir / "production" / "delivery_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output
