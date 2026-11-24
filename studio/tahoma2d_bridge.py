"""Prepare non-destructive, canvas-aligned SVG layers for Tahoma2D.

Tahoma2D imports SVG levels as vector (PLI) drawings. This adapter exports
individual original-art layers and rig metadata without inventing a .tnz scene
or pretending that a Plastic skeleton has already been authored.
"""
from __future__ import annotations

import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def _tag(name: str) -> str:
    return f"{{{SVG_NS}}}{name}"


def _safe_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError(f"Unsafe character id: {value!r}")
    return value


def _write_layer(source_root: ET.Element, group_path: list[ET.Element],
                 output: Path, character_id: str, layer_id: str) -> None:
    """Copy the exact ancestor transforms/styles and one layer into a full canvas."""
    view_box = source_root.get("viewBox", "0 0 200 220")
    width = source_root.get("width", "200")
    height = source_root.get("height", "220")
    root = ET.Element(_tag("svg"), {
        "width": width, "height": height, "viewBox": view_box,
        "version": "1.1", "data-character-id": character_id,
        "data-layer-id": layer_id,
    })
    parent = root
    for ancestor in group_path[:-1]:
        clone = ET.SubElement(parent, _tag("g"), dict(ancestor.attrib))
        parent = clone
    parent.append(ET.fromstring(ET.tostring(group_path[-1], encoding="unicode")))
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)


def prepare_tahoma2d_character(character_id: str, prepared_cast_dir: Path,
                               output_root: Path) -> Path:
    """Export original vector references, articulated SVG layers and joint map.

    Output is an import-ready asset package, not a fabricated Tahoma scene.
    Tahoma2D's Plastic mesh/skeleton is authored in the application and then
    saved by Tahoma2D itself.
    """
    character_id = _safe_id(character_id)
    prepared_cast_dir = Path(prepared_cast_dir)
    output_root = Path(output_root)
    source_svg = prepared_cast_dir / f"{character_id}.svg"
    layers_svg = prepared_cast_dir / f"{character_id}.rig_layers.svg"
    rig_json = prepared_cast_dir / f"{character_id}.rig.json"
    for path in (source_svg, layers_svg, rig_json):
        if not path.is_file():
            raise FileNotFoundError(path)

    target = output_root / character_id
    if target.exists() and any(target.iterdir()):
        raise FileExistsError(f"Tahoma2D output already exists: {target}")
    target.mkdir(parents=True, exist_ok=True)

    # Keep an untouched, full-character SVG as the visual source of truth.
    shutil.copy2(source_svg, target / "full_character_reference.svg")
    rig = json.loads(rig_json.read_text(encoding="utf-8"))
    layers_root = ET.parse(layers_svg).getroot()
    outer = next((n for n in layers_root if n.tag == _tag("g")), None)
    if outer is None:
        raise ValueError(f"No outer character group in {layers_svg}")
    inner = next((n for n in outer if n.tag == _tag("g")), None)
    if inner is None:
        raise ValueError(f"No inner character group in {layers_svg}")

    exported: list[dict[str, Any]] = []
    for group in list(inner):
        layer_id = group.get("id", "")
        if not layer_id:
            continue
        layer_path = target / f"{layer_id}.svg"
        _write_layer(layers_root, [outer, inner, group], layer_path,
                     character_id, layer_id)
        exported.append({
            "id": layer_id,
            "file": layer_path.name,
            "kind": "original_vector_segment",
            "source_art_modified": False,
        })

    manifest = {
        "schema_version": 1,
        "engine": "Tahoma2D",
        "character_id": character_id,
        "canvas": {"width": 200, "height": 220, "view_box": "0 0 200 220"},
        "source_art_preserved": True,
        "reference_art": "full_character_reference.svg",
        "rig_file": rig_json.name,
        "joints": rig.get("joints", {}),
        "bones": rig.get("bones", []),
        "layers": exported,
        "layer_count": len(exported),
        "rigging_status": "vector_layers_exported_plastic_skeleton_not_yet_authored",
        "known_gaps": [
            "The original full-character reference is not automatically split into torso, head, and both legs.",
            "The cast source does not contain independently drawn hands/fingers.",
            "A Tahoma2D Plastic mesh and skeleton must be created and saved in Tahoma2D.",
            "This package does not claim to be a native .tnz scene or a finished rig.",
        ],
    }
    manifest_path = target / "tahoma2d_character_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    guide = """# Tahoma2D character import

1. Open Tahoma2D and create a project/scene using the episode's target frame rate.
2. Load each SVG level from this folder. Tahoma2D converts imported SVG levels to PLI vector levels.
3. Use full_character_reference.svg as the visual registration reference; do not leave it visible together with duplicate segment layers.
4. Place the exported segment levels in their correct stacking order and align them using the shared 200x220 canvas.
5. For a deforming whole-character test, create a Mesh level from the source artwork, then use Plastic → Build Skeleton. Place the root, neck, shoulders, elbows, wrists, pelvis, hips, knees and ankles using tahoma2d_character_manifest.json.
6. Test a neutral pose first, then a short wave and walk. Inspect seams, line thickness, occlusion and foot contact before authoring the full cast.
7. Save the native Tahoma2D scene from the application. This package intentionally does not fabricate a .tnz file.

Important: arm/foot SVG segments are exported from existing source paths. Torso and legs are not yet fully segmented; do not claim a complete cut-out rig until those layers are prepared and tested.
"""
    (target / "TAHOMA2D_IMPORT_GUIDE.md").write_text(guide, encoding="utf-8")
    return manifest_path


def prepare_tahoma2d_episode(project_dir: Path, character_ids: list[str] | None = None) -> list[Path]:
    project_dir = Path(project_dir)
    episode_path = project_dir / "episode.json"
    if not episode_path.is_file():
        raise FileNotFoundError(episode_path)
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    actors = episode.get("characters", [])
    if character_ids is None:
        character_ids = sorted({
            str(actor.get("cast_id", actor.get("id", "")))
            for actor in actors
            if str(actor.get("cast_id", actor.get("id", ""))).startswith("extra_")
        })
        named_ids = sorted({
            str(actor.get("id", ""))
            for actor in actors
            if str(actor.get("id", "")) in {"youssef", "adam"}
        })
    else:
        named_ids = []
    prepared = project_dir / "assets" / "characters" / "prepared_cast_60"
    output_root = project_dir / "production" / "tahoma2d" / "characters"
    outputs: list[Path] = []
    if character_ids:
        if not (prepared / "cast_manifest.json").is_file():
            from .svg_character_assets import prepare_svg_cast
            prepare_svg_cast(
                project_dir / "assets" / "characters" / "cast_60" / "contact_sheet.svg",
                prepared,
            )
        outputs.extend(
            prepare_tahoma2d_character(character_id, prepared, output_root)
            for character_id in character_ids
        )
    if named_ids:
        from .svg_character_assets import prepare_named_character_svg
        for character_id in named_ids:
            source = project_dir / "assets" / "characters" / character_id / "design_sheet.svg"
            if not source.is_file():
                raise FileNotFoundError(source)
            target = output_root / character_id
            if target.exists() and any(target.iterdir()):
                raise FileExistsError(f"Tahoma2D output already exists: {target}")
            target.mkdir(parents=True, exist_ok=True)
            cropped = target / "full_character_reference.svg"
            prepare_named_character_svg(source, cropped, character_id)
            manifest = {
                "schema_version": 1,
                "engine": "Tahoma2D",
                "character_id": character_id,
                "source_art_preserved": True,
                "reference_art": cropped.name,
                "rigging_status": "reference_only_manual_layering_and_plastic_skeleton_required",
                "known_gaps": [
                    "This source has not yet been separated into independently moving body-part layers.",
                    "No anatomical joint map is inferred for this named character.",
                    "Create and save the Plastic mesh/skeleton in Tahoma2D after inspecting the source artwork.",
                ],
            }
            manifest_path = target / "tahoma2d_character_manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (target / "TAHOMA2D_IMPORT_GUIDE.md").write_text(
                "# Tahoma2D named-character import\n\n"
                "Import full_character_reference.svg as a vector level. Inspect the artwork and manually create clean layers before building a Plastic mesh/skeleton. "
                "Do not claim this reference-only package is a completed cut-out rig. Save the native scene from Tahoma2D.\n",
                encoding="utf-8",
            )
            outputs.append(manifest_path)
    if not outputs:
        raise ValueError("No supported character IDs found in episode.json; use extra_NNN, youssef, or adam.")
    return outputs
