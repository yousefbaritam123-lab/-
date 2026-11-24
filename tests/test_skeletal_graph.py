import unittest

from studio.skeletal_graph import Pose, SkeletonGraph


class SkeletalGraphTests(unittest.TestCase):
    def setUp(self):
        self.graph = SkeletonGraph.from_rig(
            {"shoulder": [0, 0], "elbow": [0, 10], "wrist": [0, 20]},
            [
                {"name": "upper_arm", "parent": "shoulder", "child": "elbow"},
                {"name": "forearm", "parent": "elbow", "child": "wrist"},
            ],
        )

    def test_rig_definition_round_trips_as_named_graph(self):
        data = self.graph.to_dict()
        self.assertEqual(data["segments"]["forearm"], {"from": "elbow", "to": "wrist"})
        self.assertEqual(data["points"]["elbow"], {"x": 0.0, "y": 10.0})

    def test_pose_loop_interpolates_last_to_first(self):
        a = Pose({"joint": {"x": 0, "y": 0}})
        b = Pose({"joint": {"x": 10, "y": 20}})
        result = Pose.loop([a, b], 1.5)
        self.assertEqual(result.points["joint"], {"x": 5.0, "y": 10.0})

    def test_pose_flip_preserves_other_axis(self):
        pose = Pose({"joint": {"x": 4, "y": 8}})
        flipped = pose.flipped(horizontal=True, center_x=10)
        self.assertEqual(flipped.points["joint"], {"x": 16.0, "y": 8.0})

    def test_rejects_missing_joint_references(self):
        with self.assertRaises(ValueError):
            SkeletonGraph({"a": {"x": 0, "y": 0}}, {"bone": {"from": "a", "to": "b"}})

    def test_rejects_non_finite_coordinates(self):
        with self.assertRaises(ValueError):
            Pose({"joint": {"x": float("nan"), "y": 0}})


if __name__ == "__main__":
    unittest.main()
