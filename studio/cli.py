"""Command line for the Python production manager."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .models import validate_episode, read_json
from .continuity import validate_continuity
from .pipeline import build_production_plan

TEMPLATE = {
    "id": "episode-001",
    "title": "الحلقة التجريبية",
    "language": "ar-DZ",
    "format": {"width": 1080, "height": 1920, "fps": 30, "duration_seconds": 100},
    "characters": [
        {"id": "youssef", "name": "يوسف", "rig": "assets/characters/youssef/character.toon.json", "scarf": True, "accent": "#C62828"},
        {"id": "adam", "name": "آدم", "rig": "assets/characters/adam/character.toon.json", "accent": "#2878C8"}
    ],
    "locations": [{
        "id": "street_01", "name": "شارع الحي",
        "sky_top": "#78BCEB", "sky_bottom": "#F6D9B5",
        "hill": "#719C70", "ground": "#527B4F"
    }],
    "shots": [
        {"id": "shot-001", "duration_seconds": 25, "location": "street_01", "actors": ["youssef"], "action": "walk", "dialogue": []},
        {"id": "shot-002", "duration_seconds": 25, "location": "street_01", "actors": ["youssef", "adam"], "action": "wave", "positions": {"youssef": {"x": 380}, "adam": {"x": 760}}, "dialogue": []},
        {"id": "shot-003", "duration_seconds": 25, "location": "street_01", "actors": ["youssef", "adam"], "action": "talk", "camera": {"zoom": 1.08}, "dialogue": []},
        {"id": "shot-004", "duration_seconds": 25, "location": "street_01", "actors": ["youssef"], "action": "idle", "dialogue": []}
    ]
}


def init_project(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for folder in ("assets/characters", "assets/locations", "audio/dialogue", "audio/fx", "renders", "production", "continuity"):
        (path / folder).mkdir(parents=True, exist_ok=True)
    bundled_assets = Path(__file__).resolve().parent.parent / "assets"
    if bundled_assets.is_dir():
        shutil.copytree(bundled_assets, path / "assets", dirs_exist_ok=True)
    episode_file = path / "episode.json"
    if not episode_file.exists():
        episode_file.write_text(json.dumps(TEMPLATE, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    continuity_file = path / "continuity.json"
    if not continuity_file.exists():
        continuity_file.write_text(json.dumps({
            "schema_version": 1, "series_id": "youssef-daily-life",
            "episode_number": 1, "previous_episode": None,
            "character_state": {
                "youssef": {"wardrobe": "default", "personality": ["curious", "stubborn"], "known_facts": []},
                "adam": {"wardrobe": "default", "personality": ["loyal", "observant"], "known_facts": []}
            },
            "world_state": [], "unresolved_threads": []
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Project initialized: {path.resolve()}")


def doctor() -> int:
    checks = {
        "Python 3.10+": sys.version_info >= (3, 10),
        "Skia renderer": _module_available("skia"),
        "imageio-ffmpeg": _module_available("imageio_ffmpeg"),
        "Node.js": shutil.which("node") is not None,
        "pnpm": shutil.which("pnpm") is not None,
        "Rhubarb (optional lip-sync)": shutil.which("rhubarb") is not None,
    }
    for label, ok in checks.items():
        suffix = "OK" if ok else ("OPTIONAL / NOT FOUND" if "optional" in label else "NOT FOUND")
        print(f"[{suffix}] {label}")
    return 0 if checks["Python 3.10+"] else 1


def _module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def _validate(project: Path) -> bool:
    errors = validate_episode(project)
    try:
        episode = read_json(project / "episode.json")
        errors.extend(validate_continuity(project, episode))
    except ValueError as exc:
        errors.append(str(exc))
    if errors:
        print("EPISODE VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="studio", description="Stickman Studio Pro production manager and renderer")
    sub = parser.add_subparsers(dest="command", required=True)
    init_cmd = sub.add_parser("init", help="create a new episode project")
    init_cmd.add_argument("project", type=Path)
    for name in ("validate", "plan", "render", "encode"):
        cmd = sub.add_parser(name)
        cmd.add_argument("project", type=Path)
        if name == "render":
            cmd.add_argument("--frames", help="render frame range START:END (end excluded); default: remaining episode")
    sub.add_parser("doctor", help="check local production tools")
    args = parser.parse_args(argv)

    if args.command == "init":
        init_project(args.project)
        return 0
    if args.command == "doctor":
        return doctor()
    if args.command == "validate":
        return 0 if _validate(args.project) else 1
    if args.command == "plan":
        if not _validate(args.project):
            return 1
        print(f"Production plan created: {build_production_plan(args.project)}")
        return 0
    if args.command == "render":
        if not _validate(args.project):
            return 1
        start, count = 0, None
        if args.frames:
            try:
                left, right = args.frames.split(":", 1)
                start, end = int(left), int(right)
                if start < 0 or end <= start:
                    raise ValueError
                count = end - start
            except ValueError:
                parser.error("--frames must be a valid START:END range, e.g. 0:300")
        from .renderer import render_episode_frames
        folder, rendered = render_episode_frames(args.project, start, count)
        print(f"Rendered {rendered} frame(s) into {folder}")
        return 0
    if args.command == "encode":
        if not _validate(args.project):
            return 1
        from .media import encode_video
        episode = json.loads((args.project / "episode.json").read_text(encoding="utf-8"))
        output = encode_video(args.project, int(episode["format"]["fps"]))
        print(f"Video encoded: {output}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
