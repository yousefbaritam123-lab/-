"""Command line for the Python production manager."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .models import validate_episode
from .pipeline import build_production_plan

TEMPLATE = {
    "id": "episode-001",
    "title": "الحلقة التجريبية",
    "language": "ar-DZ",
    "format": {"width": 1080, "height": 1920, "fps": 30, "duration_seconds": 100},
    "characters": [
        {"id": "youssef", "name": "يوسف", "rig": "assets/characters/youssef/character.toon.json"},
        {"id": "friend", "name": "الصديق", "rig": "assets/characters/friend/character.toon.json"}
    ],
    "locations": [{"id": "street_01", "name": "شارع الحي", "asset": "assets/locations/street_01"}],
    "shots": [
        {"id": "shot-001", "duration_seconds": 25, "location": "street_01", "actors": ["youssef"], "dialogue": []},
        {"id": "shot-002", "duration_seconds": 25, "location": "street_01", "actors": ["youssef", "friend"], "dialogue": []},
        {"id": "shot-003", "duration_seconds": 25, "location": "street_01", "actors": ["youssef", "friend"], "dialogue": []},
        {"id": "shot-004", "duration_seconds": 25, "location": "street_01", "actors": ["youssef"], "dialogue": []}
    ]
}


def init_project(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for folder in ("assets/characters", "assets/locations", "audio/dialogue", "audio/fx", "renders", "production", "continuity"):
        (path / folder).mkdir(parents=True, exist_ok=True)
    episode_file = path / "episode.json"
    if not episode_file.exists():
        episode_file.write_text(json.dumps(TEMPLATE, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    continuity_file = path / "continuity.json"
    if not continuity_file.exists():
        continuity_file.write_text(json.dumps({
            "schema_version": 1,
            "series_id": "youssef-daily-life",
            "episode_number": 1,
            "previous_episode": None,
            "character_state": {
                "youssef": {"wardrobe": "default", "personality": ["curious", "stubborn"], "known_facts": []},
                "friend": {"wardrobe": "default", "personality": ["loyal"], "known_facts": []}
            },
            "world_state": [],
            "unresolved_threads": []
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Project initialized: {path.resolve()}")


def doctor() -> int:
    checks = {
        "Python 3.10+": sys.version_info >= (3, 10),
        "Node.js": shutil.which("node") is not None,
        "pnpm": shutil.which("pnpm") is not None,
        "FFmpeg": shutil.which("ffmpeg") is not None,
        "Rhubarb (optional lip-sync)": shutil.which("rhubarb") is not None,
    }
    for label, ok in checks.items():
        suffix = "OK" if ok else ("OPTIONAL / NOT FOUND" if "optional" in label else "NOT FOUND")
        print(f"[{suffix}] {label}")
    return 0 if checks["Python 3.10+"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="studio", description="Stickman Studio Pro production manager")
    sub = parser.add_subparsers(dest="command", required=True)
    init_cmd = sub.add_parser("init", help="create a new episode project")
    init_cmd.add_argument("project", type=Path)
    for name in ("validate", "plan"):
        cmd = sub.add_parser(name)
        cmd.add_argument("project", type=Path)
    sub.add_parser("doctor", help="check local production tools")
    args = parser.parse_args(argv)

    if args.command == "init":
        init_project(args.project)
        return 0
    if args.command == "doctor":
        return doctor()
    if args.command == "validate":
        errors = validate_episode(args.project)
        if errors:
            print("EPISODE VALIDATION FAILED")
            for error in errors:
                print(f"- {error}")
            return 1
        print("EPISODE STRUCTURE VALID")
        return 0
    if args.command == "plan":
        errors = validate_episode(args.project)
        if errors:
            print("Cannot create plan; fix validation errors first:")
            for error in errors:
                print(f"- {error}")
            return 1
        print(f"Production plan created: {build_production_plan(args.project)}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
