import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from studio.voice import generate_dialogue_audio


class VoiceGenerationTests(unittest.TestCase):
    def test_piper_generates_wavs_and_timed_mix_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "assets" / "voices").mkdir(parents=True)
            (root / "assets" / "voices" / "arabic.onnx").write_bytes(b"model")
            (root / "production").mkdir()
            (root / "production" / "voice_cast.json").write_text(json.dumps({
                "voices": {"youssef": {"model": "assets/voices/arabic.onnx"}}
            }), encoding="utf-8")
            (root / "episode.json").write_text(json.dumps({
                "id": "voice-test",
                "characters": [{"id": "youssef"}],
                "shots": [{"id": "s1", "duration_seconds": 3, "dialogue": [{
                    "speaker": "youssef", "text": "السلام عليكم",
                    "start_seconds": 0.5, "end_seconds": 2.0
                }]}]
            }, ensure_ascii=False), encoding="utf-8")
            def fake_run(command, **kwargs):
                output = Path(command[command.index("--output_file") + 1])
                output.parent.mkdir(parents=True, exist_ok=True)
                with wave.open(str(output), "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(16000)
                    wav.writeframes(b"\x00\x00" * 8000)
                return type("Result", (), {"returncode": 0, "stderr": ""})()
            with patch("studio.voice.shutil.which", return_value="piper"), patch(
                "studio.voice.subprocess.run", side_effect=fake_run
            ):
                mix_path = generate_dialogue_audio(root)
            plan = json.loads(mix_path.read_text(encoding="utf-8"))
            clip = plan["tracks"][0]["clips"][0]
            self.assertEqual(clip["start_seconds"], 0.5)
            self.assertEqual(clip["end_seconds"], 1.0)
            self.assertTrue((root / "audio/dialogue/s1_youssef_01.wav").is_file())

    def test_missing_voice_model_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "production").mkdir()
            (root / "production" / "voice_cast.json").write_text(json.dumps({
                "voices": {"youssef": {"model": "assets/missing.onnx"}}
            }), encoding="utf-8")
            (root / "episode.json").write_text(json.dumps({
                "id": "voice-test", "shots": [{
                    "id": "s1", "duration_seconds": 2, "dialogue": [{
                        "speaker": "youssef", "text": "مرحبا",
                        "start_seconds": 0, "end_seconds": 1
                    }]
                }]
            }), encoding="utf-8")
            with patch("studio.voice.shutil.which", return_value="piper"):
                with self.assertRaises(FileNotFoundError):
                    generate_dialogue_audio(root)


if __name__ == "__main__":
    unittest.main()
