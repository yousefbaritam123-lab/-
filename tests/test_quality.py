import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from studio.cli import init_project
from studio.quality import audit_episode, certify_delivery

class QualityGateTests(unittest.TestCase):
    def project(self, root):
        p = Path(root) / "episode"
        init_project(p)
        path = p / "episode.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["format"]["duration_seconds"] = 1
        doc["shots"] = [{"id":"shot-001","duration_seconds":1,"location":"street_01",
                         "actors":["youssef"],"action":"idle","dialogue":[]}]
        path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        return p

    def test_missing_frames_block_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = audit_episode(self.project(tmp))
            self.assertFalse(report["delivery_eligible"])
            self.assertTrue(any("Incomplete render" in e for e in report["errors"]))

    def test_complete_frames_pass_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(tmp)
            folder = p / "renders" / "frames"
            folder.mkdir(parents=True)
            for n in range(30):
                Image.new("RGB", (1080,1920), (30+n,70,110)).save(folder / f"frame_{n:06d}.png")
            report = audit_episode(p)
            self.assertTrue(report["delivery_eligible"], report["errors"])
            self.assertEqual(report["summary"]["found_frames"], 30)

    def test_finalize_refuses_incomplete_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                certify_delivery(self.project(tmp))

if __name__ == "__main__":
    unittest.main()
