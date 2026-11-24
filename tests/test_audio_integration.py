import json
import math
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from studio.audio import mix_episode_audio
import imageio_ffmpeg


def write_tone(path: Path, seconds: float, frequency: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rate = 48000
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        frames = bytearray()
        for index in range(int(rate * seconds)):
            sample = int(5000 * math.sin(2 * math.pi * frequency * index / rate))
            frames.extend(sample.to_bytes(2, "little", signed=True))
        output.writeframes(frames)


class AudioIntegrationTests(unittest.TestCase):
    def test_ffmpeg_mixes_dialogue_music_and_effects_to_episode_length(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "episode.json").write_text(json.dumps({
                "id": "audio-integration",
                "format": {"duration_seconds": 3}
            }), encoding="utf-8")
            write_tone(root / "audio/dialogue/line.wav", 1.4, 440)
            write_tone(root / "audio/music/score.wav", 3.0, 220)
            write_tone(root / "audio/fx/step.wav", 0.5, 880)
            config = {
                "tracks": [
                    {"name": "dialogue", "gain_db": -2, "clips": [
                        {"file": "audio/dialogue/line.wav", "start_seconds": 0.2, "end_seconds": 1.6}
                    ]},
                    {"name": "music", "gain_db": -14, "clips": [
                        {"file": "audio/music/score.wav", "start_seconds": 0, "end_seconds": 3}
                    ]},
                    {"name": "effects", "gain_db": -6, "clips": [
                        {"file": "audio/fx/step.wav", "start_seconds": 1.8, "end_seconds": 2.3}
                    ]}
                ]
            }
            config_path = root / "production/audio_mix.json"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(json.dumps(config), encoding="utf-8")
            output = mix_episode_audio(root)
            self.assertTrue(output.is_file())
            probe = subprocess.run(
                [imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(output), "-f", "null", "-"],
                capture_output=True, text=True, check=False
            )
            self.assertEqual(probe.returncode, 0, probe.stderr[-2000:])
            self.assertIn("48000 Hz", probe.stderr)
            self.assertIn("stereo", probe.stderr)
            self.assertIn("s24", probe.stderr)
            report = json.loads((root / "production/audio_mix_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "mixed")
            self.assertEqual(report["buses"], ["dialogue", "effects", "music"])
            self.assertEqual(report["music_ducking"], "dialogue_sidechain")


if __name__ == "__main__":
    unittest.main()
