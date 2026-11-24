import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from studio.frame_interpolation import interpolate_video


class FrameInterpolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "renders").mkdir()
        (self.root / "episode.json").write_text(json.dumps({
            "format": {"fps": 30}
        }), encoding="utf-8")
        self.source = self.root / "renders" / "episode.mp4"
        self.source.write_bytes(b"x" * 2048)

    def tearDown(self):
        self.temp.cleanup()

    def test_rejects_non_multiple_fps(self):
        with self.assertRaises(ValueError):
            interpolate_video(self.root, 50)

    def test_rejects_source_overwrite(self):
        with self.assertRaises(ValueError):
            interpolate_video(self.root, 60, output=self.source)

    @patch("imageio_ffmpeg.get_ffmpeg_exe", return_value="ffmpeg")
    @patch("studio.frame_interpolation.subprocess.run")
    def test_interpolates_and_decodes_before_publish(self, run, _ffmpeg):
        def fake_run(command, **kwargs):
            if "-vf" in command:
                Path(command[-1]).write_bytes(b"y" * 4096)
            return Mock(returncode=0, stderr="", stdout="")
        run.side_effect = fake_run
        result = interpolate_video(self.root, 60)
        self.assertEqual(result.name, "episode-60fps.mp4")
        self.assertTrue(result.is_file())
        first_command = run.call_args_list[0].args[0]
        self.assertIn("minterpolate=fps=60", first_command)
        self.assertTrue(any("-f" in call.args[0] for call in run.call_args_list))

    @patch("imageio_ffmpeg.get_ffmpeg_exe", return_value="ffmpeg")
    @patch("studio.frame_interpolation.subprocess.run")
    def test_failed_interpolation_preserves_source_and_removes_partial(self, run, _ffmpeg):
        run.return_value = Mock(returncode=1, stderr="filter unavailable", stdout="")
        with self.assertRaises(RuntimeError):
            interpolate_video(self.root, 60)
        self.assertTrue(self.source.is_file())
        self.assertFalse((self.root / "renders" / "episode-60fps.partial.mp4").exists())


if __name__ == "__main__":
    unittest.main()
