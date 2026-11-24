from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from studio.cli import main


class Tahoma2DCommandTests(unittest.TestCase):
    def test_cli_prepares_named_cast_references_without_claiming_rigs(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "episode-001"
            self.assertEqual(main(["init", str(project)]), 0)
            self.assertEqual(main(["tahoma2d-prepare", str(project)]), 0)

            root = project / "production" / "tahoma2d" / "characters"
            for character_id in ("youssef", "adam"):
                folder = root / character_id
                manifest = json.loads(
                    (folder / "tahoma2d_character_manifest.json").read_text(encoding="utf-8")
                )
                self.assertTrue((folder / manifest["reference_art"]).is_file())
                self.assertEqual(
                    manifest["rigging_status"],
                    "reference_only_manual_layering_and_plastic_skeleton_required",
                )
                self.assertFalse(any(folder.glob("*.tnz")))


if __name__ == "__main__":
    unittest.main()
