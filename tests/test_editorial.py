import json
import tempfile
import unittest
from pathlib import Path

from studio.editorial import build_subtitles, export_edit_plan


class EditorialTests(unittest.TestCase):
    def test_subtitles_use_episode_global_timing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "episode.json").write_text(json.dumps({
                "id": "ep1", "title": "حلقة",
                "format": {"fps": 30, "duration_seconds": 5},
                "characters": [{"id": "youssef", "name": "يوسف"}],
                "shots": [
                    {"id": "s1", "duration_seconds": 2, "dialogue": [{
                        "speaker": "youssef", "text": "السلام عليكم",
                        "start_seconds": 0.2, "end_seconds": 1.4
                    }]},
                    {"id": "s2", "duration_seconds": 3, "dialogue": [{
                        "speaker": "youssef", "text": "وعليكم السلام",
                        "start_seconds": 0.5, "end_seconds": 1.5
                    }]}
                ]
            }), encoding="utf-8")
            path = build_subtitles(root)
            content = path.read_text(encoding="utf-8-sig")
            self.assertIn("00:00:02,500 --> 00:00:03,500", content)
            self.assertIn("السلام عليكم", content)
            self.assertIn("وعليكم السلام", content)

    def test_edit_plan_has_exact_frame_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "episode.json").write_text(json.dumps({
                "id": "ep1", "title": "Test",
                "format": {"fps": 30, "duration_seconds": 3},
                "shots": [
                    {"id": "a", "duration_seconds": 1, "dialogue": []},
                    {"id": "b", "duration_seconds": 2, "dialogue": []}
                ]
            }), encoding="utf-8")
            path = export_edit_plan(root)
            plan = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(plan["shots"][1]["start_frame"], 30)
            self.assertEqual(plan["shots"][1]["duration_frames"], 60)


if __name__ == "__main__":
    unittest.main()
