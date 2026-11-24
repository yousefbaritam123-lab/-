import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from studio.renderer import render_episode_frames, render_frame, shot_at
from studio.cli import init_project


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


    def test_episode_render_loads_rig_and_motion_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "episode"
            init_project(project)
            frame_dir, rendered = render_episode_frames(project, start_frame=0, max_frames=2)
            self.assertEqual(rendered, 2)
            self.assertTrue((frame_dir / "frame_000000.png").is_file())
            self.assertTrue((frame_dir / "frame_000001.png").is_file())


    def test_cast_catalog_profile_renders_by_cast_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "episode"
            init_project(project)
            episode_path = project / "episode.json"
            episode = json.loads(episode_path.read_text(encoding="utf-8"))
            episode["format"]["duration_seconds"] = 1
            episode["shots"] = [{
                "id": "cast-shot", "duration_seconds": 1, "location": "street_01",
                "actors": ["extra_actor"], "action": "wave", "dialogue": []
            }]
            episode["characters"] = [{
                "id": "extra_actor", "name": "Extra", "cast_id": "extra_001",
                "x": 270, "y": 730, "scale": 0.8
            }]
            episode_path.write_text(json.dumps(episode, ensure_ascii=False), encoding="utf-8")
            frame_dir, rendered = render_episode_frames(project, start_frame=0, max_frames=1)
            self.assertEqual(rendered, 1)
            self.assertGreater((frame_dir / "frame_000000.png").stat().st_size, 1000)

    def test_frame_render_retries_transient_failure_and_verifies_png(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "episode"
            init_project(project)
            real_render = render_frame
            calls = {"count": 0}

            def flaky_render(*args, **kwargs):
                calls["count"] += 1
                if calls["count"] == 1:
                    raise RuntimeError("temporary renderer fault")
                return real_render(*args, **kwargs)

            with patch("studio.renderer.render_frame", side_effect=flaky_render):
                folder, rendered = render_episode_frames(
                    project, start_frame=0, max_frames=1, frame_retries=1
                )
            self.assertEqual(rendered, 1)
            self.assertEqual(calls["count"], 2)
            with open(folder / "frame_000000.png", "rb") as stream:
                self.assertEqual(stream.read(8), b"\x89PNG\r\n\x1a\n")

    def test_renderer_retries_invalid_png_output(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "episode"
            init_project(project)
            real_render = render_frame
            calls = {"count": 0}

            def invalid_then_valid(*args, **kwargs):
                calls["count"] += 1
                if calls["count"] == 1:
                    Path(args[2]).write_bytes(b"not a png")
                    return
                return real_render(*args, **kwargs)

            with patch("studio.renderer.render_frame", side_effect=invalid_then_valid):
                folder, rendered = render_episode_frames(
                    project, start_frame=0, max_frames=1, frame_retries=1
                )
            self.assertEqual(rendered, 1)
            self.assertEqual(calls["count"], 2)
            with Image.open(folder / "frame_000000.png") as image:
                image.verify()

    def test_renderer_fails_after_retry_budget_and_leaves_no_partial_png(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "episode"
            init_project(project)

            def always_invalid(*args, **kwargs):
                Path(args[2]).write_bytes(b"partial")

            with patch("studio.renderer.render_frame", side_effect=always_invalid):
                with self.assertRaisesRegex(RuntimeError, "failed after 2 attempt"):
                    render_episode_frames(
                        project, start_frame=0, max_frames=1, frame_retries=1
                    )
            self.assertFalse((project / "renders" / "frames" / "frame_000000.png").exists())

    def test_resume_skips_existing_frames_and_repairs_empty_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "episode"
            init_project(project)
            frame_dir, first_count = render_episode_frames(project, start_frame=0, max_frames=2)
            self.assertEqual(first_count, 2)
            frame_dir.joinpath("frame_000001.png").write_bytes(b"")
            _, resumed_count = render_episode_frames(project, start_frame=0, max_frames=2, resume=True)
            self.assertEqual(resumed_count, 1)
            self.assertGreater(frame_dir.joinpath("frame_000001.png").stat().st_size, 1000)


    def test_catalog_profile_id_is_resolved_without_explicit_cast_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "episode"
            init_project(project)
            episode_path = project / "episode.json"
            episode = json.loads(episode_path.read_text(encoding="utf-8"))
            episode["format"]["duration_seconds"] = 1
            episode["shots"] = [{
                "id": "direct-catalog-shot", "duration_seconds": 1,
                "location": "street_01", "actors": ["extra_001"],
                "action": "wave", "dialogue": []
            }]
            episode["characters"] = [{
                "id": "extra_001", "name": "Extra 001",
                "x": 300, "y": 730, "scale": 0.8
            }]
            episode_path.write_text(json.dumps(episode, ensure_ascii=False), encoding="utf-8")
            frame_dir, rendered = render_episode_frames(project, start_frame=0, max_frames=1)
            self.assertEqual(rendered, 1)
            self.assertGreater((frame_dir / "frame_000000.png").stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
