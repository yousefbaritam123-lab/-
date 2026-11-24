import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from studio.audio import mix_episode_audio


class AudioMixTests(unittest.TestCase):
    def test_mixes_timed_clips_and_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "audio" / "dialogue").mkdir(parents=True)
            (root / "audio" / "dialogue" / "line.wav").write_bytes(b"audio")
            (root / "audio" / "dialogue" / "music.wav").write_bytes(b"music")
            (root / "episode.json").write_text(json.dumps({
                "id": "audio-test", "format": {"duration_seconds": 10}
            }), encoding="utf-8")
            (root / "production").mkdir()
            (root / "production" / "audio_mix.json").write_text(json.dumps({
                "tracks": [{"name": "dialogue", "gain_db": -2, "clips": [{
                    "file": "audio/dialogue/line.wav", "start_seconds": 1.5,
                    "end_seconds": 4.0, "gain_db": 1
                }]}, {"name": "music", "gain_db": -12, "clips": [{
                    "file": "audio/dialogue/music.wav", "start_seconds": 0,
                    "end_seconds": 10
                }]}]
            }), encoding="utf-8")
            def fake_run(command, **kwargs):
                output = Path(command[-1])
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"x" * 2048)
                return type("Result", (), {"returncode": 0, "stderr": ""})()
            with patch("imageio_ffmpeg.get_ffmpeg_exe", return_value="ffmpeg"), patch(
                "studio.audio.subprocess.run", side_effect=fake_run
            ) as run:
                result = mix_episode_audio(root)
            self.assertEqual(result, root / "audio" / "final_mix.wav")
            command = run.call_args.args[0]
            self.assertIn("adelay=1500|1500", " ".join(command))
            self.assertIn("loudnorm=I=-16:TP=-1.5:LRA=11", " ".join(command))
            self.assertIn("sidechaincompress=threshold=0.03", " ".join(command))
            report = json.loads((root / "production" / "audio_mix_report.json").read_text())
            self.assertEqual(report["clip_count"], 2)
            self.assertEqual(report["music_ducking"], "dialogue_sidechain")
            self.assertEqual(report["status"], "mixed")

    def test_rejects_paths_outside_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "episode.json").write_text(json.dumps({
                "id": "audio-test", "format": {"duration_seconds": 5}
            }), encoding="utf-8")
            (root / "production").mkdir()
            (root / "production" / "audio_mix.json").write_text(json.dumps({
                "tracks": [{"clips": [{"file": "../outside.wav"}]}]
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "inside"):
                mix_episode_audio(root)


if __name__ == "__main__":
    unittest.main()
