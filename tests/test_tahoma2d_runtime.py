import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from studio.tahoma2d_runtime import render_tahoma2d_scene, _tahoma_environment


class Tahoma2DRuntimeTests(unittest.TestCase):
    def test_requires_native_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                render_tahoma2d_scene(Path(tmp) / "missing.tnz", Path(tmp) / "out.tif")

    def test_validates_frame_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            scene = Path(tmp) / "scene.tnz"
            scene.write_text("placeholder")
            with self.assertRaises(ValueError):
                render_tahoma2d_scene(scene, Path(tmp) / "out.tif", start_frame=0)

    def test_discovers_adjacent_tahoma_profile_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "Tahoma2D"
            binary = app / "usr" / "bin" / "tcomposer"
            stuff = app / "tahomastuff"
            binary.parent.mkdir(parents=True)
            binary.write_text("")
            (stuff / "profiles").mkdir(parents=True)
            with patch("studio.tahoma2d_runtime.shutil.which", return_value=None):
                env = _tahoma_environment(str(binary))
            self.assertEqual(env["TAHOMA2DROOT"], str(stuff))
            self.assertEqual(env["TAHOMA2DPROFILES"], str(stuff / "profiles"))
            self.assertEqual(env["TAHOMA2DPROJECTS"], str(stuff / "projects"))

    def test_invokes_batch_renderer_and_checks_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            scene = Path(tmp) / "scene.tnz"
            scene.write_text("placeholder")
            output = Path(tmp) / "renders" / "shot.tif"

            def fake_run(command, **kwargs):
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"x" * 2048)
                self.assertIn("env", kwargs)
                return Mock(returncode=0, stdout="rendered", stderr="")

            with patch("studio.tahoma2d_runtime.find_tcomposer", return_value="tcomposer"), patch(
                "studio.tahoma2d_runtime.subprocess.run", side_effect=fake_run
            ) as run:
                self.assertEqual(
                    render_tahoma2d_scene(scene, output, start_frame=1, end_frame=24, threads=2),
                    output,
                )
            command = run.call_args.args[0]
            self.assertIn("-range", command)
            self.assertEqual(
                command[command.index("-range") + 1:command.index("-range") + 3],
                ["1", "24"],
            )
            self.assertIn("-multimedia", command)
            self.assertTrue((output.parent / "tahoma2d_render.log").is_file())

    def test_runtime_report_when_missing(self):
        from studio.tahoma2d_runtime import tahoma2d_runtime_report
        with patch("studio.tahoma2d_runtime.find_tcomposer", side_effect=FileNotFoundError("missing")):
            self.assertFalse(tahoma2d_runtime_report()["available"])


if __name__ == "__main__":
    unittest.main()
