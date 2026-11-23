"""Episode-facing helpers for the built-in 60-character cast."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .characters import load_character_catalog


def _catalog(project_dir: Path) -> dict[str, Any]:
    path = project_dir / "assets" / "characters" / "cast_60" / "catalog.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing 60-character catalog: {path}. Run studio init first.")
    return load_character_catalog(path)


def list_cast_profiles(project_dir: Path) -> list[dict[str, Any]]:
    """Return all 60 validated profiles in their stable catalog order."""
    return list(_catalog(project_dir)["characters"])


def add_cast_character(project_dir: Path, cast_id: str, *, shot_id: str = 'shot-001',
                       actor_id: str | None = None, x: float = 700, y: float = 1450,
                       action: str = 'idle') -> dict[str, Any]:
    """Add one catalog profile to episode.json and the requested shot."""
    catalog = _catalog(project_dir)
    profile = next((item for item in catalog["characters"] if item["id"] == cast_id), None)
    if profile is None:
        raise KeyError(f"Unknown cast character {cast_id!r}. Run studio cast-list to see valid IDs.")

    episode_path = project_dir / "episode.json"
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    shot = next((item for item in episode.get("shots", []) if item.get("id") == shot_id), None)
    if shot is None:
        raise KeyError(f"Unknown shot {shot_id!r} in {episode_path}")

    resolved_actor_id = actor_id or cast_id
    if any(item.get("id") == resolved_actor_id for item in episode.get("characters", [])):
        raise ValueError(f"Episode already contains character id {resolved_actor_id!r}")
    actor = {
        "id": resolved_actor_id,
        "name": profile.get("display_name", resolved_actor_id),
        "cast_id": cast_id,
        "rig": profile.get("rig", catalog.get("shared_rig")),
        "appearance": dict(profile.get("appearance", {})),
        "proportions": dict(profile.get("proportions", {})),
        "x": float(x),
        "y": float(y),
        "action": action,
    }
    episode.setdefault("characters", []).append(actor)
    shot.setdefault("actors", []).append(resolved_actor_id)
    episode_path.write_text(json.dumps(episode, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return actor
