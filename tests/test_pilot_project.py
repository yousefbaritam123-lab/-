import json
import tempfile
import unittest
from pathlib import Path

from studio.cli import init_project
from studio.models import validate_episode


class ShortFormPilotTests(unittest.TestCase):
    def test_fifteen_second_vertical_preview_is_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "pilot"
            init_project(project)
            episode_path = project / "episode.json"
            doc = json.loads(episode_path.read_text(encoding="utf-8"))
            doc["format"].update({"width": 540, "height": 960, "duration_seconds": 15})
            doc["shots"] = [
                {"id": "a", "duration_seconds": 5, "location": "street_01", "actors": ["youssef"], "action": "walk", "dialogue": []},
                {"id": "b", "duration_seconds": 5, "location": "street_01", "actors": ["youssef", "adam"], "action": "wave", "dialogue": []},
                {"id": "c", "duration_seconds": 5, "location": "street_01", "actors": ["youssef", "adam"], "action": "talk", "dialogue": []},
            ]
            episode_path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(validate_episode(project), [])

    def test_non_portrait_format_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "pilot"
            init_project(project)
            episode_path = project / "episode.json"
            doc = json.loads(episode_path.read_text(encoding="utf-8"))
            doc["format"].update({"width": 960, "height": 540})
            episode_path.write_text(json.dumps(doc), encoding="utf-8")
            self.assertTrue(any("9:16" in error for error in validate_episode(project)))


if __name__ == "__main__":
    unittest.main()
