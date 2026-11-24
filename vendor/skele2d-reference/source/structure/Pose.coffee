import {lerpPoints} from "../helpers.coffee"

export default class Pose
	constructor: (def)->
		@points = {}
		if def?
			{points} = def
			for point_name, {x, y} of points
				@points[point_name] = {x, y}

	@lerp: (a, b, b_ness)->
		result = new Pose
		for point_name, point_a of a.points
			point_b = b.points[point_name]
			result.points[point_name] = lerpPoints(point_a, point_b, b_ness)
		result

	@lerpAnimationLoop: (frames, soft_index)->
		a = frames[(~~(soft_index) + 0) %% frames.length]
		b = frames[(~~(soft_index) + 1) %% frames.length]
		Pose.lerp(a, b, soft_index %% 1)
