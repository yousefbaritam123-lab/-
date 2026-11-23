"""Deterministic serial-story beat planner; dialogue and director approval remain explicit."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

BEATS = [
 ("cold_open",8,"Open on a visual question or consequence carried from the previous episode."),
 ("setup",12,"Establish the day's ordinary goal and location."),
 ("inciting_incident",12,"Introduce a new problem connected to a character or world fact."),
 ("reaction",12,"Show distinct character reactions and a clear choice."),
 ("escalation",18,"Complicate the plan; use visual action rather than exposition alone."),
 ("turning_point",14,"Reveal a useful fact or force a meaningful decision."),
 ("payoff",14,"Resolve the immediate problem while preserving a consequence."),
 ("cliffhanger",10,"Plant one specific unresolved question for the next episode.")
]

def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value

def build_next_episode_outline(project_dir: Path, *, episode_title: str | None = None) -> Path:
    episode = _load(project_dir / "episode.json")
    continuity = _load(project_dir / "continuity.json")
    number = int(continuity.get("episode_number", 1))
    unresolved = continuity.get("unresolved_threads", [])
    world, chars = continuity.get("world_state", []), continuity.get("character_state", {})
    if not isinstance(unresolved, list) or not isinstance(world, list) or not isinstance(chars, dict):
        raise ValueError("Continuity ledger has invalid story-state fields")
    seed = unresolved[0] if unresolved else "Introduce an everyday problem that tests the protagonist's established personality."
    ids = [c["id"] for c in episode.get("characters", []) if isinstance(c, dict) and c.get("id")]
    beats = [{"id": f"ep{number:03d}_{key}", "type": key, "duration_seconds": seconds,
              "writer_instruction": instruction,
              "continuity_seed": seed if key in ("cold_open","inciting_incident","cliffhanger") else None,
              "dialogue_draft": [], "characters": ids}
             for key, seconds, instruction in BEATS]
    outline = {
      "schema_version":1, "series_id":continuity.get("series_id"), "episode_number":number,
      "episode_id":f"episode-{number:03d}", "title":episode_title or f"حلقة {number}",
      "language":episode.get("language","ar-DZ"), "target_duration_seconds":100,
      "previous_episode":continuity.get("previous_episode"),
      "continuity_snapshot":{"character_state":chars,"world_state":world,"unresolved_threads":unresolved},
      "central_thread":seed, "beats":beats,
      "writer_room_status":"outline_requires_dialogue_and_director_review",
      "next_episode_rule":"Advance continuity only after the rendered episode is approved."
    }
    folder=project_dir/"production"/"story"
    folder.mkdir(parents=True,exist_ok=True)
    output=folder/f"episode-{number:03d}-outline.json"
    output.write_text(json.dumps(outline,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return output
