"""Load reusable procedural character profiles from the cast catalog."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_character_catalog(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    characters = data.get("characters", [])
    ids = [item.get("id") for item in characters]
    if len(characters) != 60 or len(set(ids)) != 60:
        raise ValueError("The cast catalog must contain exactly 60 unique character IDs")
    return data


def make_episode_character(
    catalog_path: Path,
    character_id: str,
    *,
    x: float = 540,
    y: float = 1450,
    action: str = "idle",
) -> dict[str, Any]:
    """Return an episode-ready actor record using the shared canonical rig path."""
    catalog = load_character_catalog(catalog_path)
    profile = next((item for item in catalog["characters"] if item["id"] == character_id), None)
    if profile is None:
        raise KeyError(f"Unknown cast character: {character_id}")
    return {
        "id": profile["id"],
        "rig": profile.get("rig", catalog["shared_rig"]),
        "appearance": dict(profile.get("appearance", {})),
        "proportions": dict(profile.get("proportions", {})),
        "x": x,
        "y": y,
        "action": action,
    }
