import json
import tempfile
import unittest
from pathlib import Path

from studio.cli import init_project
from studio.models import validate_episode
from studio.pipeline import build_production_plan


class StudioProjectTests(unittest.TestCase):
    def test_template_validates_and_builds_ten_departments(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "episode"
            init_project(project)
            self.assertEqual(validate_episode(project), [])
            plan_path = build_production_plan(project)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertEqual(len(plan["tasks"]), 10)
            self.assertEqual(plan["status"], "planning_only")

    def test_init_copies_canonical_character_and_motion_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "episode"
            init_project(project)
            self.assertTrue((project / "assets/characters/youssef/character.toon.json").is_file())
            self.assertTrue((project / "assets/characters/adam/design_sheet.svg").is_file())
            self.assertTrue((project / "assets/motions/motion_library.json").is_file())
            self.assertTrue((project / "assets/locations/algerian_neighborhood/location.json").is_file())

    def test_duplicate_character_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "episode"
            init_project(project)
            episode_path = project / "episode.json"
            doc = json.loads(episode_path.read_text(encoding="utf-8"))
            doc["characters"].append(dict(doc["characters"][0]))
            episode_path.write_text(json.dumps(doc), encoding="utf-8")
            self.assertTrue(any("Character IDs must be unique" in e for e in validate_episode(project)))

    def test_unknown_actor_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "episode"
            init_project(project)
            episode_path = project / "episode.json"
            doc = json.loads(episode_path.read_text(encoding="utf-8"))
            doc["shots"][0]["actors"] = ["ghost"]
            episode_path.write_text(json.dumps(doc), encoding="utf-8")
            self.assertTrue(any("unknown character" in e for e in validate_episode(project)))


if __name__ == "__main__":
    unittest.main()
