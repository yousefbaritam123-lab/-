import json
import tempfile
import unittest
from pathlib import Path

from studio.cast import add_cast_character, list_cast_profiles
from studio.cli import init_project


class CastIntegrationTests(unittest.TestCase):
    def test_lists_all_sixty_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "episode"
            init_project(project)
            profiles = list_cast_profiles(project)
            self.assertEqual(len(profiles), 60)
            self.assertEqual(len({item["id"] for item in profiles}), 60)

    def test_adds_profile_to_episode_and_shot(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "episode"
            init_project(project)
            actor = add_cast_character(project, 'extra_001', shot_id='shot-001',
                                       actor_id='market_vendor', x=720, action='wave')
            episode = json.loads((project / "episode.json").read_text(encoding="utf-8"))
            self.assertEqual(actor["cast_id"], "extra_001")
            self.assertIn("shirt", actor["appearance"])
            self.assertIn("market_vendor", episode["shots"][0]["actors"])
            saved = next(item for item in episode["characters"] if item["id"] == "market_vendor")
            self.assertEqual(saved["rig"], "assets/characters/youssef/character.toon.json")

    def test_unknown_cast_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "episode"
            init_project(project)
            with self.assertRaises(KeyError):
                add_cast_character(project, "not-a-real-character")


if __name__ == "__main__":
    unittest.main()
