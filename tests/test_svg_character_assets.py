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
            self.assertTrue(any(node.get("stroke") == "#171923" for node in extracted.iter(f"{{{SVG_NS}}}g")) )

    def test_writes_joint_map_and_splits_existing_arm_subpaths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._source(root)
            tree = ET.parse(source)
            first = tree.getroot().find(f".//{{{SVG_NS}}}g")
            ET.SubElement(first, f"{{{SVG_NS}}}path", {
                "d": "M 83 109 L 64 133 L 50 151 M 117 109 L 136 133 L 150 151",
                "fill": "none", "stroke": "#171923", "stroke-width": "8",
            })
            ET.SubElement(first, f"{{{SVG_NS}}}path", {
                "d": "M 83 109 L 64 133 L 50 151 M 117 109 L 136 133 L 150 151",
                "fill": "none", "stroke": "#E7B98F", "stroke-width": "4",
            })
            tree.write(source, encoding="utf-8", xml_declaration=True)
            out = root / "prepared"
            prepare_svg_cast(source, out)
            rig = json.loads((out / "extra_001.rig.json").read_text(encoding="utf-8"))
            self.assertEqual(len(rig["joints"]), 15)
            self.assertEqual(rig["joints"]["left_elbow"], [64.0, 133.0])
            layers = ET.parse(out / "extra_001.rig_layers.svg").getroot()
            ids = {node.get("id") for node in layers.iter(f"{{{SVG_NS}}}g")}
            self.assertIn("upper_arm_outline_L", ids)
            self.assertIn("forearm_outline_L", ids)
            self.assertIn("upper_arm_outline_R", ids)
            self.assertIn("forearm_outline_R", ids)
            self.assertIn("upper_arm_skin_L", ids)
            self.assertIn("forearm_skin_L", ids)
            self.assertIn("upper_arm_skin_R", ids)
            self.assertIn("forearm_skin_R", ids)
            self.assertFalse(rig["source_artwork_changed"])

    def test_real_repository_cast_extracts_all_60_with_joint_maps(self):
        repository = Path(__file__).resolve().parents[1]
        source = repository / "assets" / "characters" / "cast_60" / "contact_sheet.svg"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "prepared"
            manifest_path = prepare_svg_cast(source, output)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["character_count"], 60)
            for index in (1, 6, 60):
                character_id = f"extra_{index:03d}"
                rig = json.loads((output / f"{character_id}.rig.json").read_text(encoding="utf-8"))
                self.assertEqual(len(rig["joints"]), 15)
                self.assertTrue((output / f"{character_id}.rig_layers.svg").is_file())
                self.assertTrue((output / f"{character_id}.svg").is_file())

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
