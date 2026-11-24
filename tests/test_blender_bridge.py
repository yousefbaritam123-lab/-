import json
import tempfile
import unittest
from pathlib import Path

from studio.blender_bridge import build_blender_manifest


class BlenderBridgeTests(unittest.TestCase):
    def test_manifest_carries_episode_and_resolved_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "episode.json").write_text(json.dumps({
                "id": "bridge-test",
                "format": {"width": 360, "height": 640, "fps": 30, "duration_seconds": 2},
                "characters": [{"id": "hero", "name": "Hero"}],
                "locations": [{"id": "street"}],
                "shots": [{"id": "shot-1", "actors": ["hero"]}],
            }), encoding="utf-8")
            manifest_path = build_blender_manifest(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], 2)
            self.assertEqual(manifest["episode_id"], "bridge-test")
            self.assertEqual(manifest["characters"][0]["id"], "hero")
            self.assertEqual(manifest["shots"][0]["id"], "shot-1")
            self.assertEqual(Path(manifest["output_root"]), root / "renders" / "blender")
            self.assertEqual(Path(manifest["catalog_path"]), root / "assets" / "characters" / "cast_60" / "catalog.json")

    def test_missing_episode_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(FileNotFoundError):
                build_blender_manifest(Path(temporary))


if __name__ == "__main__":
    unittest.main()
