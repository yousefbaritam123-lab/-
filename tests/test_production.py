import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageDraw

from studio.cli import init_project
from studio.production import run_production


class IterativeProductionTests(unittest.TestCase):
    def make_project(self, root):
        project = Path(root) / "episode"
        init_project(project)
        episode_path = project / "episode.json"
        episode = json.loads(episode_path.read_text(encoding="utf-8"))
        episode["format"].update({"width": 240, "height": 426, "fps": 30, "duration_seconds": 2})
        episode["shots"] = [{
            "id": "shot-001", "duration_seconds": 2, "location": "street_01",
            "actors": ["youssef"], "action": "idle", "dialogue": []
        }]
        episode_path.write_text(json.dumps(episode, ensure_ascii=False), encoding="utf-8")
        import wave
        with wave.open(str(project / "audio" / "final_mix.wav"), "wb") as audio:
            audio.setnchannels(2)
            audio.setsampwidth(3)
            audio.setframerate(48000)
            audio.writeframes(b"\x00" * (48000 * 2 * 6))
        approval = {
            "episode_id": episode["id"], "approved": True,
            "reviewer": "QA reviewer", "notes": "Inspected the full contact sheet and playback."
        }
        (project / "production" / "human_visual_approval.json").write_text(
            json.dumps(approval), encoding="utf-8"
        )
        return project

    def fake_render(self, project, start, count, resume=True):
        folder = project / "renders" / "frames"
        folder.mkdir(parents=True, exist_ok=True)
        for n in range(start, start + count):
            image = Image.new("RGB", (240, 426), (35, 65, 90))
            draw = ImageDraw.Draw(image)
            draw.rectangle((10 + n, 20, 55 + n, 120), fill=(180, 110, 60))
            image.save(folder / f"frame_{n:06d}.png")
        return folder, count

    def test_production_runs_full_audit_then_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(tmp)
            output = project / "renders" / "episode.mp4"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"video")
            with patch("studio.production.render_episode_frames", side_effect=self.fake_render), \
                 patch("studio.production.certify_delivery", return_value=output):
                report = run_production(project)
            self.assertEqual(report["status"], "delivered")
            self.assertEqual(report["final_frame_audit"]["verified_frames"], 60)
            self.assertTrue(report["quality_policy"]["human_visual_signoff_required"])

    def test_production_recovers_after_transient_render_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(tmp)
            output = project / "renders" / "episode.mp4"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"video")
            calls = {"count": 0}

            def flaky_render(project_dir, start, count, resume=True):
                calls["count"] += 1
                if calls["count"] == 1:
                    folder = project_dir / "renders" / "frames"
                    folder.mkdir(parents=True, exist_ok=True)
                    (folder / "frame_000000.png").write_bytes(b"partial")
                    raise RuntimeError("simulated temporary render crash")
                return self.fake_render(project_dir, start, count, resume)

            with patch("studio.production.render_episode_frames", side_effect=flaky_render):
                with patch("studio.production.certify_delivery", return_value=output):
                    report = run_production(project, max_repair_rounds=3)

            self.assertEqual(report["status"], "delivered")
            self.assertEqual(calls["count"], 2)
            self.assertIn("simulated temporary render crash", report["rounds"][0]["render_error"])
            self.assertEqual(report["final_frame_audit"]["verified_frames"], 60)

    def test_invalid_audio_is_rebuilt_from_existing_mix_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(tmp)
            (project / "audio" / "final_mix.wav").write_bytes(b"corrupt")
            (project / "production" / "audio_mix.json").write_text(
                json.dumps({"tracks": [{"name": "music", "clips": []}]}), encoding="utf-8"
            )
            output = project / "renders" / "episode.mp4"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"video")

            def rebuild(project_dir, config_path=None):
                import wave
                with wave.open(str(project_dir / "audio" / "final_mix.wav"), "wb") as audio:
                    audio.setnchannels(2)
                    audio.setsampwidth(3)
                    audio.setframerate(48000)
                    audio.writeframes(b"\\x00" * (48000 * 2 * 6))
                return project_dir / "audio" / "final_mix.wav"

            with patch("studio.production.render_episode_frames", side_effect=self.fake_render):
                with patch("studio.audio.mix_episode_audio", side_effect=rebuild):
                    with patch("studio.production.certify_delivery", return_value=output):
                        report = run_production(project)

            self.assertEqual(report["status"], "delivered")
            self.assertEqual(report["audio_repair"]["status"], "repaired")

    def test_missing_audio_or_visual_signoff_blocks_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(tmp)
            (project / "audio" / "final_mix.wav").unlink()
            (project / "production" / "human_visual_approval.json").unlink()
            with patch("studio.production.render_episode_frames", side_effect=self.fake_render), \
                 patch("studio.production.certify_delivery") as certify:
                report = run_production(project)
            self.assertEqual(report["status"], "blocked")
            self.assertFalse(report["delivery_allowed"])
            self.assertTrue(any("audio" in error.lower() for error in report["errors"]))
            self.assertTrue(any("visual review" in error.lower() for error in report["errors"]))
            certify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
