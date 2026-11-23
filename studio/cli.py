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
from .story import build_next_episode_outline
from .director import build_storyboard
from .assembly import assemble_storyboard
from .cast import add_cast_character, list_cast_profiles
from .quality import audit_episode, certify_delivery

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
            cmd.add_argument("--resume", action="store_true", help="skip already rendered non-empty frames")
    sub.add_parser("doctor", help="check local production tools")
    for name in ("qc", "finalize"):
        cmd = sub.add_parser(name, help="audit episode or certify final delivery")
        cmd.add_argument("project", type=Path, help="episode project directory")
    story_cmd = sub.add_parser("story-next", help="create the next serialized episode outline")
    story_cmd.add_argument("project", type=Path)
    story_cmd.add_argument("--title")
    storyboard_cmd = sub.add_parser("storyboard", help="turn the latest story outline into an editable 100-second shot plan")
    storyboard_cmd.add_argument("project", type=Path)
    storyboard_cmd.add_argument("--outline", type=Path)
    assemble_cmd = sub.add_parser("assemble", help="assemble storyboard and assets into an isolated renderable animatic project")
    assemble_cmd.add_argument("project", type=Path)
    assemble_cmd.add_argument("--storyboard", type=Path)
    image_cmd = sub.add_parser("prepare-character", help="remove image background and prepare a character manifest")
    image_cmd.add_argument("source", type=Path)
    image_cmd.add_argument("output", type=Path)
    image_cmd.add_argument("character_id")
    lip_cmd = sub.add_parser("lipsync", help="generate visemes from dialogue audio with Rhubarb")
    lip_cmd.add_argument("audio", type=Path)
    lip_cmd.add_argument("output", type=Path)
    lip_cmd.add_argument("--speaker", required=True)
    lip_cmd.add_argument("--episode", type=Path, help="optional episode.json to update in place")
    lip_cmd.add_argument("--shot-id", help="shot containing the speaker dialogue line")
    lip_cmd.add_argument("--dialog-file", type=Path)
    cast_list_cmd = sub.add_parser("cast-list", help="list all 60 built-in character profiles")
    cast_list_cmd.add_argument("project", type=Path)
    cast_add_cmd = sub.add_parser("cast-add", help="add a catalog character to an episode shot")
    cast_add_cmd.add_argument("project", type=Path)
    cast_add_cmd.add_argument("cast_id")
    cast_add_cmd.add_argument("--shot-id", default="shot-001")
    cast_add_cmd.add_argument("--actor-id")
    cast_add_cmd.add_argument("--x", type=float, default=700)
    cast_add_cmd.add_argument("--y", type=float, default=1450)
    cast_add_cmd.add_argument("--action", default="idle")
    production_cmd = sub.add_parser("production-run", help="iterative render, full-frame audit, repair and delivery gates")
    production_cmd.add_argument("project", type=Path)
    production_cmd.add_argument("--repair-rounds", type=int, default=3)
    approve_cmd = sub.add_parser("visual-approve", help="record explicit human visual review after inspecting the rendered episode")
    approve_cmd.add_argument("project", type=Path)
    approve_cmd.add_argument("--reviewer", required=True)
    approve_cmd.add_argument("--notes", required=True)
    blend_cmd = sub.add_parser("blender-render", help="build and open an optional Blender scene")
    blend_cmd.add_argument("project", type=Path)
    blend_cmd.add_argument("--blender", default="blender")
    args = parser.parse_args(argv)

    if args.command == "init":
        init_project(args.project)
        return 0
    if args.command == "doctor":
        return doctor()
    if args.command == "cast-list":
        for item in list_cast_profiles(args.project):
            print(f"{item['id']} | {item.get('display_name', item['id'])} | {item.get('role', 'character')}")
        return 0
    if args.command == "cast-add":
        actor = add_cast_character(
            args.project, args.cast_id, shot_id=args.shot_id,
            actor_id=args.actor_id, x=args.x, y=args.y, action=args.action,
        )
        print(f"Added {actor['id']} ({actor['cast_id']}) to {args.shot_id}")
        return 0
    if args.command == "validate":
        return 0 if _validate(args.project) else 1
    if args.command == "qc":
        report = audit_episode(args.project)
        print("QC " + report["status"] + ": " + str(report["summary"]))
        for error in report["errors"]:
            print("ERROR: " + error)
        for warning in report["warnings"]:
            print("WARNING: " + warning)
        print("Report: " + str(args.project / "production" / "quality_report.json"))
        return 0 if report["delivery_eligible"] else 1
    if args.command == "finalize":
        try:
            output = certify_delivery(args.project)
        except Exception as exc:
            print("DELIVERY BLOCKED: " + str(exc))
            return 1
        print("DELIVERED: " + str(output))
        return 0
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
        folder, rendered = render_episode_frames(args.project, start, count, resume=args.resume)
        print(f"Rendered {rendered} new frame(s) into {folder}")
        return 0
    if args.command == "encode":
        if not _validate(args.project):
            return 1
        from .media import encode_video
        episode = json.loads((args.project / "episode.json").read_text(encoding="utf-8"))
        output = encode_video(args.project, int(episode["format"]["fps"]))
        print(f"Video encoded: {output}")
        return 0
    if args.command == "story-next":
        output = build_next_episode_outline(args.project, episode_title=args.title)
        print(f"Story outline created: {output}")
        return 0
    if args.command == "storyboard":
        output = build_storyboard(args.project, args.outline)
        print(f"Editable storyboard created: {output}")
        return 0
    if args.command == "assemble":
        output = assemble_storyboard(args.project, args.storyboard)
        print(f"Isolated animatic project created: {output}")
        print("Next: run validate, render, then encode using this new project directory.")
        return 0
    if args.command == "prepare-character":
        from .image_character import prepare_character_image
        output = prepare_character_image(args.source, args.output, args.character_id)
        print(f"Character image manifest created: {output}")
        return 0
    if args.command == "lipsync":
        from .lipsync import generate_visemes, attach_visemes
        cues = generate_visemes(args.audio, args.output, speaker=args.speaker, dialog_file=args.dialog_file)
        if args.episode or args.shot_id:
            if not (args.episode and args.shot_id):
                parser.error("--episode and --shot-id must be supplied together")
            episode = json.loads(args.episode.read_text(encoding="utf-8"))
            attach_visemes(episode, shot_id=args.shot_id, speaker=args.speaker, cues=cues)
            args.episode.write_text(json.dumps(episode, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Generated {len(cues)} mouth cues: {args.output}")
        return 0
    if args.command == "production-run":
        from .production import run_production
        report = run_production(args.project, max_repair_rounds=args.repair_rounds)
        print("PRODUCTION " + report["status"])
        print("Report: " + str(args.project / "production" / "production_run.json"))
        for error in report.get("errors", []):
            print("BLOCKED: " + error)
        return 0 if report.get("status") == "delivered" else 1
    if args.command == "visual-approve":
        episode = read_json(args.project / "episode.json")
        approval = {"episode_id": episode["id"], "approved": True,
                    "reviewer": args.reviewer, "notes": args.notes}
        target = args.project / "production" / "human_visual_approval.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(approval, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
        print("Visual approval recorded: " + str(target))
        return 0
    if args.command == "blender-render":
        from .blender_bridge import render_with_blender
        output = render_with_blender(args.project, blender=args.blender)
        print(f"Blender scene prepared: {output}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
