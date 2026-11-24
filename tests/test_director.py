import json
import tempfile
import unittest
from pathlib import Path

from studio.director import build_storyboard


class DirectorTests(unittest.TestCase):
    def test_storyboard_converts_100_seconds_to_eight_editable_shots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "production" / "story").mkdir(parents=True)
            (root / "episode.json").write_text(json.dumps({
                "id": "series-ep-001",
                "format": {"duration_seconds": 100},
                "characters": [{"id": "youssef"}, {"id": "adam"}],
                "locations": [{"id": "street"}],
            }), encoding="utf-8")
            outline_path = root / "production" / "story" / "episode-001-outline.json"
            outline_path.write_text(json.dumps({
                "episode_id": "episode-001",
                "beats": [
                    {"id": f"b{i}", "type": kind, "duration_seconds": seconds,
                     "writer_instruction": "test"}
                    for i, (kind, seconds) in enumerate([
                        ("cold_open",8),("setup",12),("inciting_incident",12),("reaction",12),
                        ("escalation",18),("turning_point",14),("payoff",14),("cliffhanger",10)
                    ])
                ]
            }), encoding="utf-8")
            result_path = build_storyboard(root, outline_path)
            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["shot_count"], 8)
            self.assertEqual(result["total_duration_seconds"], 100)
            self.assertEqual(result["shots"][0]["motion_tracks"]["youssef"][0]["action"], "surprised")
            self.assertEqual(result["shots"][0]["motion_tracks"]["adam"][0]["action"], "listen")
            self.assertEqual(result["shots"][-1]["start_seconds"], 90)
            self.assertEqual(result["shots"][0]["shot_size"], "close_up")
            self.assertEqual(result["shots"][0]["focus_actor"], "youssef")
            self.assertEqual(result["shots"][0]["positions"]["youssef"]["x"], 345.6)
            self.assertEqual(result["shots"][1]["shot_size"], "wide")
            self.assertEqual(result["status"], "director_blocking_pass_needs_screenwriter_and_director_review")


if __name__ == "__main__":
    unittest.main()
