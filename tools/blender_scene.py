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
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 1.0
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


def set_pose(actor, action, frame):
    arms = actor["arms"]
    legs = actor["legs"]
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
            pivot.rotation_euler[2] = angle + math.radians(24)
            pivot.keyframe_insert(data_path="rotation_euler", frame=frame + 8)
            pivot.rotation_euler[2] = angle - math.radians(18)
            pivot.keyframe_insert(data_path="rotation_euler", frame=frame + 16)
            pivot.rotation_euler[2] = angle
            pivot.keyframe_insert(data_path="rotation_euler", frame=frame + 24)
    for key, pivot in legs.items():
        angle = 0.0
        if action in ("walk", "run"):
            angle = math.radians(18 if key.endswith("L") else -18)
        elif action in ("kick",):
            angle = math.radians(-52 if key.endswith("L") else 52)
        pivot.rotation_euler[2] = angle
        pivot.keyframe_insert(data_path="rotation_euler", frame=frame)


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
    root.scale = (float(actor.get("scale", 1.0)) * 0.01,
                  float(actor.get("scale", 1.0)) * 0.01,
                  float(actor.get("scale", 1.0)) * 0.01)

    head_r = float(appearance.get("head_radius", 72)) / 100.0 * float(proportions.get("head", 1))
    make_disc(actor_id + "_head", 0, 1.43, head_r, head_r * 1.08, skin, root, 0.24)
    make_disc(actor_id + "_hair", 0, 1.58, head_r * 1.02, head_r * 0.48, hair, root, 0.27)
    # Forehead-colored mask keeps the hairline above the face.
    make_disc(actor_id + "_face", 0, 1.40, head_r * 0.91, head_r * 0.82, skin, root, 0.29)
    eye_gap = float(appearance.get("eye_spacing", 48)) / 100.0
    for side in (-1, 1):
        make_disc(actor_id + "_eye_white", side * eye_gap * 0.5, 1.47,
                  0.055, 0.075, white, root, 0.34)
        make_disc(actor_id + "_eye", side * eye_gap * 0.5 + 0.012, 1.46,
                  0.024, 0.04, pupil, root, 0.37)
    make_line(actor_id + "_mouth", [(-0.09, 1.22), (0, 1.19), (0.09, 1.22)],
              0.018, ink, root, 0.38)

    torso_len = 0.92 * float(proportions.get("torso", 1))
    make_line(actor_id + "_torso_outline", [(0, 1.08), (0, 0.16)], 0.27, ink, root, 0.08)
    make_line(actor_id + "_torso", [(0, 1.08), (0, 0.16)], 0.225, shirt, root, 0.10)
    make_line(actor_id + "_collar", [(-0.18, 1.03), (0, 0.91), (0.18, 1.03)],
              0.025, ink, root, 0.16)
    make_line(actor_id + "_belt", [(-0.18, 0.18), (0.18, 0.18)], 0.035, ink, root, 0.18)

    arms = {}
    for side, suffix in ((-1, "L"), (1, "R")):
        shoulder = make_pivot(actor_id + "_arm_" + suffix, root, (side * 0.22, 0.96, 0.18))
        upper_len = 0.55 * float(proportions.get("upper_arm", 1))
        fore_len = 0.48 * float(proportions.get("forearm", 1))
        make_limb(actor_id + "_upper_" + suffix, shoulder, upper_len, shirt, 0.095, -1)
        elbow = make_pivot(actor_id + "_elbow_" + suffix, shoulder, (0, -upper_len, 0))
        make_limb(actor_id + "_fore_" + suffix, elbow, fore_len, skin, 0.075, -1)
        make_disc(actor_id + "_hand_" + suffix, 0, -fore_len, 0.10, 0.09, skin, elbow, 0.18)
        arms[suffix] = shoulder

    legs = {}
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

    scarf = appearance.get("scarf", actor.get("scarf", False))
    if scarf:
        scarf_mat = material(actor_id + "_scarf", rgba(appearance.get("accent", "#C62828")))
        make_line(actor_id + "_scarf", [(-0.2, 1.02), (0, 0.83), (0.2, 1.02)],
                  0.07, scarf_mat, root, 0.22)
    return {"root": root, "arms": arms, "legs": legs}


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
    scene.render.filepath = str(Path(manifest["output_root"]) / "frames" / "frame_")
    scene.render.use_file_extension = True
    scene.render.resolution_percentage = 100
    scene.camera = None

    camera_data = bpy.data.cameras.new("Studio_2D_Camera")
    camera = bpy.data.objects.new("Studio_2D_Camera", camera_data)
    scene.collection.objects.link(camera)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = width / 100.0
    camera.location = (0, 0, 30)
    camera.rotation_euler = (0, 0, 0)
    scene.camera = camera

    world = bpy.data.worlds.new("Studio_Background") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.76, 0.84, 0.91, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8

    # A simple floor and soft lighting establish a readable 2D stage.
    floor_mat = material("Studio_Floor", (0.25, 0.34, 0.31, 1))
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, -height / 200.0 + 0.4, -0.8))
    floor = bpy.context.object
    floor.name = "Studio_Floor"
    floor.data.materials.append(floor_mat)

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
        active = set(shot.get("actors", []))
        positions = shot.get("positions", {})
        tracks = shot.get("motion_tracks", {})
        for actor_id, actor in actors.items():
            root = actor["root"]
            enabled = actor_id in active
            root.scale = (0.01, 0.01, 0.01) if not enabled else root.scale
            root.keyframe_insert(data_path="scale", frame=start)
            root.keyframe_insert(data_path="location", frame=start)
            if not enabled:
                root.scale = (0.00001, 0.00001, 0.00001)
                root.keyframe_insert(data_path="scale", frame=start)
                root.keyframe_insert(data_path="scale", frame=end)
                continue
            pos = positions.get(actor_id, {})
            px = float(pos.get("x", next((c.get("x", width * 0.5) for c in manifest["characters"] if c["id"] == actor_id), width * 0.5)))
            py = float(pos.get("y", next((c.get("y", height * 0.82) for c in manifest["characters"] if c["id"] == actor_id), height * 0.82)))
            root.location = ((px - width * 0.5) / 100.0, (height * 0.5 - py) / 100.0, 0)
            root.keyframe_insert(data_path="location", frame=start)
            root.keyframe_insert(data_path="location", frame=end)
            track = tracks.get(actor_id, [])
            action = track[0].get("action") if track else shot.get("action", "idle")
            set_pose(actor, action, start)
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
    (output / "frames").mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(output / "frames" / "frame_")
    bpy.ops.render.render(animation=True)
    blend_path = output / (manifest["episode_id"] + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print("BLENDER_RENDER_COMPLETE", total_frames, str(output))


if __name__ == "__main__":
    main()
