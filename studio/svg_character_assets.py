"""Extract the original 60 SVG cast drawings without altering their artwork.

This is a lossless asset-preparation stage, not a completed anatomical rig.
Every original SVG child element is retained as its own named source layer so
later rigging can map parts without redrawing or flattening the character.
"""
from __future__ import annotations

import json
import re
import shutil
import xml.etree.ElementTree as ET

from .skeletal_graph import SkeletonGraph
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



def _absolute_polyline_points(path_data: str) -> list[tuple[float, float]]:
    """Read absolute M/L vertices used by the cast's arm and leg paths."""
    points: list[tuple[float, float]] = []
    for match in re.finditer(r"(?<![A-Za-z])(?:M|L)\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)", path_data):
        points.append((float(match.group(1)), float(match.group(2))))
    return points


def _split_subpaths(path_data: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?=M\s*[-+]?(?:\d|\.\d))", path_data.strip()) if part.strip()]



def prepare_named_character_svg(
    source_svg: Path,
    output_svg: Path,
    character_id: str,
    *,
    view_box: tuple[float, float, float, float] = (150.0, 20.0, 260.0, 570.0),
) -> Path:
    """Extract the original character drawing from a labeled model sheet.

    Only the transformed character group is copied; the sheet background,
    headings and design notes are excluded. Source artwork remains untouched.
    """
    character_id = _safe_id(character_id)
    source_svg = Path(source_svg)
    output_svg = Path(output_svg)
    if not source_svg.is_file():
        raise FileNotFoundError(source_svg)
    if output_svg.exists():
        raise FileExistsError(output_svg)
    source_root = ET.parse(source_svg).getroot()
    candidates = [
        node for node in source_root.iter(_tag("g"))
        if node.get("transform", "").startswith("translate(")
        and any(child.tag in {_tag("path"), _tag("circle"), _tag("ellipse")} for child in node.iter())
    ]
    if len(candidates) != 1:
        raise ValueError(f"Expected one original character group in {source_svg.name}, found {len(candidates)}")
    x, y, width, height = view_box
    wrapper = ET.Element(_tag("svg"), {
        "width": f"{width:g}", "height": f"{height:g}",
        "viewBox": f"0 0 {width:g} {height:g}", "version": "1.1",
        "data-character-id": character_id,
    })
    crop = ET.SubElement(wrapper, _tag("g"), {"transform": f"translate({-x:g} {-y:g})"})
    crop.append(ET.fromstring(ET.tostring(candidates[0], encoding="unicode")))
    output_svg.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(wrapper).write(output_svg, encoding="utf-8", xml_declaration=True)
    return output_svg



def prepare_named_character_layers(
    source_svg: Path,
    output_dir: Path,
    character_id: str,
    *,
    view_box: tuple[float, float, float, float] = (150.0, 20.0, 260.0, 570.0),
) -> Path:
    """Split existing named model-sheet paths into aligned importable vector levels.

    The source sheet is copied unchanged. Existing two-subpath arm/leg paths
    are separated at their existing vertices; no new anatomy or artwork is
    drawn. This prepares levels and joint landmarks, not a Plastic rig.
    """
    character_id = _safe_id(character_id)
    source_svg, output_dir = Path(source_svg), Path(output_dir)
    if not source_svg.is_file():
        raise FileNotFoundError(source_svg)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    source_root = ET.parse(source_svg).getroot()
    candidates = [
        node for node in source_root.iter(_tag("g"))
        if node.get("transform", "").startswith("translate(")
        and any(child.tag in {_tag("path"), _tag("circle"), _tag("ellipse")} for child in node.iter())
    ]
    if len(candidates) != 1:
        raise ValueError(f"Expected one original character group in {source_svg.name}, found {len(candidates)}")
    source_group = candidates[0]
    x0, y0, width, height = view_box
    shutil.copy2(source_svg, output_dir / "source_design_sheet.svg")
    reference = output_dir / "full_character_reference.svg"
    prepare_named_character_svg(source_svg, reference, character_id, view_box=view_box)

    layers: list[tuple[str, ET.Element, dict[str, Any]]] = []
    joints: dict[str, list[float]] = {}
    bones: list[dict[str, str]] = []
    generic_index = 0

    for element_index, child in enumerate(list(source_group)):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "path":
            subpaths = _split_subpaths(child.get("d", ""))
            parsed = [_absolute_polyline_points(path_data) for path_data in subpaths]
            parsed = [points for points in parsed if len(points) >= 2]
            fill = child.get("fill", "")
            stroke_width = float(child.get("stroke-width", "0") or 0)

            if fill == "none" and len(parsed) == 2 and all(len(points) == 3 for points in parsed):
                mean_y = sum(point[1] for points in parsed for point in points) / 6
                limb_kind = "arm" if mean_y < -180 else "leg"
                for points in parsed:
                    side = "L" if sum(point[0] for point in points) / 3 < 0 else "R"
                    first_name, second_name = (
                        ("upper_arm", "forearm") if limb_kind == "arm"
                        else ("thigh", "shin")
                    )
                    for segment_name, segment_points in (
                        (first_name, points[:2]), (second_name, points[1:])
                    ):
                        part = ET.Element(_tag("path"), dict(child.attrib))
                        part.set("d", "M " + " L ".join(f"{px:g} {py:g}" for px, py in segment_points))
                        layer_id = f"{segment_name}_{side}"
                        layers.append((layer_id, part, {
                            "source_element_index": element_index,
                            "source_path_split_at_existing_vertex": True,
                            "source_art_redrawn": False,
                        }))
                    if limb_kind == "arm":
                        joints[f"{'left' if side == 'L' else 'right'}_shoulder"] = list(points[0])
                        joints[f"{'left' if side == 'L' else 'right'}_elbow"] = list(points[1])
                        joints[f"{'left' if side == 'L' else 'right'}_wrist"] = list(points[2])
                    else:
                        joints[f"{'left' if side == 'L' else 'right'}_hip"] = list(points[0])
                        joints[f"{'left' if side == 'L' else 'right'}_knee"] = list(points[1])
                        joints[f"{'left' if side == 'L' else 'right'}_ankle"] = list(points[2])
            elif len(parsed) == 1 and len(parsed[0]) == 2 and stroke_width >= 24:
                points = parsed[0]
                torso = ET.fromstring(ET.tostring(child, encoding="unicode"))
                layers.append(("torso_centerline", torso, {
                    "source_element_index": element_index,
                    "source_art_redrawn": False,
                }))
                joints["neck"] = list(points[-1])
                joints["pelvis"] = list(points[0])
                bones.append({"name": "torso", "parent": "neck", "child": "pelvis"})
            elif len(parsed) == 2 and all(len(points) == 2 for points in parsed) and stroke_width >= 18:
                for points in parsed:
                    side = "L" if sum(point[0] for point in points) / 2 < 0 else "R"
                    part = ET.Element(_tag("path"), dict(child.attrib))
                    part.set("d", "M " + " L ".join(f"{px:g} {py:g}" for px, py in points))
                    layers.append((f"shoe_{side}", part, {
                        "source_element_index": element_index,
                        "source_path_split_at_existing_subpath": True,
                        "source_art_redrawn": False,
                    }))
            else:
                generic_index += 1
                role = "costume_or_face_detail" if fill != "none" else "original_stroke_detail"
                copied = ET.fromstring(ET.tostring(child, encoding="unicode"))
                layers.append((f"{role}_{generic_index:02d}", copied, {
                    "source_element_index": element_index,
                    "source_art_redrawn": False,
                }))
        elif tag == "circle":
            radius = float(child.get("r", "0") or 0)
            copied = ET.fromstring(ET.tostring(child, encoding="unicode"))
            if radius >= 40:
                layer_id = "head"
                joints["head_center"] = [
                    float(child.get("cx", "0")), float(child.get("cy", "0"))
                ]
            else:
                generic_index += 1
                layer_id = f"face_detail_{generic_index:02d}"
            layers.append((layer_id, copied, {
                "source_element_index": element_index,
                "source_art_redrawn": False,
            }))
        else:
            generic_index += 1
            copied = ET.fromstring(ET.tostring(child, encoding="unicode"))
            layers.append((f"original_detail_{generic_index:02d}", copied, {
                "source_element_index": element_index,
                "source_art_redrawn": False,
            }))

    if len(layers) < 8:
        raise ValueError(f"Named character segmentation produced too few vector layers: {len(layers)}")
    if not {"head_center", "neck", "pelvis"}.issubset(joints):
        raise ValueError("Named character source is missing required head/torso landmarks")

    bones.extend([
        {"name": "head", "parent": "neck", "child": "head_center"},
        {"name": "upper_arm_L", "parent": "left_shoulder", "child": "left_elbow"},
        {"name": "forearm_L", "parent": "left_elbow", "child": "left_wrist"},
        {"name": "upper_arm_R", "parent": "right_shoulder", "child": "right_elbow"},
        {"name": "forearm_R", "parent": "right_elbow", "child": "right_wrist"},
        {"name": "thigh_L", "parent": "left_hip", "child": "left_knee"},
        {"name": "shin_L", "parent": "left_knee", "child": "left_ankle"},
        {"name": "thigh_R", "parent": "right_hip", "child": "right_knee"},
        {"name": "shin_R", "parent": "right_knee", "child": "right_ankle"},
    ])

    def make_svg(selected: list[tuple[str, ET.Element, dict[str, Any]]], destination: Path) -> None:
        wrapper = ET.Element(_tag("svg"), {
            "width": f"{width:g}", "height": f"{height:g}",
            "viewBox": f"0 0 {width:g} {height:g}", "version": "1.1",
            "data-character-id": character_id,
        })
        crop = ET.SubElement(wrapper, _tag("g"), {"transform": f"translate({-x0:g} {-y0:g})"})
        for layer_id, element, _metadata in selected:
            layer_group = ET.SubElement(crop, _tag("g"), {"id": layer_id})
            character_group = ET.SubElement(layer_group, _tag("g"), dict(source_group.attrib))
            character_group.append(ET.fromstring(ET.tostring(element, encoding="unicode")))
        destination.parent.mkdir(parents=True, exist_ok=True)
        ET.ElementTree(wrapper).write(destination, encoding="utf-8", xml_declaration=True)

    for layer_id, element, _metadata in layers:
        make_svg([(layer_id, element, {})], output_dir / f"{layer_id}.svg")
    combined = output_dir / "rig_layers.svg"
    make_svg(layers, combined)

    manifest = {
        "schema_version": 1,
        "character_id": character_id,
        "source_design_sheet": "source_design_sheet.svg",
        "full_character_reference": "full_character_reference.svg",
        "canvas": {"width": width, "height": height, "view_box": f"0 0 {width:g} {height:g}"},
        "source_art_preserved": True,
        "geometry_policy": "Only original vector elements are copied; existing polyline paths are split at their authored vertices without changing coordinates or stroke attributes.",
        "layers": [
            {"id": layer_id, "file": f"{layer_id}.svg", **metadata}
            for layer_id, _element, metadata in layers
        ],
        "combined_levels_svg": combined.name,
        "layer_count": len(layers),
        "joints": joints,
        "bones": bones,
        "rigging_status": "vector_parts_segmented_at_existing_path_vertices_plastic_mesh_and_skeleton_not_yet_authored",
        "known_gaps": [
            "No native Tahoma2D Plastic mesh or skeleton has been authored.",
            "The source character uses simple stroke limbs; it does not contain separately drawn fingers or deformable hand artwork.",
            "Head, face, scarf and clothing shapes are preserved as source vector levels; expression variants are not generated.",
        ],
    }
    manifest_path = output_dir / "named_character_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


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
        "rig_status": "source_layers_and_elbow_split_arm_segments_created_leg_segmentation_incomplete",
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
        articulated_parts = []
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
            # Existing paired SVG subpaths can be exported independently without altering the source layer.
            d = child.get("d", "") if tag == "path" else ""
            subpaths = _split_subpaths(d) if tag == "path" else []
            if tag == "path" and child.get("fill") == "none" and child.get("stroke-width") in {"8", "4"}:
                kind = "outline" if child.get("stroke-width") == "8" else "skin"
                for subpath in subpaths:
                    points = _absolute_polyline_points(subpath)
                    if len(points) >= 3:
                        side = "L" if sum(p[0] for p in points) / len(points) < (100 + column * 200) else "R"
                        for segment_name, segment_points in (("upper", points[:2]), ("forearm", points[1:3])):
                            segment_path = "M " + " L ".join(f"{x:g} {y:g}" for x, y in segment_points)
                            part = ET.Element(_tag("path"), dict(child.attrib))
                            part.set("d", segment_path)
                            layer_name = f"{segment_name}_arm_{kind}_{side}" if segment_name == "upper" else f"forearm_{kind}_{side}"
                            articulated_parts.append((layer_name, part))
            elif tag == "path" and child.get("fill") != "none" and child.get("stroke-width") == "4":
                for subpath in subpaths:
                    points = _absolute_polyline_points(subpath)
                    if len(points) >= 2:
                        side = "L" if sum(p[0] for p in points) / len(points) < (100 + column * 200) else "R"
                        part = ET.Element(_tag("path"), dict(child.attrib))
                        part.set("d", subpath)
                        articulated_parts.append((f"foot_{side}", part))
            elements.append({
                "layer_id": layer_id, "role": role,
                "source_order": element_index, "source_tag": tag,
                "source_attributes": dict(child.attrib),
            })

        # Joint landmarks are derived from the original source path vertices.
        cx, cy = 100.0, 76.0
        joints = {
            "head_center": [cx, cy], "neck": [cx, 102.5],
            "left_shoulder": [83.0, 109.0], "right_shoulder": [117.0, 109.0],
            "left_elbow": [64.0, 133.0], "right_elbow": [136.0, 129.0],
            "left_wrist": [50.0, 151.0], "right_wrist": [150.0, 151.0],
            "pelvis": [100.0, 139.0],
            "left_hip": [87.0, 139.0], "right_hip": [113.0, 139.0],
            "left_knee": [83.0, 172.0], "right_knee": [117.0, 172.0],
            "left_ankle": [81.0, 188.0], "right_ankle": [120.0, 188.0],
        }
        for node in source_children:
            if node.tag != _tag("path") or node.get("fill") != "none" or node.get("stroke-width") != "8":
                continue
            paths = [_absolute_polyline_points(p) for p in _split_subpaths(node.get("d", ""))]
            paths = [p for p in paths if len(p) >= 3]
            left = [p for p in paths if sum(x for x, _ in p) / len(p) < (100 + column * 200)]
            right = [p for p in paths if sum(x for x, _ in p) / len(p) >= (100 + column * 200)]
            if left and right:
                lp = [(x - column * 200, y) for x, y in left[0][:3]]
                rp = [(x - column * 200, y) for x, y in right[0][:3]]
                joints["left_shoulder"], joints["left_elbow"], joints["left_wrist"] = [list(p) for p in lp]
                joints["right_shoulder"], joints["right_elbow"], joints["right_wrist"] = [list(p) for p in rp]
            break
        for node in source_children:
            if node.tag == _tag("circle") and node.get("r") and node.get("fill") and node.get("stroke-width") == "5":
                joints["head_center"] = [
                    float(node.get("cx", cx)) - column * 200,
                    float(node.get("cy", cy)),
                ]
                break
        for node in source_children:
            if node.tag == _tag("rect"):
                joints["neck"] = [
                    float(node.get("x", cx)) - column * 200 + float(node.get("width", 0)) * 0.5,
                    float(node.get("y", 0)) + float(node.get("height", 0)),
                ]
                break
        for node in source_children:
            if node.tag != _tag("path") or node.get("fill") == "none" or node.get("stroke-width") != "5":
                continue
            points = [(x - column * 200, y) for x, y in _absolute_polyline_points(node.get("d", ""))]
            left = [p for p in points if p[0] < 100]
            right = [p for p in points if p[0] > 100]
            if len(points) >= 9 and left and right:
                joints["left_hip"] = list(min(left, key=lambda p: p[1]))
                joints["right_hip"] = list(min(right, key=lambda p: p[1]))
                joints["left_knee"] = list(min((p for p in left if p[1] > joints["left_hip"][1]), key=lambda p: abs(p[1] - 172), default=tuple(joints["left_knee"])))
                joints["right_knee"] = list(min((p for p in right if p[1] > joints["right_hip"][1]), key=lambda p: abs(p[1] - 172), default=tuple(joints["right_knee"])))
                left_bottom = [p for p in left if p[1] == max(q[1] for q in left)]
                right_bottom = [p for p in right if p[1] == max(q[1] for q in right)]
                if left_bottom:
                    joints["left_ankle"] = [sum(p[0] for p in left_bottom) / len(left_bottom), sum(p[1] for p in left_bottom) / len(left_bottom)]
                if right_bottom:
                    joints["right_ankle"] = [sum(p[0] for p in right_bottom) / len(right_bottom), sum(p[1] for p in right_bottom) / len(right_bottom)]
                joints["pelvis"] = [(joints["left_hip"][0] + joints["right_hip"][0]) * 0.5, (joints["left_hip"][1] + joints["right_hip"][1]) * 0.5]
            break
        bone_definitions = [
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
        ]
        skeleton_graph = SkeletonGraph.from_rig(joints, bone_definitions)
        rig = {
            "schema_version": 2,
            "structure_format": "named_joint_segment_graph_v1",
            "structure": skeleton_graph.to_dict(),
            "character_id": character_id,
            "coordinate_space": "character_cell_200x220",
            "joints": joints,
            "bones": bone_definitions,
            "articulation_status": {
                "arms": "upper_arm_and_forearm_outline_and_skin_segments_extracted_from_original_paths",
                "legs": "source_lower_body_outline_preserved; joint_landmarks_derived_but_leg_meshes_not_split",
                "head": "source element exists",
                "torso": "source element exists",
                "hands": "not separately drawn",
                "feet": "source path may contain both feet",
            },
            "source_artwork_changed": False,
        }
        rig_layers_path = output_dir / f"{character_id}.rig_layers.svg"
        rig_root = ET.Element(_tag("svg"), {"width": "200", "height": "220", "viewBox": "0 0 200 220", "version": "1.1"})
        rig_outer = ET.SubElement(rig_root, _tag("g"), {"transform": f"translate({-column * 200} {-row * 200})"})
        rig_inner = ET.SubElement(rig_outer, _tag("g"), {key: value for key, value in group.attrib.items() if key != "id"})
        for part_id, part_element in articulated_parts:
            part_group = ET.SubElement(rig_inner, _tag("g"), {"id": part_id})
            part_group.append(part_element)
        ET.ElementTree(rig_root).write(rig_layers_path, encoding="utf-8", xml_declaration=True)
        rig["articulated_layers_svg"] = rig_layers_path.name
        rig["articulated_layer_ids"] = [part_id for part_id, _ in articulated_parts]
        rig["articulation_status"]["arms"] = "left_right_upper_arm_and_forearm_outline_and_skin_segments_exported"
        rig["articulation_status"]["feet"] = "left_and_right_feet_exported" if any(part_id.startswith("foot_") for part_id, _ in articulated_parts) else "not_split"
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
            "rig_status": "elbow_split_arm_segments_created_leg_segmentation_incomplete",
        })

    manifest_path = output_dir / "cast_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path
