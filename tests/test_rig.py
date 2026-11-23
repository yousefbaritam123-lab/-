import unittest

from studio.rig import build_skeleton, facial_pose, sample_motion, solve_two_bone


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

    def test_two_bone_solver_respects_segment_lengths(self):
        elbow, end = solve_two_bone((0, 0), (100, 0), 60, 60, bend=1)
        self.assertAlmostEqual((elbow[0] ** 2 + elbow[1] ** 2) ** 0.5, 60, places=5)
        self.assertAlmostEqual(((end[0] - elbow[0]) ** 2 + (end[1] - elbow[1]) ** 2) ** 0.5, 60, places=5)

    def test_rig_exposes_wrist_fingers_and_toes(self):
        joints = build_skeleton(sample_motion("wave", .4))
        for key in ("left_wrist", "right_wrist", "left_fingers", "right_fingers",
                    "left_toe", "right_toe"):
            self.assertIn(key, joints)
        self.assertEqual(len(joints["right_fingers"]), 5)

    def test_joint_limits_prevent_unphysical_extremes(self):
        pose = sample_motion("idle", 0)
        pose["right_arm"] = 900
        pose["right_elbow"] = 900
        joints = build_skeleton(pose, {"joint_limits": {
            "shoulder": [-90, 90], "elbow": [-45, 45]
        }})
        shoulder = joints["right_shoulder"]
        elbow = joints["right_elbow"]
        self.assertLessEqual(abs(elbow[0] - shoulder[0]), 92.1)

    def test_ik_targets_drive_wrist_and_ankle(self):
        pose = sample_motion("idle", 0)
        pose.update({"right_hand_target_x": 95, "right_hand_target_y": 45,
                     "left_ankle_target_x": -45, "left_ankle_target_y": 165})
        joints = build_skeleton(pose)
        self.assertAlmostEqual(joints["right_wrist"][0], 95, places=5)
        self.assertAlmostEqual(joints["right_wrist"][1], 45, places=5)
        self.assertAlmostEqual(joints["left_foot"][0], -45, places=5)
        self.assertAlmostEqual(joints["left_foot"][1], 165, places=5)

    def test_facial_controls_clamp_gaze_and_blink(self):
        face = facial_pose({"gaze_x": 10, "gaze_y": -10, "blink": 4, "emotion": 1}, .5)
        self.assertEqual(face["gaze_x"], 1)
        self.assertEqual(face["gaze_y"], -1)
        self.assertEqual(face["blink"], 1)
        self.assertGreater(face["brow"], 0)

    def test_new_emotion_clips_are_available(self):
        for action in ("point", "think", "celebrate", "sad", "surprised"):
            pose = sample_motion(action, .3)
            self.assertIn("emotion", pose)
            self.assertIn("right_wrist", pose)

    def test_unknown_action_falls_back_to_idle(self):
        self.assertEqual(sample_motion("missing", .2), sample_motion("idle", .2))


if __name__ == "__main__":
    unittest.main()
