import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from studio.svg_character_assets import SVG_NS, prepare_svg_cast
from studio.tahoma2d_bridge import prepare_tahoma2d_character


class Tahoma2DBridgeTests(unittest.TestCase):
    def test_exports_canvas_aligned_original_vector_segments_without_source_changes(self):
        ns = f"{{{SVG_NS}}}"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "contact.svg"
            svg = ET.Element(ns + "svg", {"width": "2000", "height": "1200", "viewBox": "0 0 2000 1200"})
            group = ET.SubElement(svg, ns + "g", {"id": "extra-001", "transform": "translate(0 0)", "stroke": "#171923"})
            ET.SubElement(group, ns + "path", {"d": "M 83 109 L 64 133 L 50 151 M 117 109 L 136 133 L 150 151", "fill": "none", "stroke-width": "8"})
            ET.SubElement(group, ns + "path", {"d": "M 83 109 L 64 133 L 50 151 M 117 109 L 136 133 L 150 151", "fill": "none", "stroke-width": "4"})
            ET.SubElement(group, ns + "path", {"d": "M 80 100 L 100 80 L 120 100", "fill": "#C62828", "stroke-width": "5"})
            ET.SubElement(group, ns + "rect", {"x": "95", "y": "100", "width": "10", "height": "8"})
            ET.SubElement(group, ns + "circle", {"cx": "100", "cy": "76", "r": "20", "fill": "#F1C27D", "stroke-width": "5"})
            for index in range(2, 61):\n                extra = ET.SubElement(svg, ns + "g", {"id": f"extra-{index:03d}", "transform": f"translate({((index - 1) % 10) * 200} {((index - 1) // 10) * 200})"})\n                ET.SubElement(extra, ns + "path", {"d": f"M {index} 1 L {index} 2", "fill": "#C62828"})\n            ET.ElementTree(svg).write(source, encoding="utf-8", xml_declaration=True)
            original = source.read_bytes()
            prepared = root / "prepared"
            prepare_svg_cast(source, prepared)
            manifest_path = prepare_tahoma2d_character("extra_001", prepared, root / "tahoma")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertTrue(manifest["source_art_preserved"])
            self.assertEqual(source.read_bytes(), original)
            self.assertGreaterEqual(manifest["layer_count"], 8)
            for layer in manifest["layers"]:
                layer_root = ET.parse(manifest_path.parent / layer["file"]).getroot()
                self.assertEqual(layer_root.get("viewBox"), "0 0 200 220")
                self.assertEqual(layer_root.get("data-character-id"), "extra_001")
            self.assertTrue((manifest_path.parent / "full_character_reference.svg").is_file())
            self.assertIn("does not fabricate", (manifest_path.parent / "TAHOMA2D_IMPORT_GUIDE.md").read_text())
