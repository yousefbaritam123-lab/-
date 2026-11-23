"""Assemble a director storyboard into an isolated, renderable animatic project.

The source episode is never overwritten. The assembled project receives its own
episode.json, continuity ledger, and copies of the assets/audio it needs.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .continuity import validate_continuity
from .models import validate_episode


def assemble_storyboard(project_dir: Path, storyboard_path: Path | None = None) -> Path:
    source_episode_path = project_dir / "episode.json"
    if not source_episode_path.is_file():
        raise FileNotFoundError(f"Missing source episode: {source_episode_path}")
    source: dict[str, Any] = json.loads(source_episode_path.read_text(encoding="utf-8"))

    if storyboard_path is None:
        candidates = sorted((project_dir / "production" / "story").glob("episode-*-storyboard.json"))
        if not candidates:
            raise FileNotFoundError("No storyboard found. Run 'story-next' then 'storyboard'.")
        storyboard_path = candidates[-1]
    storyboard: dict[str, Any] = json.loads(storyboard_path.read_text(encoding="utf-8"))

    if storyboard.get("status") not in (
        "director_blocking_pass_needs_screenwriter_and_director_review",
        "approved_for_animatic",
    ):
        raise ValueError("Storyboard status is not recognized; refusing to assemble it.")
    shots = storyboard.get("shots")
    if not isinstance(shots, list) or not shots:
        raise ValueError("Storyboard must contain at least one shot.")

    episode = dict(source)
    episode["shots"] = []
    for index, item in enumerate(shots, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Storyboard shot {index} must be an object.")
        episode["shots"].append({
            "id": item.get("id") or f"shot-{index:03d}",
            "duration_seconds": item.get("duration_seconds"),
            "location": item.get("location"),
            "actors": list(item.get("actors", [])),
            "action": item.get("action", "idle"),
            "camera": dict(item.get("camera", {})),
            "motion_tracks": dict(item.get("motion_tracks", {})),
            "dialogue": list(item.get("dialogue", [])),
            "editorial_notes": item.get("editorial_notes", ""),
            "beat_id": item.get("beat_id"),
            "beat_type": item.get("beat_type"),
        })

    episode["production"] = {
        "stage": "assembled_animatic_draft",
        "storyboard": str(storyboard_path),
        "dialogue_complete": all(bool(shot["dialogue"]) for shot in episode["shots"]),
        "approval_required": True,
        "note": "This is a renderable blocking animatic, not a finished episode. Review dialogue, staging, assets and continuity before publication.",
    }

    output_root = project_dir / "production" / "assembled"
    output_root.mkdir(parents=True, exist_ok=True)
    safe_id = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in str(episode["id"]))
    output_dir = output_root / f"{safe_id}-animatic"
    if output_dir.exists():
        raise FileExistsError(
            f"Assembly already exists: {output_dir}. Move or rename it before creating a fresh assembly; existing work was not overwritten."
        )
    output_dir.mkdir(parents=True)

    try:
        (output_dir / "episode.json").write_text(
            json.dumps(episode, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        continuity = project_dir / "continuity.json"
        if continuity.is_file():
            shutil.copy2(continuity, output_dir / "continuity.json")
        assets = project_dir / "assets"
        if assets.is_dir():
            shutil.copytree(assets, output_dir / "assets", dirs_exist_ok=True)
        audio = project_dir / "audio"
        if audio.is_dir():
            shutil.copytree(audio, output_dir / "audio", dirs_exist_ok=True)

        errors = validate_episode(output_dir)
        if (output_dir / "continuity.json").is_file():
            errors.extend(validate_continuity(output_dir, episode))
        if errors:
            raise ValueError("Assembled episode failed validation:\n- " + "\n- ".join(errors))
    except Exception:
        shutil.rmtree(output_dir, ignore_errors=True)
        raise
    return output_dir
