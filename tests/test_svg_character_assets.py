import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from studio.svg_character_assets import SVG_NS, prepare_named_character_layers, prepare_named_character_svg, prepare_svg_cast


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
            self.assertEqual(rig["schema_version"], 2)
            self.assertEqual(rig["structure_format"], "named_joint_segment_graph_v1")
            self.assertEqual(
                rig["structure"]["segments"]["forearm_L"],
                {"from": "left_elbow", "to": "left_wrist"},
            )
            self.assertEqual(
                rig["structure"]["points"]["head_center"],
                {"x": 100.0, "y": 76.0},
            )

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
                self.assertGreater(rig["joints"]["head_center"][0], 0)
                self.assertGreater(rig["joints"]["left_elbow"][1], rig["joints"]["left_shoulder"][1])
                self.assertGreater(rig["joints"]["left_ankle"][1], rig["joints"]["left_knee"][1])
                self.assertTrue((output / f"{character_id}.rig_layers.svg").is_file())
                self.assertTrue((output / f"{character_id}.svg").is_file())

    def test_extracts_original_named_character_from_model_sheet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ns = f"{{{SVG_NS}}}"
            svg = ET.Element(ns + "svg", {"viewBox": "0 0 1000 650"})
            ET.SubElement(svg, ns + "rect", {"width": "1000", "height": "650", "fill": "#1d2b40"})
            ET.SubElement(svg, ns + "text").text = "YOUSSEF — OFFICIAL MODEL SHEET"
            group = ET.SubElement(svg, ns + "g", {"transform": "translate(280 570)", "stroke": "#171923"})
            ET.SubElement(group, ns + "path", {"d": "M0 -170L-48 -55L-65 0", "fill": "none"})
            ET.SubElement(group, ns + "circle", {"cy": "-465", "r": "76", "fill": "#F3D2B2"})
            source = root / "design_sheet.svg"
            ET.ElementTree(svg).write(source, encoding="utf-8", xml_declaration=True)
            original = source.read_bytes()
            output = prepare_named_character_svg(source, root / "prepared" / "youssef.svg", "youssef")
            self.assertEqual(source.read_bytes(), original)
            extracted = ET.parse(output).getroot()
            self.assertEqual(extracted.get("viewBox"), "0 0 260 570")
            self.assertEqual(len(list(extracted.iter(ns + "path"))), 1)
            self.assertEqual(len(list(extracted.iter(ns + "circle"))), 1)
            self.assertFalse(any(node.tag == ns + "rect" for node in extracted.iter()))
            self.assertFalse(any(node.tag == ns + "text" for node in extracted.iter()))

    def test_named_youssef_and_adam_export_aligned_articulated_vector_layers(self):
        repository = Path(__file__).resolve().parents[1]
        for character_id in ("youssef", "adam"):
            with self.subTest(character=character_id), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = repository / "assets" / "characters" / character_id / "design_sheet.svg"
                original = source.read_bytes()
                output = root / character_id
                manifest_path = prepare_named_character_layers(source, output, character_id)
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

                self.assertEqual(source.read_bytes(), original)
                self.assertTrue((output / "source_design_sheet.svg").is_file())
                self.assertTrue((output / "full_character_reference.svg").is_file())
                self.assertTrue((output / "rig_layers.svg").is_file())
                self.assertGreaterEqual(manifest["layer_count"], 14)
                self.assertEqual(manifest["rigging_status"],
                                 "vector_parts_segmented_at_existing_path_vertices_plastic_mesh_and_skeleton_not_yet_authored")
                self.assertIn("upper_arm_L", {layer["id"] for layer in manifest["layers"]})
                self.assertIn("forearm_R", {layer["id"] for layer in manifest["layers"]})
                self.assertIn("thigh_L", {layer["id"] for layer in manifest["layers"]})
                self.assertIn("shin_R", {layer["id"] for layer in manifest["layers"]})
                self.assertIn("torso_centerline", {layer["id"] for layer in manifest["layers"]})
                self.assertIn("head", {layer["id"] for layer in manifest["layers"]})
                for layer in manifest["layers"]:
                    layer_root = ET.parse(output / layer["file"]).getroot()
                    self.assertEqual(layer_root.get("viewBox"), "0 0 260 570")
                self.assertIn("left_elbow", manifest["joints"])
                self.assertIn("right_knee", manifest["joints"])

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
