import unittest
from pathlib import Path


class BlenderBridgeSyntaxTests(unittest.TestCase):
    def test_blender_script_compiles_without_blender_runtime(self):
        script = Path(__file__).resolve().parents[1] / "tools" / "blender_scene.py"
        compile(script.read_text(encoding="utf-8"), str(script), "exec")


if __name__ == "__main__":
    unittest.main()
