import tempfile
import unittest
from pathlib import Path

from studio.tahoma2d_authoring import prepare_scene_levels, write_toonzscript


class Tahoma2DAuthoringTests(unittest.TestCase):
    def test_prepares_transparent_scene_levels_from_preserved_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for character in ("youssef", "adam"):
                folder = root / "production" / "tahoma2d" / "characters" / character
                folder.mkdir(parents=True)
                (folder / "full_character_reference.svg").write_text(
                    '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="200" viewBox="0 0 100 200">'
                    '<circle cx="50" cy="50" r="25" fill="#c62828"/></svg>', encoding="utf-8"
                )
            output = root / "authoring"
            levels = prepare_scene_levels(root, output)
            self.assertEqual(len(levels), 2)
            from PIL import Image
            with Image.open(levels[0]) as image:
                self.assertEqual(image.size, (1920, 1080))
                self.assertEqual(image.mode, "RGBA")
                self.assertGreater(image.getbbox()[2], 300)
            manifest = (output / "scene_input_manifest.json").read_text(encoding="utf-8")
            self.assertIn('"plastic_skeletons": "not_authored"', manifest)

    def test_writes_documented_toonzscript_that_saves_native_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            levels = []
            for name in ("youssef.png", "adam.png"):
                path = root / name
                path.write_bytes(b"png-level-placeholder")
                levels.append(path)
            script = write_toonzscript(root / "pilot.tnz", levels, root / "create_scene.js", frames=24)
            source = script.read_text(encoding="utf-8")
            self.assertIn("new Scene()", source)
            self.assertIn("scene.loadLevel", source)
            self.assertIn("scene.setCell(23, 1", source)
            self.assertIn("scene.save", source)


if __name__ == "__main__":
    unittest.main()
