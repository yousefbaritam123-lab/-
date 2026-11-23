import tempfile
import unittest
from pathlib import Path

from studio.renderer import render_frame, shot_at


class RendererTests(unittest.TestCase):
    def test_shot_timeline_uses_local_time(self):
        shots = [
            {"id": "a", "duration_seconds": 2},
            {"id": "b", "duration_seconds": 3},
        ]
        shot, local = shot_at(shots, 2.5)
        self.assertEqual(shot["id"], "b")
        self.assertAlmostEqual(local, 0.5)

    def test_skia_renders_a_png_frame(self):
        episode = {
            "format": {"width": 320, "height": 568, "fps": 30, "duration_seconds": 1},
            "locations": [{"id": "street", "sky_top": "#78BCEB", "sky_bottom": "#F6D9B5"}],
            "characters": [{"id": "hero", "name": "Hero", "accent": "#C62828"}],
            "shots": [{
                "id": "shot-1", "duration_seconds": 1, "location": "street",
                "actors": ["hero"], "action": "wave", "dialogue": []
            }]
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "frame.png"
            render_frame(episode, 0.25, output)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 1000)
            self.assertEqual(output.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
