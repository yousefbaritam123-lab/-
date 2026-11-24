import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from studio.image_character import prepare_character_image


class ImageCharacterPreparationTests(unittest.TestCase):
    def test_manifest_records_missing_optional_segmentation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.png"
            source.write_bytes(b"source")
            output = root / "character"
            def fake_remove(_source, destination):
                destination.write_bytes(b"transparent-cutout")
            with patch("studio.image_character._remove_background", side_effect=fake_remove), \
                 patch("studio.image_character._pose_landmarks", return_value=[]):
                manifest_path = prepare_character_image(source, output, "hero_01")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], 2)
            self.assertEqual(manifest["rig_status"], "needs_manual_layer_separation_and_rig_review")
            self.assertEqual(manifest["pose_landmarks"], [])
            self.assertIsNone(manifest["segmentation_mask"])

    def test_rejects_unsafe_character_identifier(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.png"
            source.write_bytes(b"source")
            with self.assertRaises(ValueError):
                prepare_character_image(source, root / "out", "../hero")


if __name__ == "__main__":
    unittest.main()
