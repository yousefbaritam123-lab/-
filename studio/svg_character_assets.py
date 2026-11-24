"""Extract the original 60 SVG cast drawings without altering their artwork.

This is a lossless asset-preparation stage, not a completed anatomical rig.
Every original SVG child element is retained as its own named source layer so
later rigging can map parts without redrawing or flattening the character.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def _tag(local: str) -> str:
    return f"{{{SVG_NS}}}{local}"


def _safe_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError(f"Unsafe SVG character id: {value!r}")
    return value


def prepare_svg_cast(source_svg: Path, output_dir: Path, *, expected_count: int = 60) -> Path:
    """Extract each cast group and preserve each direct SVG element verbatim.

    The source file is read-only. Output consists of one SVG per character and
    a manifest recording original element order/attributes. No body-part
    guesses are made: a source path may contain multiple limbs in one element.
    """
    source_svg = Path(source_svg)
    output_dir = Path(output_dir)
    if not source_svg.is_file():
        raise FileNotFoundError(source_svg)
    tree = ET.parse(source_svg)
    root = tree.getroot()
    view_box = root.get("viewBox")
    if not view_box:
        raise ValueError("Cast SVG must declare a viewBox")
    groups = [
        node for node in root.iter(_tag("g"))
        if re.fullmatch(r"extra-\d{3}", node.get("id", ""))
    ]
    groups.sort(key=lambda node: node.get("id", ""))
    if len(groups) != expected_count:
        raise ValueError(f"Expected {expected_count} cast groups, found {len(groups)}")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "source_svg": str(source_svg),
        "source_preserved": True,
        "character_count": len(groups),
        "characters": [],
        "rig_status": "source_layers_extracted_joint_maps_created_articulation_incomplete",
        "important_limit": (
            "Source SVG elements are preserved as independent vector layers. "
            "This does not infer anatomical joints or split compound paths."
        ),
    }
    for group in groups:
        source_id = _safe_id(group.get("id", ""))
        character_id = source_id.replace("-", "_")
        index = int(source_id.split("-")[1])
        column = (index - 1) % 10
        row = (index - 1) // 10
        wrapper = ET.Element(_tag("svg"), {
            "width": "200", "height": "220", "viewBox": "0 0 200 220",
            "version": "1.1",
        })
        # Preserve inherited group presentation and the original coordinates.
        outer = ET.SubElement(wrapper, _tag("g"), {
            "id": character_id,
            "transform": f"translate({-column * 200} {-row * 200})",
        })
        inner = ET.SubElement(outer, _tag("g"), {
            key: value for key, value in group.attrib.items() if key != "id"
        })
        elements = []
        source_children = list(group)
        for element_index, child in enumerate(source_children):
            tag = child.tag.rsplit("}", 1)[-1]
            role = tag
            if tag == "path":
                fill = child.get("fill", "")
                stroke_width = child.get("stroke-width", "")
                if fill == "none" and stroke_width == "8":
                    role = "arm_outline_source"
                elif fill == "none" and stroke_width == "4":
                    role = "arm_skin_source"
                elif stroke_width == "5" and fill != "none":
                    role = "body_or_torso_source"
                elif stroke_width == "4" and fill != "none":
                    role = "shoe_or_accessory_source"
                else:
                    role = "decorative_path_source"
            elif tag == "ellipse":
                role = "ground_shadow"
            elif tag == "rect":
                role = "neck_source"
            elif tag == "circle":
                role = "head_or_eye_source"
            elif tag == "text":
                role = "contact_sheet_label"
            layer_id = f"source_layer_{element_index:02d}"
            layer = ET.SubElement(inner, _tag("g"), {"id": layer_id, "data-role": role})
            copied = ET.fromstring(ET.tostring(child, encoding="unicode"))
            layer.append(copied)
            elements.append({
                "layer_id": layer_id, "role": role,
                "source_order": element_index, "source_tag": tag,
                "source_attributes": dict(child.attrib),
            })

        # Joint landmarks are relative to the character's 200 x 220 cell.
        # They describe the source pose; they do not imply that compound
        # artwork has already been separated into independently moving pieces.
        cx, cy = 100.0, 76.0
        joints = {
            "head_center": [cx, cy], "neck": [cx, 95.0],
            "left_shoulder": [cx - 17.0, 109.0],
            "right_shoulder": [cx + 17.0, 109.0],
            "left_elbow": [cx - 36.0, 133.0],
            "right_elbow": [cx + 36.0, 133.0],
            "left_wrist": [cx - 50.0, 151.0],
            "right_wrist": [cx + 50.0, 151.0],
            "pelvis": [cx, 148.0],
            "left_hip": [cx - 10.0, 146.0],
            "right_hip": [cx + 10.0, 146.0],
            "left_knee": [cx - 17.0, 172.0],
            "right_knee": [cx + 17.0, 172.0],
            "left_ankle": [cx - 30.0, 188.0],
            "right_ankle": [cx + 30.0, 188.0],
        }
        rig = {
            "schema_version": 1,
            "character_id": character_id,
            "coordinate_space": "character_cell_200x220",
            "joints": joints,
            "bones": [
                {"name": "head", "parent": "neck", "child": "head_center"},
                {"name": "torso", "parent": "neck", "child": "pelvis"},
                {"name": "upper_arm_L", "parent": "left_shoulder", "child": "left_elbow"},
                {"name": "forearm_L", "parent": "left_elbow", "child": "left_wrist"},
                {"name": "upper_arm_R", "parent": "right_shoulder", "child": "right_elbow"},
                {"name": "forearm_R", "parent": "right_elbow", "child": "right_wrist"},
                {"name": "thigh_L", "parent": "left_hip", "child": "left_knee"},
                {"name": "shin_L", "parent": "left_knee", "child": "left_ankle"},
                {"name": "thigh_R", "parent": "right_hip", "child": "right_knee"},
                {"name": "shin_R", "parent": "right_knee", "child": "right_ankle"},
            ],
            "articulation_status": {
                "arms": "landmarks_defined; source compound paths not yet split",
                "legs": "landmarks_defined; connected lower-body silhouette not yet split",
                "head": "source element exists",
                "torso": "source element exists",
                "hands": "not separately drawn",
                "feet": "source path may contain both feet",
            },
            "source_artwork_changed": False,
        }
        rig_path = output_dir / f"{character_id}.rig.json"
        rig_path.write_text(json.dumps(rig, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        target = output_dir / f"{character_id}.svg"
        ET.ElementTree(wrapper).write(target, encoding="utf-8", xml_declaration=True)
        manifest["characters"].append({
            "id": character_id,
            "source_group_id": source_id,
            "svg": target.name,
            "source_element_count": len(elements),
            "layers": elements,
            "rig": rig_path.name,
            "joint_count": len(joints),
            "rig_status": "joint_map_created_articulation_incomplete",
        })

    manifest_path = output_dir / "cast_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path
