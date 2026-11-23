import json
import tempfile
import unittest
from pathlib import Path

from studio.assembly import assemble_storyboard
from studio.cli import init_project
from studio.director import build_storyboard
from studio.models import validate_episode


class AssemblyTests(unittest.TestCase):
    def test_storyboard_becomes_isolated_valid_animatic_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "episode-source"
            init_project(root)
            original = (root / "episode.json").read_text(encoding="utf-8")
            story_dir = root / "production" / "story"
            story_dir.mkdir(parents=True, exist_ok=True)
            outline = story_dir / "episode-001-outline.json"
            beats = [
                ("cold_open", 8), ("setup", 12), ("inciting_incident", 12),
                ("reaction", 12), ("escalation", 18), ("turning_point", 14),
                ("payoff", 14), ("cliffhanger", 10),
            ]
            outline.write_text(json.dumps({
                "episode_id": "episode-001",
                "beats": [
                    {"id": f"beat-{i}", "type": kind, "duration_seconds": seconds,
                     "writer_instruction": "blocking test"}
                    for i, (kind, seconds) in enumerate(beats, 1)
                ],
            }), encoding="utf-8")

            storyboard = build_storyboard(root, outline)
            assembled = assemble_storyboard(root, storyboard)
            self.assertEqual(validate_episode(assembled), [])
            episode = json.loads((assembled / "episode.json").read_text(encoding="utf-8"))
            self.assertEqual(len(episode["shots"]), 8)
            self.assertEqual(episode["format"]["duration_seconds"], 100)
            self.assertEqual(episode["production"]["stage"], "assembled_animatic_draft")
            self.assertFalse(episode["production"]["dialogue_complete"])
            self.assertEqual(episode["shots"][0]["motion_tracks"]["youssef"][0]["action"], "surprised")
            self.assertTrue((assembled / "assets" / "motions" / "motion_library.json").is_file())
            self.assertEqual((root / "episode.json").read_text(encoding="utf-8"), original)

    def test_assembly_refuses_to_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "episode-source"
            init_project(root)
            story_dir = root / "production" / "story"
            story_dir.mkdir(parents=True, exist_ok=True)
            storyboard = story_dir / "episode-001-storyboard.json"
            storyboard.write_text(json.dumps({
                "status": "director_blocking_pass_needs_screenwriter_and_director_review",
                "shots": [{"id": "one", "duration_seconds": 100, "actors": ["youssef"],
                           "location": "street_01", "motion_tracks": {"youssef": [
                               {"start": 0, "end": 100, "action": "idle"}
                           ]}}],
            }), encoding="utf-8")
            assemble_storyboard(root, storyboard)
            with self.assertRaises(FileExistsError):
                assemble_storyboard(root, storyboard)


if __name__ == "__main__":
    unittest.main()
