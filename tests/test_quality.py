import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

from studio.cli import init_project
from studio.quality import audit_episode, certify_delivery


class QualityGateTests(unittest.TestCase):
    def project(self, root):
        p = Path(root) / "episode"
        init_project(p)
        path = p / "episode.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["format"].update({"width": 240, "height": 426, "fps": 30, "duration_seconds": 1})
        doc["shots"] = [{"id":"shot-001","duration_seconds":1,"location":"street_01",
                         "actors":["youssef"],"action":"idle","dialogue":[]}]
        path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        return p

    def frames(self, project):
        folder = project / "renders" / "frames"
        folder.mkdir(parents=True)
        for n in range(30):
            image = Image.new("RGB", (240, 426), (30+n, 70, 110))
            from PIL import ImageDraw
            ImageDraw.Draw(image).rectangle((20, 20, 90+n, 180), fill=(190, 130, 70))
            image.save(folder / f"frame_{n:06d}.png")

    def approve_and_add_audio(self, project):
        episode = json.loads((project / "episode.json").read_text(encoding="utf-8"))
        import wave
        with wave.open(str(project / "audio" / "final_mix.wav"), "wb") as audio:
            audio.setnchannels(2)
            audio.setsampwidth(3)
            audio.setframerate(48000)
            audio.writeframes(b"\x00" * (48000 * 6))
        approval = {"episode_id":episode["id"],"approved":True,
                    "reviewer":"QA reviewer","notes":"Watched full video and reviewed frames."}
        (project / "production" / "human_visual_approval.json").write_text(
            json.dumps(approval), encoding="utf-8")

    def test_missing_frames_block_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = audit_episode(self.project(tmp))
            self.assertFalse(report["delivery_eligible"])
            self.assertTrue(any("Incomplete render" in e for e in report["errors"]))

    def test_every_frame_is_checked_not_only_sparse_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(tmp)
            self.frames(p)
            Image.new("RGB", (120, 180), (30, 70, 110)).save(p / "renders/frames/frame_000017.png")
            report = audit_episode(p)
            self.assertTrue(any("incorrect dimensions" in e for e in report["errors"]))

    def test_corrupt_or_wrong_duration_audio_mix_blocks_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(tmp)
            self.frames(p)
            (p / "audio" / "final_mix.wav").write_bytes(b"not a wav file")
            report = audit_episode(p)
            self.assertFalse(report["delivery_eligible"])
            self.assertTrue(any("cannot be decoded" in error.lower() for error in report["errors"]))

    def test_delivery_requires_audio_and_human_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(tmp)
            self.frames(p)
            with self.assertRaisesRegex(RuntimeError, "Delivery blocked"):
                certify_delivery(p)

    def test_complete_reviewed_project_can_be_certified(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(tmp)
            self.frames(p)
            self.approve_and_add_audio(p)
            output = p / "renders" / "episode.mp4"
            output.parent.mkdir(parents=True, exist_ok=True)
            with patch("studio.media.encode_video", return_value=output):
                output.write_bytes(b"x" * 2048)
                with patch("studio.quality.shutil.which", return_value=None):
                    result = certify_delivery(p)
            self.assertEqual(result, output)
            manifest = json.loads((p / "production/delivery_manifest.json").read_text())
            self.assertEqual(manifest["status"], "delivered")


if __name__ == "__main__":
    unittest.main()
