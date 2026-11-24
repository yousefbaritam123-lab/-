import unittest
from pathlib import Path


class BlenderBridgeSyntaxTests(unittest.TestCase):
    def test_blender_script_compiles_without_blender_runtime(self):
        script = Path(__file__).resolve().parents[1] / "tools" / "blender_scene.py"
        compile(script.read_text(encoding="utf-8"), str(script), "exec")

    def test_procedural_puppets_have_independent_elbow_and_knee_controls(self):
        script = Path(__file__).resolve().parents[1] / "tools" / "blender_scene.py"
        source = script.read_text(encoding="utf-8")
        self.assertIn('elbows[suffix] = elbow', source)
        self.assertIn('knees[suffix] = knee', source)
        self.assertIn('for key, pivot in elbows.items()', source)
        self.assertIn('for key, pivot in knees.items()', source)
        self.assertIn('"_finger_"', source)
        self.assertIn('"_thumb_"', source)


if __name__ == "__main__":
    unittest.main()
