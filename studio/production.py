"""Iterative, gate-driven episode production.

This coordinator never equates a successful render command with a finished episode.
It verifies every frame, repairs render-integrity failures, records review rounds,
and blocks delivery when hard requirements remain unmet.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat

from .models import read_json, validate_episode
from .continuity import validate_continuity
from .renderer import render_episode_frames
from .quality import certify_delivery


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _frame_audit(project_dir: Path, episode: dict[str, Any]) -> dict[str, Any]:
    fmt = episode["format"]
    width, height = int(fmt["width"]), int(fmt["height"])
    fps = int(fmt["fps"])
    total = int(round(float(fmt["duration_seconds"]) * fps))
    folder = project_dir / "renders" / "frames"
    missing: list[int] = []
    corrupt: list[int] = []
    blank: list[int] = []
    wrong_size: list[int] = []
    hashes: dict[str, int] = {}
    brightness: list[float] = []
    started = time.monotonic()

    for number in range(total):
        path = folder / f"frame_{number:06d}.png"
        if not path.is_file() or path.stat().st_size < 256:
            missing.append(number)
            continue
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                image = image.convert("RGB")
                if image.size != (width, height):
                    wrong_size.append(number)
                    continue
                # Full-frame luminance/variance screen catches empty renders.
                stat = ImageStat.Stat(image.resize((96, 96)))
                mean = sum(stat.mean) / 3.0
                variance = sum(stat.stddev) / 3.0
                brightness.append(mean)
                if variance < 1.15 or mean < 1.0 or mean > 254.0:
                    blank.append(number)
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                hashes[digest] = hashes.get(digest, 0) + 1
        except Exception:
            corrupt.append(number)

    exact_duplicate_frames = sum(count - 1 for count in hashes.values() if count > 1)
    return {
        "expected_frames": total,
        "verified_frames": total - len(missing) - len(corrupt) - len(wrong_size),
        "missing": missing,
        "corrupt": corrupt,
        "wrong_dimensions": wrong_size,
        "blank_or_near_blank": blank,
        "exact_duplicate_frames": exact_duplicate_frames,
        "brightness_min": round(min(brightness), 2) if brightness else None,
        "brightness_max": round(max(brightness), 2) if brightness else None,
        "scan_seconds": round(time.monotonic() - started, 2),
    }


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")


def run_production(project_dir: Path, *, max_repair_rounds: int = 3) -> dict[str, Any]:
    """Render, inspect every frame, repair technical defects, and gate delivery."""
    if max_repair_rounds < 1 or max_repair_rounds > 10:
        raise ValueError("max_repair_rounds must be between 1 and 10")
    project_dir = Path(project_dir)
    started = time.monotonic()
    episode = read_json(project_dir / "episode.json")
    errors = validate_episode(project_dir) + validate_continuity(project_dir, episode)
    if errors:
        report = {"status": "blocked", "phase": "preflight", "errors": errors, "rounds": []}
        _write_json(project_dir / "production" / "production_run.json", report)
        return report

    fmt = episode["format"]
    total = int(round(float(fmt["duration_seconds"]) * int(fmt["fps"])))
    rounds: list[dict[str, Any]] = []
    final_audit: dict[str, Any] = {}

    for round_no in range(1, max_repair_rounds + 1):
        render_start = time.monotonic()
        folder, rendered = render_episode_frames(project_dir, 0, total, resume=True)
        render_seconds = round(time.monotonic() - render_start, 2)
        final_audit = _frame_audit(project_dir, episode)
        defects = sorted(set(final_audit["missing"] + final_audit["corrupt"] +
                             final_audit["wrong_dimensions"] + final_audit["blank_or_near_blank"]))
        rounds.append({
            "round": round_no,
            "rendered_frames": rendered,
            "render_seconds": render_seconds,
            "audit": final_audit,
            "repair_candidates": defects,
            "status": "passed" if not defects else "repair_required",
        })
        if not defects:
            break
        # Remove only failed frames. The next resumable render regenerates those frames.
        for number in defects:
            path = folder / f"frame_{number:06d}.png"
            if path.exists():
                path.unlink()

    hard_errors: list[str] = []
    if final_audit.get("missing") or final_audit.get("corrupt") or final_audit.get("wrong_dimensions") or final_audit.get("blank_or_near_blank"):
        hard_errors.append("Frame integrity defects remain after repair rounds")
    if final_audit.get("verified_frames") != total:
        hard_errors.append("Not every expected frame passed full-frame integrity verification")

    dialogue = [line for shot in episode.get("shots", []) for line in shot.get("dialogue", [])]
    final_mix = project_dir / "audio" / "final_mix.wav"
    if dialogue and not final_mix.is_file():
        hard_errors.append("Dialogue exists in the script but audio/final_mix.wav is missing")
    if not dialogue and not final_mix.is_file():
        hard_errors.append("Final audio mix is missing")

    # A deterministic engine cannot judge acting, anatomy, continuity aesthetics,
    # Arabic performance, or whether a joke/emotion lands. A human visual sign-off
    # is therefore mandatory; it cannot be auto-forged by this pipeline.
    review_path = project_dir / "production" / "human_visual_approval.json"
    approval = None
    if review_path.is_file():
        try:
            approval = json.loads(review_path.read_text(encoding="utf-8"))
        except Exception:
            approval = None
    approved = bool(approval and approval.get("approved") is True and
                    approval.get("episode_id") == episode.get("id") and
                    isinstance(approval.get("reviewer"), str) and approval["reviewer"].strip() and
                    isinstance(approval.get("notes"), str) and approval["notes"].strip())
    if not approved:
        hard_errors.append("Human visual review is not approved; create production/human_visual_approval.json after inspecting the contact sheet")

    status = "ready_for_delivery" if not hard_errors else "blocked"
    report = {
        "schema_version": 1,
        "episode_id": episode.get("id"),
        "started_at": _stamp(),
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "status": status,
        "delivery_allowed": not hard_errors,
        "quality_policy": {
            "all_frames_must_decode": True,
            "all_frames_must_match_dimensions": True,
            "no_blank_frames": True,
            "scripted_dialogue_requires_final_mix": True,
            "human_visual_signoff_required": True,
            "automatic_artistic_perfection_claimed": False,
        },
        "rounds": rounds,
        "final_frame_audit": final_audit,
        "errors": hard_errors,
        "next_action": "Run studio finalize only after visual approval and all hard gates pass.",
    }
    _write_json(project_dir / "production" / "production_run.json", report)
    if not hard_errors:
        try:
            output = certify_delivery(project_dir)
            report["status"] = "delivered"
            report["delivery_allowed"] = True
            report["video"] = str(output.relative_to(project_dir))
        except Exception as exc:
            report["status"] = "blocked"
            report["delivery_allowed"] = False
            report["errors"].append(f"Encoding/final verification failed: {exc}")
        _write_json(project_dir / "production" / "production_run.json", report)
    return report
