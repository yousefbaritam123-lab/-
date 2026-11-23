import json, tempfile, unittest
from pathlib import Path
from studio.lipsync import convert_rhubarb_data
from studio.story import build_next_episode_outline

class LipSyncTests(unittest.TestCase):
    def test_rhubarb_mapping_and_order(self):
        data={"mouthCues":[{"start":.4,"end":.7,"value":"B"},{"start":0,"end":.4,"value":"A"}]}
        self.assertEqual(convert_rhubarb_data(data),[{"at":0.0,"shape":"A"},{"at":.4,"shape":"CLOSED"}])
    def test_unknown_shape_fails(self):
        with self.assertRaises(ValueError):
            convert_rhubarb_data({"mouthCues":[{"start":0,"value":"?"}]})

class StoryTests(unittest.TestCase):
    def test_outline_100s_and_ledger_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/"production").mkdir()
            (root/"episode.json").write_text(json.dumps({"id":"ep-current","language":"ar-DZ","characters":[{"id":"youssef"}]}),encoding="utf-8")
            ledger={"series_id":"test","episode_number":4,"previous_episode":"episode-003","character_state":{"youssef":{"wardrobe":"red"}},"world_state":["school tomorrow"],"unresolved_threads":["Who took the notebook?"]}
            path=root/"continuity.json"; original=json.dumps(ledger); path.write_text(original,encoding="utf-8")
            outline=json.loads(build_next_episode_outline(root).read_text(encoding="utf-8"))
            self.assertEqual(sum(b["duration_seconds"] for b in outline["beats"]),100)
            self.assertEqual(outline["central_thread"],"Who took the notebook?")
            self.assertEqual(path.read_text(encoding="utf-8"),original)

if __name__=="__main__": unittest.main()
