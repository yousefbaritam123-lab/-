import unittest

from studio.rig import build_skeleton, sample_motion


class CharacterRigTests(unittest.TestCase):
    def test_motion_interpolates_and_loops(self):
        clip = {"clips": {"walk": {"duration": 2, "loop": True, "keyframes": [
            {"at": 0, "pose": {"left_leg": -20}},
            {"at": 1, "pose": {"left_leg": 20}},
        ]}}}
        first = sample_motion("walk", 0.25, clip)
        wrapped = sample_motion("walk", 2.25, clip)
        self.assertAlmostEqual(first["left_leg"], wrapped["left_leg"])
        self.assertGreater(first["left_leg"], -20)
        self.assertLess(first["left_leg"], 20)

    def test_skeleton_uses_character_proportions(self):
        pose = sample_motion("idle", 0)
        standard = build_skeleton(pose)
        tall = build_skeleton(pose, {"torso": 1.5, "upper_arm": 1.2})
        self.assertGreater(abs(tall["chest"][1]), abs(standard["chest"][1]))
        self.assertGreater(abs(tall["left_elbow"][1] - tall["left_shoulder"][1]),
                           abs(standard["left_elbow"][1] - standard["left_shoulder"][1]))

    def test_unknown_action_falls_back_to_idle(self):
        self.assertEqual(sample_motion("missing", .2), sample_motion("idle", .2))


if __name__ == "__main__":
    unittest.main()
