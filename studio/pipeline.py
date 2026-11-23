"""Production department planner. This creates a traceable work order; it does not fake a render."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

DEPARTMENTS = [
    ("story_editor", "Story editor", "Check hook, conflict, payoff and previous-episode continuity."),
    ("screenwriter", "Screenwriter", "Check Algerian Arabic dialogue, speaker IDs and line timing."),
    ("director", "Director", "Check shot order, staging, screen direction and shot durations."),
    ("character", "Character department", "Resolve canonical character rigs, wardrobe and expression assets."),
    ("layout", "Background and layout", "Resolve locations, props, layers and lighting references."),
    ("animation", "Animation department", "Prepare body acting, gestures, locomotion, anticipation and follow-through."),
    ("camera", "Camera department", "Check framing, camera moves, cuts and vertical safe areas."),
    ("sound", "Sound department", "Resolve dialogue, ambience, Foley and licensed audio assets."),
    ("editorial", "Editorial", "Assemble shots, transitions, mix and encode the episode."),
    ("quality", "Quality control", "Validate continuity, missing assets, timing, audio and final media."),
]


def build_production_plan(project_dir: Path) -> Path:
    episode = json.loads((project_dir / "episode.json").read_text(encoding="utf-8"))
    tasks = []
    for order, (key, name, brief) in enumerate(DEPARTMENTS, start=1):
        tasks.append({
            "order": order,
            "department": key,
            "name": name,
            "status": "blocked",
            "brief": brief,
            "input": "episode.json + continuity.json + assets/",
            "output": f"production/{order:02d}_{key}.json",
        })
    plan = {
        "schema_version": 1,
        "episode_id": episode["id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "planning_only",
        "note": "Tasks are work orders, not proof that animation or rendering has completed.",
        "tasks": tasks,
    }
    out_dir = project_dir / "production"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "production_plan.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out
