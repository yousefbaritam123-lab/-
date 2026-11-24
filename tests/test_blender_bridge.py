import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from studio.blender_bridge import _rasterize_character_svg, build_blender_manifest


class BlenderBridgeTests(unittest.TestCase):
    def test_manifest_carries_episode_and_resolved_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "episode.json").write_text(json.dumps({
                "id": "bridge-test",
                "format": {"width": 360, "height": 640, "fps": 30, "duration_seconds": 2},
                "characters": [{"id": "hero", "name": "Hero"}],
                "locations": [{"id": "street"}],
                "shots": [{"id": "shot-1", "actors": ["hero"]}],
            }), encoding="utf-8")
            manifest_path = build_blender_manifest(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], 2)
            self.assertEqual(manifest["episode_id"], "bridge-test")
            self.assertEqual(manifest["characters"][0]["id"], "hero")
            self.assertEqual(manifest["shots"][0]["id"], "shot-1")
            self.assertEqual(Path(manifest["output_root"]), root / "renders" / "blender")
            self.assertEqual(Path(manifest["catalog_path"]), root / "assets" / "characters" / "cast_60" / "catalog.json")
            self.assertEqual(Path(manifest["prepared_cast_path"]), root / "assets" / "characters" / "prepared_cast_60")
            self.assertEqual(Path(manifest["cast_source_svg"]), root / "assets" / "characters" / "cast_60" / "contact_sheet.svg")

    def test_original_svg_rasterization_preserves_alpha_and_open_strokes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "character.svg"
            source.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 20 20">'
                '<path d="M2 2 L18 18" fill="none" stroke="#171923" stroke-width="4"/>'
                '<circle cx="10" cy="10" r="3" fill="#C62828"/>'
                '</svg>',
                encoding="utf-8",
            )
            output = _rasterize_character_svg(source)
            self.assertTrue(output.is_file())
            with Image.open(output) as image:
                image.load()
                self.assertEqual(image.size, (60, 60))
                self.assertEqual(image.mode, "RGBA")
                alpha = image.getchannel("A")
                self.assertLess(alpha.getextrema()[0], 255)
                self.assertGreater(alpha.getextrema()[1], 0)

    def test_missing_episode_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(FileNotFoundError):
                build_blender_manifest(Path(temporary))


if __name__ == "__main__":
    unittest.main()
