import unittest

from studio.motion_library import active_track_segment, resolve_motion, validate_motion_track


class MotionLibraryTests(unittest.TestCase):
    def test_catalogue_alias_resolves_to_shared_rig_clip(self):
        self.assertEqual(resolve_motion("greet")[0], "wave")
        self.assertEqual(resolve_motion("hit_react")[0], "impact_react")

    def test_track_selects_segment_and_local_clock(self):
        track = [
            {"start": 0, "end": 2, "action": "walk"},
            {"start": 2, "end": 5, "action": "greet"},
        ]
        segment, local = active_track_segment(track, 3.25)
        self.assertEqual(segment["action"], "greet")
        self.assertAlmostEqual(local, 1.25)

    def test_track_is_random_access_and_gap_returns_no_segment(self):
        track = [{"start": 2, "end": 4, "action": "walk"}]
        self.assertIsNone(active_track_segment(track, 1)[0])
        self.assertEqual(active_track_segment(track, 8)[0]["action"], "walk")

    def test_overlapping_or_out_of_range_segments_are_rejected(self):
        errors = validate_motion_track([
            {"start": 0, "end": 3, "action": "walk"},
            {"start": 2, "end": 4, "action": "talk"},
        ], 5)
        self.assertTrue(any("overlaps" in item for item in errors))
        self.assertTrue(validate_motion_track([{"start": 0, "end": 8, "action": "walk"}], 5))


if __name__ == "__main__":
    unittest.main()
