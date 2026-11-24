import json
import tempfile
import unittest
from pathlib import Path

from studio.script_qc import audit_dialogue


class ScriptQualityTests(unittest.TestCase):
    def project(self, root, dialogue):
        path = Path(root) / "episode.json"
        path.write_text(json.dumps({
            "id": "script-test",
            "characters": [{"id": "youssef", "name": "يوسف"}],
            "shots": [{"id": "shot-1", "duration_seconds": 5,
                       "actors": ["youssef"], "dialogue": dialogue}]
        }, ensure_ascii=False), encoding="utf-8")

    def test_valid_dialogue_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.project(tmp, [{"speaker": "youssef", "text": "واش راك اليوم؟",
                                "start_seconds": 0.5, "end_seconds": 2.0}])
            report = audit_dialogue(Path(tmp))
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["word_count"], 3)

    def test_missing_timing_and_overlap_are_blockers(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.project(tmp, [
                {"speaker": "youssef", "text": "الأول", "start_seconds": 0, "end_seconds": 2},
                {"speaker": "youssef", "text": "الثاني", "start_seconds": 1, "end_seconds": 3},
                {"speaker": "youssef", "text": "بدون توقيت"}
            ])
            report = audit_dialogue(Path(tmp))
            self.assertEqual(report["status"], "failed")
            self.assertTrue(any("overlap" in item for item in report["errors"]))
            self.assertTrue(any("start_seconds" in item for item in report["errors"]))


if __name__ == "__main__":
    unittest.main()
