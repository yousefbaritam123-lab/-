import json
import tempfile
import unittest
from pathlib import Path

from studio.characters import load_character_catalog, make_episode_character


class CharacterCatalogTests(unittest.TestCase):
    def test_catalog_has_sixty_unique_profiles(self):
        path = Path("assets/characters/cast_60/catalog.json")
        data = load_character_catalog(path)
        self.assertEqual(len(data["characters"]), 60)
        self.assertEqual(len({c["id"] for c in data["characters"]}), 60)

    def test_profile_becomes_episode_ready_actor(self):
        actor = make_episode_character(
            Path("assets/characters/cast_60/catalog.json"),
            "extra_001",
            x=300,
            action="walk",
        )
        self.assertEqual(actor["rig"], "assets/characters/youssef/character.toon.json")
        self.assertEqual(actor["x"], 300)
        self.assertEqual(actor["action"], "walk")
        self.assertIn("shirt", actor["appearance"])


if __name__ == "__main__":
    unittest.main()
