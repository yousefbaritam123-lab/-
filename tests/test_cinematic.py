import json
import tempfile
import unittest
from pathlib import Path

from studio.blender_bridge import build_blender_manifest
from studio.cli import init_project
from studio.renderer import render_frame


class CinematicTests(unittest.TestCase):
    def test_environment_and_fx_render(self):
        episode = {
            "format": {"width": 320, "height": 568, "fps": 30, "duration_seconds": 1},
            "locations": [{"id": "room", "environment": "classroom", "weather": "fog"}],
            "characters": [{"id": "hero", "name": "Hero"}],
            "shots": [{
                "id": "shot", "duration_seconds": 1, "location": "room",
                "actors": ["hero"], "action": "wave", "dialogue": [],
                "effects": [{"type": "impact_flash", "start": 0.1, "duration": 0.3},
                            {"type": "speed_lines", "start": 0.2, "duration": 0.4}]
            }]
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "frame.png"
            render_frame(episode, .25, out)
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size, 1000)

    def test_blender_manifest_preserves_episode_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "episode"
            init_project(project)
            manifest_path = build_blender_manifest(project)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["format"]["width"], 1080)
            self.assertEqual(manifest["format"]["height"], 1920)
            self.assertEqual(manifest["format"]["duration_seconds"], 100)
            self.assertEqual(manifest["backend"], "blender_procedural_2d")


if __name__ == "__main__":
    unittest.main()
