"""Explicit, validated continuity ledger for a serialized Stickman series.

No story facts are inferred here. Episode changes are applied only from an
explicit state_update object supplied by the writer/director pipeline.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LEDGER_NAME = "continuity.json"


def load_continuity(project_dir: Path) -> dict[str, Any]:
    path = project_dir / LEDGER_NAME
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Missing continuity ledger: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid continuity JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("Continuity ledger must be a JSON object")
    return data


def validate_continuity(project_dir: Path, episode: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    try:
        ledger = load_continuity(project_dir)
    except ValueError as exc:
        return [str(exc)]

    if ledger.get("schema_version") != 1:
        errors.append("continuity.schema_version must be 1")
    if not isinstance(ledger.get("series_id"), str) or not ledger["series_id"].strip():
        errors.append("continuity.series_id must be a non-empty string")
    number = ledger.get("episode_number")
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        errors.append("continuity.episode_number must be a positive integer")

    character_state = ledger.get("character_state")
    if not isinstance(character_state, dict):
        errors.append("continuity.character_state must be an object")
        character_state = {}
    for char_id, state in character_state.items():
        if not isinstance(char_id, str) or not char_id:
            errors.append("continuity character IDs must be non-empty strings")
        if not isinstance(state, dict):
            errors.append(f"continuity.character_state.{char_id} must be an object")
            continue
        if "wardrobe" in state and (not isinstance(state["wardrobe"], str) or not state["wardrobe"].strip()):
            errors.append(f"continuity.character_state.{char_id}.wardrobe must be a non-empty string")
        if "personality" in state and (
            not isinstance(state["personality"], list)
            or any(not isinstance(item, str) or not item.strip() for item in state["personality"])
        ):
            errors.append(f"continuity.character_state.{char_id}.personality must be an array of non-empty strings")
        if "known_facts" in state and not isinstance(state["known_facts"], list):
            errors.append(f"continuity.character_state.{char_id}.known_facts must be an array")

    for key in ("world_state", "unresolved_threads"):
        if not isinstance(ledger.get(key), list):
            errors.append(f"continuity.{key} must be an array")

    if episode is not None:
        episode_ids = {c.get("id") for c in episode.get("characters", []) if isinstance(c, dict)}
        unknown = sorted(set(character_state) - episode_ids)
        if unknown:
            errors.append("Continuity contains unknown character IDs: " + ", ".join(unknown))
        missing = sorted(episode_ids - set(character_state))
        if missing:
            errors.append("Continuity is missing character IDs: " + ", ".join(missing))
    return errors


def apply_episode_update(
    project_dir: Path,
    episode: dict[str, Any],
    state_update: dict[str, Any],
    *,
    expected_episode_number: int,
) -> Path:
    """Apply an explicit episode-end state patch and advance the ledger once."""
    errors = validate_continuity(project_dir, episode)
    if errors:
        raise ValueError("Cannot update invalid continuity: " + "; ".join(errors))
    if not isinstance(state_update, dict):
        raise ValueError("state_update must be an object")

    ledger = load_continuity(project_dir)
    current = ledger["episode_number"]
    if current != expected_episode_number:
        raise ValueError(f"Continuity conflict: expected episode {expected_episode_number}, found {current}")

    allowed = {"character_state", "world_state", "unresolved_threads"}
    unknown = set(state_update) - allowed
    if unknown:
        raise ValueError("Unsupported state_update keys: " + ", ".join(sorted(unknown)))

    patch_chars = state_update.get("character_state", {})
    if not isinstance(patch_chars, dict):
        raise ValueError("state_update.character_state must be an object")
    known_ids = {c["id"] for c in episode.get("characters", [])}
    for char_id, patch in patch_chars.items():
        if char_id not in known_ids:
            raise ValueError(f"Cannot update unknown character: {char_id}")
        if not isinstance(patch, dict):
            raise ValueError(f"Character update for {char_id} must be an object")
        ledger["character_state"].setdefault(char_id, {}).update(patch)

    for key in ("world_state", "unresolved_threads"):
        if key in state_update:
            if not isinstance(state_update[key], list):
                raise ValueError(f"state_update.{key} must be an array")
            ledger[key] = state_update[key]

    ledger["previous_episode"] = episode.get("id")
    ledger["episode_number"] = current + 1
    path = project_dir / LEDGER_NAME
    path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
