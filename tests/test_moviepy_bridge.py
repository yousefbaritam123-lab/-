import json
import tempfile
import unittest
from pathlib import Path

from studio.moviepy_bridge import load_timeline


class MoviePyTimelineTests(unittest.TestCase):
    def test_loads_project_relative_clips_and_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "renders").mkdir()
            (root / "renders" / "shot.mp4").write_bytes(b"video")
            timeline = root / "production" / "timeline.json"
            timeline.parent.mkdir()
            timeline.write_text(json.dumps({
                "fps": 30, "clips": [{
                    "source": "renders/shot.mp4", "start_seconds": 0.2,
                    "end_seconds": 1.2, "transition_in_seconds": 0.1
                }]
            }), encoding="utf-8")
            spec = load_timeline(root, timeline)
            self.assertEqual(spec["fps"], 30)
            self.assertEqual(spec["clips"][0]["end_seconds"], 1.2)
            self.assertEqual(spec["output"], root / "renders" / "moviepy-final.mp4")

    def test_rejects_paths_outside_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root.parent / "outside-moviepy-test.mp4"
            outside.write_bytes(b"video")
            timeline = root / "timeline.json"
            timeline.write_text(json.dumps({
                "clips": [{"source": "../outside-moviepy-test.mp4"}]
            }), encoding="utf-8")
            try:
                with self.assertRaises(ValueError):
                    load_timeline(root, timeline)
            finally:
                outside.unlink(missing_ok=True)

    def test_rejects_empty_timeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            timeline = root / "timeline.json"
            timeline.write_text('{"clips": []}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_timeline(root, timeline)

    def test_real_moviepy_render_and_crossfade(self):
        try:
            from moviepy import ColorClip, VideoFileClip
        except ImportError:
            self.skipTest("MoviePy optional dependency is not installed")
        from studio.moviepy_bridge import compose_moviepy_timeline

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            renders = root / "renders"
            renders.mkdir()
            for name, color in (("a.mp4", (220, 40, 40)), ("b.mp4", (40, 40, 220))):
                clip = ColorClip(size=(48, 48), color=color, duration=0.6)
                clip.write_videofile(
                    str(renders / name), fps=10, codec="libx264",
                    audio=False, logger=None,
                )
                clip.close()
            timeline = root / "timeline.json"
            timeline.write_text(json.dumps({
                "fps": 10,
                "output": "renders/final.mp4",
                "clips": [
                    {"source": "renders/a.mp4", "transition_in_seconds": 0},
                    {"source": "renders/b.mp4", "transition_in_seconds": 0.2}
                ]
            }), encoding="utf-8")
            output = compose_moviepy_timeline(root, timeline)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 1024)
            rendered = VideoFileClip(str(output))
            try:
                self.assertAlmostEqual(rendered.duration, 1.0, delta=0.15)
                self.assertEqual(rendered.size, (48, 48))
            finally:
                rendered.close()


if __name__ == "__main__":
    unittest.main()
