import json
import tempfile
import unittest
from pathlib import Path

from studio.cli import init_project
from studio.continuity import apply_episode_update, load_continuity, validate_continuity
from studio.models import read_json


class ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / "episode"
        init_project(self.project)
        self.episode = read_json(self.project / "episode.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_template_continuity_matches_episode_cast(self):
        self.assertEqual(validate_continuity(self.project, self.episode), [])

    def test_unknown_character_is_rejected(self):
        path = self.project / "continuity.json"
        ledger = load_continuity(self.project)
        ledger["character_state"]["ghost"] = {"wardrobe": "unknown"}
        path.write_text(json.dumps(ledger), encoding="utf-8")
        self.assertTrue(any("unknown character IDs" in e for e in validate_continuity(self.project, self.episode)))

    def test_explicit_update_advances_episode_and_preserves_other_state(self):
        apply_episode_update(
            self.project, self.episode,
            {"character_state": {"youssef": {"wardrobe": "jacket-red"}},
             "world_state": [{"id": "key-found", "status": "known"}]},
            expected_episode_number=1,
        )
        ledger = load_continuity(self.project)
        self.assertEqual(ledger["episode_number"], 2)
        self.assertEqual(ledger["previous_episode"], "episode-001")
        self.assertEqual(ledger["character_state"]["youssef"]["wardrobe"], "jacket-red")
        self.assertEqual(ledger["character_state"]["youssef"]["personality"], ["curious", "stubborn"])
        self.assertEqual(ledger["world_state"][0]["id"], "key-found")

    def test_stale_episode_update_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "Continuity conflict"):
            apply_episode_update(self.project, self.episode, {}, expected_episode_number=7)


if __name__ == "__main__":
    unittest.main()
