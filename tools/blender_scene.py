"""Render an episode as a procedural 2D cartoon in Blender.

The renderer builds a reusable articulated puppet from Blender curves/meshes.
It is a real render path (PNG sequence + MP4), not merely a .blend bootstrap.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy


def rgba(hex_color, fallback=(0.2, 0.2, 0.2, 1.0)):
    if not isinstance(hex_color, str) or not hex_color.startswith("#") or len(hex_color) != 7:
        return fallback
    return tuple(int(hex_color[i:i + 2], 16) / 255.0 for i in (1, 3, 5)) + (1.0,)


def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = color
    emission.inputs["Strength"].default_value = 1.0
    mat.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return mat


def attach(obj, parent):
    obj.parent = parent
    return obj


def make_line(name, points, bevel, mat, parent, z=0.0):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = bevel
    curve.bevel_resolution = 3
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, (x, y) in zip(spline.points, points):
        point.co = (x, y, z, 1)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    attach(obj, parent)
    return obj


def make_disc(name, x, y, rx, ry, mat, parent, z=0.1):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1,
                                        location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (rx, ry, 0.035)
    obj.location = (x, y, z)
    obj.data.materials.append(mat)
    attach(obj, parent)
    return obj


def make_pivot(name, parent, location):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.empty_display_type = "PLAIN_AXES"
    obj.location = location
    attach(obj, parent)
    return obj


def make_limb(name, pivot, length, mat, thickness, direction=-1):
    end = (0.0, direction * length)
    line = make_line(name, [(0, 0), end], thickness, mat, pivot, z=0.12)
    joint = make_disc(name + "_joint", 0, 0, thickness * 1.25, thickness * 1.25,
                      mat, pivot, z=0.15)
    return line, joint


def make_box(name, location, scale, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    return obj


def build_location(location, width, height):
    """Create a small reusable 2D environment set from the location bible."""
    location_id = str(location.get("id", "location"))
    kind = (str(location.get("environment", "")) + " " +
            str(location.get("type", "")) + " " +
            str(location.get("id", "")) + " " +
            str(location.get("name", ""))).lower()
    objects = []
    sky = material(location_id + "_sky", rgba(location.get("sky_bottom", "#D9E3EA")))
    ground = material(location_id + "_ground", rgba(location.get("ground", "#647D62")))
    objects.append(make_box(location_id + "_sky", (0, 0, -1.1),
                            (width / 100.0 * 2.0, height / 100.0 * 2.0, 0.05), sky))
    objects.append(make_box(location_id + "_ground", (0, -height / 200.0 + 0.18, -0.55),
                            (width / 100.0 * 2.0, 0.42, 0.16), ground))
    if any(word in kind for word in ("class", "school", "room", "interior")):
        wall = material(location_id + "_wall", rgba(location.get("wall", "#E8DFCB")))
        board = material(location_id + "_board", rgba(location.get("board", "#244C45")))
        wood = material(location_id + "_wood", rgba(location.get("wood", "#986B45")))
        objects.append(make_box(location_id + "_back_wall", (0, 0.1, -0.9),
                                (width / 100.0 * 2.0, height / 100.0 * 1.9, 0.08), wall))
        objects.append(make_box(location_id + "_blackboard", (0, 0.55, -0.55),
                                (1.55, 0.78, 0.08), board))
        for desk_x in (-0.95, 0.0, 0.95):
            objects.append(make_box(location_id + "_desk", (desk_x, -1.75, -0.2),
                                    (0.62, 0.08, 0.42), wood))
            objects.append(make_box(location_id + "_desk_leg", (desk_x, -2.05, -0.2),
                                    (0.055, 0.55, 0.055), wood))
    elif any(word in kind for word in ("beach", "sea", "coast")):
        sea = material(location_id + "_sea", rgba(location.get("water", "#4C9FC0")))
        sand = material(location_id + "_sand", rgba(location.get("sand", "#E8D19B")))
        objects.append(make_box(location_id + "_sea", (0, -1.15, -0.82),
                                (width / 100.0 * 2.0, 1.25, 0.08), sea))
        objects.append(make_box(location_id + "_sand", (0, -2.45, -0.72),
                                (width / 100.0 * 2.0, 0.55, 0.08), sand))
    elif any(word in kind for word in ("park", "garden", "forest")):
        trunk = material(location_id + "_trunk", rgba("#795B3B"))
        leaves = material(location_id + "_leaves", rgba("#477D4E"))
        for index, x in enumerate((-1.35, 1.35)):
            objects.append(make_box(location_id + "_tree_trunk_" + str(index),
                                    (x, -1.15, -0.45), (0.16, 2.0, 0.16), trunk))
            objects.append(make_disc(location_id + "_tree_top_" + str(index),
                                     x, -0.12, 0.58, 0.66, leaves, None, -0.35))
        bench = material(location_id + "_bench", rgba("#986B45"))
        objects.append(make_box(location_id + "_bench_seat", (0, -1.65, -0.25),
                                (0.85, 0.12, 0.22), bench))
    elif any(word in kind for word in ("roof", "rooftop", "terrace")):
        cement = material(location_id + "_cement", rgba("#B7B5AC"))
        objects.append(make_box(location_id + "_parapet", (0, -1.65, -0.58),
                                (width / 100.0 * 2.0, 0.55, 0.12), cement))
        for x in (-1.25, 1.25):
            objects.append(make_box(location_id + "_neighbor_block", (x, 0.2, -0.9),
                                    (0.72, 2.4, 0.14), material(location_id + "_neighbor_" + str(x), rgba("#B9A18A"))))
    else:
        # Neighborhood street: varied building heights, windows, door and lamp.
        facade_colors = ("#C9B49B", "#D7C4A8", "#AFAFA4")
        for index, x in enumerate((-1.35, 1.35, 0.0)):
            facade = material(location_id + "_facade_" + str(index),
                              rgba(location.get("building", facade_colors[index])))
            building_height = (2.4, 1.9, 1.35)[index]
            objects.append(make_box(location_id + "_building_" + str(index),
                                    (x, -0.8 + building_height * 0.5, -0.88),
                                    (0.72, building_height, 0.12), facade))
            window = material(location_id + "_window_" + str(index), rgba("#7DB3C9"))
            for row in range(2):
                for col in (-1, 1):
                    objects.append(make_box(location_id + "_window",
                                            (x + col * 0.18, -0.35 + row * 0.62, -0.79),
                                            (0.13, 0.20, 0.035), window))
        door = material(location_id + "_door", rgba("#684A35"))
        objects.append(make_box(location_id + "_door", (-1.35, -1.75, -0.72),
                                (0.25, 0.65, 0.06), door))
        lamp = material(location_id + "_lamp", rgba("#3B4147"))
        objects.append(make_box(location_id + "_street_lamp", (1.55, -0.15, -0.55),
                                (0.045, 2.6, 0.05), lamp))
    for obj in objects:
        obj.hide_render = True
        obj.keyframe_insert(data_path="hide_render", frame=1)
    return objects


def set_pose(actor, action, frame, end_frame=None, fps=30):
    arms = actor["arms"]
    legs = actor["legs"]
    elbows = actor.get("elbows", {})
    knees = actor.get("knees", {})
    end_frame = max(frame, int(end_frame if end_frame is not None else frame))
    if action in ("walk", "run"):
        period = 0.80 if action == "walk" else 0.48
        step = max(1, round(fps * period / 8))
        frames = list(range(frame, end_frame + 1, step))
        if not frames or frames[-1] != end_frame:
            frames.append(end_frame)
        for key, pivot in arms.items():
            phase = 0.0 if key.endswith("L") else math.pi
            for current in frames:
                elapsed = (current - frame) / fps
                pivot.rotation_euler[2] = math.radians(18) * math.sin(2 * math.pi * elapsed / period + phase)
                pivot.keyframe_insert(data_path="rotation_euler", frame=current)
        for key, pivot in legs.items():
            phase = 0.0 if key.endswith("L") else math.pi
            for current in frames:
                elapsed = (current - frame) / fps
                pivot.rotation_euler[2] = math.radians(24) * math.sin(2 * math.pi * elapsed / period + phase)
                pivot.keyframe_insert(data_path="rotation_euler", frame=current)
        for key, pivot in elbows.items():
            phase = 0.0 if key.endswith("L") else math.pi
            for current in frames:
                elapsed = (current - frame) / fps
                bend = 12 + 12 * math.sin(2 * math.pi * elapsed / period + phase)
                pivot.rotation_euler[2] = math.radians(bend)
                pivot.keyframe_insert(data_path="rotation_euler", frame=current)
        for key, pivot in knees.items():
            phase = 0.0 if key.endswith("L") else math.pi
            for current in frames:
                elapsed = (current - frame) / fps
                bend = 8 + 18 * max(0.0, math.sin(2 * math.pi * elapsed / period + phase))
                pivot.rotation_euler[2] = math.radians(bend)
                pivot.keyframe_insert(data_path="rotation_euler", frame=current)
        return

    for key, pivot in arms.items():
        angle = 0.0
        if action in ("wave", "greet"):
            angle = math.radians(-115 if key.endswith("L") else 115)
        elif action in ("point", "explain"):
            angle = math.radians(-68 if key.endswith("L") else 68)
        elif action in ("celebrate", "celebrate_small", "jump"):
            angle = math.radians(-145 if key.endswith("L") else 145)
        elif action in ("think", "listen"):
            angle = math.radians(-35 if key.endswith("L") else 20)
        elif action in ("sad", "apologize"):
            angle = math.radians(22 if key.endswith("L") else -22)
        pivot.rotation_euler[2] = angle
        pivot.keyframe_insert(data_path="rotation_euler", frame=frame)
        if action in ("wave", "greet") and key.endswith("R"):
            wave_step = max(1, round(fps * 0.12))
            frames = list(range(frame, end_frame + 1, wave_step))
            if not frames or frames[-1] != end_frame:
                frames.append(end_frame)
            for current in frames:
                elapsed = (current - frame) / fps
                pivot.rotation_euler[2] = angle + math.radians(24) * math.sin(2 * math.pi * elapsed / 0.48)
                pivot.keyframe_insert(data_path="rotation_euler", frame=current)
    for key, pivot in legs.items():
        angle = math.radians(-52 if key.endswith("L") else 52) if action == "kick" else 0.0
        pivot.rotation_euler[2] = angle
        pivot.keyframe_insert(data_path="rotation_euler", frame=frame)
        pivot.keyframe_insert(data_path="rotation_euler", frame=end_frame)
    elbow_bends = {
        "wave": 28, "greet": 28, "point": 12, "explain": 24,
        "think": 72, "listen": 34, "celebrate": 22,
        "celebrate_small": 18, "jump": 18, "sad": 12,
        "apologize": 35, "laugh": 20, "talk": 16,
    }
    for key, pivot in elbows.items():
        bend = elbow_bends.get(action, 5)
        if action in ("wave", "greet") and key.endswith("R"):
            bend += 10
        pivot.rotation_euler[2] = math.radians(bend)
        pivot.keyframe_insert(data_path="rotation_euler", frame=frame)
        pivot.keyframe_insert(data_path="rotation_euler", frame=end_frame)
    for key, pivot in knees.items():
        bend = 48 if action == "kick" and key.endswith("L") else (8 if action in ("jump", "dodge") else 0)
        pivot.rotation_euler[2] = math.radians(bend)
        pivot.keyframe_insert(data_path="rotation_euler", frame=frame)
        pivot.keyframe_insert(data_path="rotation_euler", frame=end_frame)


def set_face(actor, action, frame):
    mouth = "REST"
    brow_angle = 0.0
    if action in ("talk", "explain"):
        mouth = "A"
    elif action in ("laugh", "celebrate", "celebrate_small", "agree"):
        mouth = "SMILE"
    elif action in ("sad", "apologize"):
        mouth = "FROWN"
        brow_angle = 0.18
    elif action in ("surprised", "impact_react", "jump"):
        mouth = "O"
        brow_angle = -0.20
    elif action in ("disagree", "angry"):
        mouth = "E"
        brow_angle = 0.28
    for name, obj in actor.get("mouths", {}).items():
        obj.hide_render = name != mouth
        obj.keyframe_insert(data_path="hide_render", frame=frame)
    for suffix, brow in actor.get("brows", {}).items():
        brow.rotation_euler[2] = brow_angle if suffix == "L" else -brow_angle
        brow.keyframe_insert(data_path="rotation_euler", frame=frame)


def set_viseme(actor, shape, frame):
    shape = str(shape).upper()
    if shape not in actor.get("mouths", {}):
        shape = "REST"
    for name, obj in actor.get("mouths", {}).items():
        obj.hide_render = name != shape
        obj.keyframe_insert(data_path="hide_render", frame=frame)



def build_character(actor, profile, width, height):
    actor_id = str(actor["id"])
    appearance = dict(profile.get("appearance", {}))
    appearance.update(actor.get("appearance", {}))
    proportions = dict(profile.get("proportions", {}))
    proportions.update(actor.get("proportions", {}))
    skin = material(actor_id + "_skin", rgba(appearance.get("skin", "#F0C9A5")))
    hair = material(actor_id + "_hair", rgba(appearance.get("hair", "#24212A")))
    shirt = material(actor_id + "_shirt", rgba(appearance.get("shirt", appearance.get("accent", "#C62828"))))
    pants = material(actor_id + "_pants", rgba(appearance.get("trousers", "#283593")))
    shoe = material(actor_id + "_shoe", rgba(appearance.get("shoes", "#302820")))
    ink = material(actor_id + "_ink", rgba(appearance.get("outline", "#171923")))
    white = material(actor_id + "_white", (0.98, 0.97, 0.92, 1))
    pupil = material(actor_id + "_pupil", (0.04, 0.05, 0.07, 1))

    root = bpy.data.objects.new("Actor_" + actor_id, None)
    bpy.context.scene.collection.objects.link(root)
    root.empty_display_type = "CIRCLE"
    root.empty_display_size = 0.35
    x = float(actor.get("x", width * 0.5))
    y = float(actor.get("y", height * 0.82))
    root.location = ((x - width * 0.5) / 100.0, (height * 0.5 - y) / 100.0, 0)
    actor_scale = float(actor.get("scale", 1.0))
    root.scale = (actor_scale, actor_scale, actor_scale)

    head_r = float(appearance.get("head_radius", 72)) / 100.0 * float(proportions.get("head", 1))
    make_disc(actor_id + "_head", 0, 1.43, head_r, head_r * 1.08, skin, root, 0.24)
    # Keep the cap above the eyes and in front of the face mask so the hair
    # remains visible instead of being hidden by the skin-colored face layer.
    make_disc(actor_id + "_hair", 0, 1.68, head_r * 1.02, head_r * 0.38, hair, root, 0.32)
    # Forehead-colored mask keeps the hairline above the face.
    make_disc(actor_id + "_face", 0, 1.40, head_r * 0.91, head_r * 0.82, skin, root, 0.29)
    eye_gap = float(appearance.get("eye_spacing", 48)) / 100.0
    for side in (-1, 1):
        make_disc(actor_id + "_eye_white", side * eye_gap * 0.5, 1.47,
                  0.055, 0.075, white, root, 0.34)
        make_disc(actor_id + "_eye", side * eye_gap * 0.5 + 0.012, 1.46,
                  0.024, 0.04, pupil, root, 0.37)
    # Separate mouth drawings can be switched at dialogue viseme timestamps.
    mouth_rest = make_line(actor_id + "_mouth_rest", [(-0.09, 1.22), (0, 1.19), (0.09, 1.22)],
                           0.018, ink, root, 0.38)
    mouth_closed = make_line(actor_id + "_mouth_closed", [(-0.075, 1.20), (0.075, 1.20)],
                             0.014, ink, root, 0.38)
    mouth_smile = make_line(actor_id + "_mouth_smile",
                            [(-0.11, 1.22), (-0.05, 1.17), (0.05, 1.17), (0.11, 1.22)],
                            0.018, ink, root, 0.38)
    mouth_frown = make_line(actor_id + "_mouth_frown",
                            [(-0.11, 1.17), (-0.05, 1.22), (0.05, 1.22), (0.11, 1.17)],
                            0.018, ink, root, 0.38)
    mouth_e = make_line(actor_id + "_mouth_e",
                         [(-0.12, 1.21), (0, 1.20), (0.12, 1.21)],
                         0.032, ink, root, 0.38)
    mouth_i = make_line(actor_id + "_mouth_i",
                        [(-0.075, 1.20), (0.075, 1.20)],
                        0.028, ink, root, 0.38)
    mouth_a = make_disc(actor_id + "_mouth_a", 0, 1.20, 0.065, 0.095, ink, root, 0.39)
    mouth_o = make_disc(actor_id + "_mouth_o", 0, 1.20, 0.055, 0.075, ink, root, 0.39)
    mouth_u = make_disc(actor_id + "_mouth_u", 0, 1.20, 0.075, 0.045, ink, root, 0.39)
    mouths = {"REST": mouth_rest, "CLOSED": mouth_closed, "SMILE": mouth_smile,
              "FROWN": mouth_frown, "E": mouth_e, "I": mouth_i,
              "A": mouth_a, "O": mouth_o, "U": mouth_u}
    for mouth in {item.name: item for item in mouths.values()}.values():
        mouth.hide_render = True
        mouth.keyframe_insert(data_path="hide_render", frame=1)
    mouth_rest.hide_render = False
    mouth_rest.keyframe_insert(data_path="hide_render", frame=1)

    brows = {}
    for side, suffix in ((-1, "L"), (1, "R")):
        brow = make_pivot(actor_id + "_brow_" + suffix, root, (side * 0.16, 1.56, 0.39))
        make_line(actor_id + "_brow_line_" + suffix,
                  [(-0.075, 0), (0.0, 0.018), (0.075, 0)],
                  0.018, hair, brow, 0.02)
        brows[suffix] = brow

    torso_len = 0.92 * float(proportions.get("torso", 1))
    make_line(actor_id + "_torso_outline", [(0, 1.08), (0, 0.16)], 0.27, ink, root, 0.08)
    make_line(actor_id + "_torso", [(0, 1.08), (0, 0.16)], 0.225, shirt, root, 0.10)
    make_line(actor_id + "_collar", [(-0.18, 1.03), (0, 0.91), (0.18, 1.03)],
              0.025, ink, root, 0.16)
    make_line(actor_id + "_belt", [(-0.18, 0.18), (0.18, 0.18)], 0.035, ink, root, 0.18)

    arms = {}
    elbows = {}
    for side, suffix in ((-1, "L"), (1, "R")):
        shoulder = make_pivot(actor_id + "_arm_" + suffix, root, (side * 0.22, 0.96, 0.18))
        upper_len = 0.55 * float(proportions.get("upper_arm", 1))
        fore_len = 0.48 * float(proportions.get("forearm", 1))
        make_limb(actor_id + "_upper_" + suffix, shoulder, upper_len, shirt, 0.095, -1)
        elbow = make_pivot(actor_id + "_elbow_" + suffix, shoulder, (0, -upper_len, 0))
        make_limb(actor_id + "_fore_" + suffix, elbow, fore_len, skin, 0.075, -1)
        make_disc(actor_id + "_hand_" + suffix, 0, -fore_len, 0.10, 0.09, skin, elbow, 0.18)
        # Small separated finger strokes make the hand silhouette readable
        # instead of using a featureless circular endpoint.
        for finger in range(3):
            fx = (finger - 1) * 0.045
            make_line(actor_id + "_finger_" + suffix + "_" + str(finger),
                      [(fx, -fore_len - 0.035), (fx + 0.008, -fore_len - 0.105)],
                      0.018, skin, elbow, 0.20)
        make_line(actor_id + "_thumb_" + suffix,
                  [(0.075, -fore_len - 0.005), (0.13, -fore_len - 0.055)],
                  0.02, skin, elbow, 0.20)
        arms[suffix] = shoulder
        elbows[suffix] = elbow

    legs = {}
    knees = {}
    for side, suffix in ((-1, "L"), (1, "R")):
        hip = make_pivot(actor_id + "_leg_" + suffix, root, (side * 0.12, 0.12, 0.18))
        thigh = 0.58 * float(proportions.get("thigh", 1))
        shin = 0.55 * float(proportions.get("shin", 1))
        make_limb(actor_id + "_thigh_" + suffix, hip, thigh, pants, 0.12, -1)
        knee = make_pivot(actor_id + "_knee_" + suffix, hip, (0, -thigh, 0))
        make_limb(actor_id + "_shin_" + suffix, knee, shin, pants, 0.095, -1)
        make_line(actor_id + "_foot_" + suffix, [(-0.02, -shin), (0.22, -shin)],
                  0.09, shoe, knee, 0.16)
        legs[suffix] = hip
        knees[suffix] = knee

    scarf = appearance.get("scarf", actor.get("scarf", False))
    if scarf:
        scarf_mat = material(actor_id + "_scarf", rgba(appearance.get("accent", "#C62828")))
        make_line(actor_id + "_scarf", [(-0.2, 1.02), (0, 0.83), (0.2, 1.02)],
                  0.07, scarf_mat, root, 0.22)
    return {"root": root, "arms": arms, "elbows": elbows, "legs": legs,
            "knees": knees, "mouths": mouths, "brows": brows}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args(argv)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    fmt = manifest["format"]
    width, height = int(fmt["width"]), int(fmt["height"])
    fps = int(fmt["fps"])
    total_frames = int(round(float(fmt["duration_seconds"]) * fps))

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys() else "BLENDER_EEVEE"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = total_frames
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.color_depth = "8"
    scene.render.filepath = str(Path(manifest["output_root"]) / "frames" / "frame_######")
    scene.render.use_file_extension = True
    scene.render.resolution_percentage = 100
    scene.camera = None

    camera_data = bpy.data.cameras.new("Studio_2D_Camera")
    camera = bpy.data.objects.new("Studio_2D_Camera", camera_data)
    scene.collection.objects.link(camera)
    camera.data.type = "ORTHO"
    camera.data.sensor_fit = "VERTICAL"
    camera.data.ortho_scale = height / 100.0
    camera.location = (0, 0, 30)
    camera.rotation_euler = (0, 0, 0)
    scene.camera = camera

    world = bpy.data.worlds.new("Studio_Background") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.76, 0.84, 0.91, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8

    # Build a distinct stage for every location in the episode bible.
    location_sets = {
        str(item.get("id")): build_location(item, width, height)
        for item in manifest.get("locations", [])
    }
    if not location_sets:
        location_sets["default"] = build_location({}, width, height)

    catalog = {}
    catalog_path = Path(manifest.get("catalog_path", ""))
    if catalog_path.is_file():
        catalog_data = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog = {item["id"]: item for item in catalog_data.get("characters", [])}

    actors = {}
    for actor in manifest.get("characters", []):
        actor_id = str(actor["id"])
        profile_id = actor.get("cast_id", actor_id)
        profile = catalog.get(profile_id, {})
        actors[actor_id] = build_character(actor, profile, width, height)

    current_frame = 1
    for shot in manifest.get("shots", []):
        duration = float(shot.get("duration_seconds", 1))
        start = current_frame
        end = min(total_frames, start + max(1, round(duration * fps)) - 1)
        # Per-shot camera blocking: zoom and pan are keyframed in the same
        # episode-local frame space as character actions.
        camera_plan = shot.get("camera", {})
        move = camera_plan.get("move", {})
        camera_from = move.get("from", {}) if move else camera_plan
        camera_to = move.get("to", {}) if move else camera_plan
        for camera_frame, camera_state in ((start, camera_from), (end, camera_to)):
            zoom = max(0.25, min(3.0, float(camera_state.get("zoom", 1.0))))
            camera.data.ortho_scale = (height / 100.0) / zoom
            camera.location.x = -float(camera_state.get("x", 0.0)) / 100.0
            camera.location.y = float(camera_state.get("y", 0.0)) / 100.0
            camera.data.keyframe_insert(data_path="ortho_scale", frame=camera_frame)
            camera.keyframe_insert(data_path="location", frame=camera_frame)
        active_location = str(shot.get("location", "default"))
        if active_location not in location_sets:
            active_location = next(iter(location_sets))
        for location_id, location_objects in location_sets.items():
            visible = location_id == active_location
            for obj in location_objects:
                obj.hide_render = not visible
                obj.keyframe_insert(data_path="hide_render", frame=start)
                obj.keyframe_insert(data_path="hide_render", frame=end)
        active = set(shot.get("actors", []))
        positions = shot.get("positions", {})
        tracks = shot.get("motion_tracks", {})
        for actor_id, actor in actors.items():
            root = actor["root"]
            enabled = actor_id in active
            root.keyframe_insert(data_path="location", frame=start)
            if not enabled:
                root.scale = (0.00001, 0.00001, 0.00001)
                root.keyframe_insert(data_path="scale", frame=start)
                root.keyframe_insert(data_path="scale", frame=end)
                continue
            pos = positions.get(actor_id, {})
            source_actor = next(c for c in manifest["characters"] if c["id"] == actor_id)
            px = float(pos.get("x", source_actor.get("x", width * 0.5)))
            py = float(pos.get("y", source_actor.get("y", height * 0.82)))
            base_scale = float(pos.get("scale", source_actor.get("scale", 1.0)))
            # Portrait framing needs smaller puppets when several actors share
            # the same narrow 9:16 shot; otherwise their heads collide.
            actor_count = max(1, len(active))
            stage_scale = 1.0 if actor_count == 1 else max(
                0.55, 0.82 * math.sqrt(2.0 / actor_count)
            )
            actor_scale = base_scale * stage_scale
            root.scale = (actor_scale, actor_scale, actor_scale)
            root.keyframe_insert(data_path="scale", frame=start)
            root.location = ((px - width * 0.5) / 100.0, (height * 0.5 - py) / 100.0, 0)
            movement = shot.get("movement", {}).get(actor_id)
            if movement:
                from_x = float(movement.get("from_x", px))
                to_x = float(movement.get("to_x", px))
                root.location.x = (from_x - width * 0.5) / 100.0
                root.keyframe_insert(data_path="location", frame=start)
                root.location.x = (to_x - width * 0.5) / 100.0
                root.keyframe_insert(data_path="location", frame=end)
            else:
                root.keyframe_insert(data_path="location", frame=start)
                root.keyframe_insert(data_path="location", frame=end)
            track = tracks.get(actor_id, [])
            if track:
                for segment in track:
                    action_frame = start + max(0, round(float(segment.get("start", 0)) * fps))
                    action_frame = min(action_frame, end)
                    action = segment.get("action", "idle")
                    segment_end = min(end, start + max(0, round(float(segment.get("end", duration)) * fps)) - 1)
                    set_pose(actor, action, action_frame, segment_end, fps)
                    set_face(actor, action, action_frame)
            else:
                action = shot.get("action", "idle")
                set_pose(actor, action, start, end, fps)
                set_face(actor, action, start)
            # Apply Rhubarb-derived cues when dialogue lines carry viseme data.
            for line in shot.get("dialogue", []):
                if line.get("speaker") != actor_id:
                    continue
                line_start = float(line.get("start_seconds", 0.0))
                for cue in line.get("visemes", []):
                    cue_frame = start + round((line_start + float(cue.get("at", 0.0))) * fps)
                    if cue_frame <= end:
                        set_viseme(actor, cue.get("shape", "REST"), max(start, cue_frame))
            root.location.y += 0.035
            root.keyframe_insert(data_path="location", frame=start + max(1, int(fps * 0.25)))
            root.location.y -= 0.035
            root.keyframe_insert(data_path="location", frame=start + max(2, int(fps * 0.5)))
            root.location.y += 0.035
            root.keyframe_insert(data_path="location", frame=start + max(3, int(fps * 0.75)))
            root.location.y -= 0.035
            root.keyframe_insert(data_path="location", frame=end)
        current_frame = end + 1
    # Hold the final frame for actors that appear in the last shot.
    scene.frame_set(1)
    output = Path(manifest["output_root"])
    (output / "frames").mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(output / "frames" / "frame_######")
    bpy.ops.render.render(animation=True)
    blend_path = output / (manifest["episode_id"] + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print("BLENDER_RENDER_COMPLETE", total_frames, str(output))


if __name__ == "__main__":
    main()
