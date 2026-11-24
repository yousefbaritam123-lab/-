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
        "rig_status": "source_layers_extracted_not_yet_articulated",
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
        for element_index, child in enumerate(list(group)):
            copied = ET.fromstring(ET.tostring(child, encoding="unicode"))
            layer_id = f"source_layer_{element_index:02d}"
            layer = ET.SubElement(inner, _tag("g"), {"id": layer_id})
            layer.append(copied)
            elements.append({
                "layer_id": layer_id,
                "source_order": element_index,
                "source_tag": child.tag.rsplit("}", 1)[-1],
                "source_attributes": dict(child.attrib),
            })
        target = output_dir / f"{character_id}.svg"
        ET.ElementTree(wrapper).write(target, encoding="utf-8", xml_declaration=True)
        manifest["characters"].append({
            "id": character_id,
            "source_group_id": source_id,
            "svg": target.name,
            "source_element_count": len(elements),
            "layers": elements,
            "rig_status": "unmapped_source_layers",
        })

    manifest_path = output_dir / "cast_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path
