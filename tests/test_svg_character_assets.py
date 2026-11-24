import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from studio.svg_character_assets import SVG_NS, prepare_svg_cast


class SvgCharacterAssetsTests(unittest.TestCase):
    def _source(self, root: Path) -> Path:
        ns = f"{{{SVG_NS}}}"
        svg = ET.Element(ns + "svg", {"viewBox": "0 0 2000 1200"})
        for index in range(1, 61):
            group = ET.SubElement(svg, ns + "g", {
                "id": f"extra-{index:03d}", "stroke": "#171923",
                "stroke-width": "5",
            })
            ET.SubElement(group, ns + "path", {
                "d": f"M {index} 1 L {index} 2", "fill": "#C62828",
            })
            ET.SubElement(group, ns + "circle", {
                "cx": str(index), "cy": "3", "r": "2",
            })
        path = root / "contact.svg"
        ET.ElementTree(svg).write(path, encoding="utf-8", xml_declaration=True)
        return path

    def test_extracts_all_original_elements_without_modifying_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._source(root)
            original = source.read_bytes()
            manifest_path = prepare_svg_cast(source, root / "prepared")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(manifest["character_count"], 60)
            self.assertEqual(manifest["characters"][0]["id"], "extra_001")
            self.assertEqual(manifest["characters"][0]["source_element_count"], 2)
            extracted = ET.parse(root / "prepared" / "extra_001.svg").getroot()
            paths = list(extracted.iter(f"{{{SVG_NS}}}path"))
            self.assertEqual(paths[0].get("d"), "M 1 1 L 1 2")
            self.assertEqual(paths[0].get("fill"), "#C62828")
            self.assertEqual(extracted.find(f".//{{{SVG_NS}}}g").get("stroke"), "#171923")

    def test_rejects_wrong_cast_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._source(root)
            with self.assertRaises(ValueError):
                prepare_svg_cast(source, root / "out", expected_count=59)

    def test_refuses_to_overwrite_nonempty_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._source(root)
            out = root / "out"
            out.mkdir()
            (out / "keep.txt").write_text("keep")
            with self.assertRaises(FileExistsError):
                prepare_svg_cast(source, out)


if __name__ == "__main__":
    unittest.main()
