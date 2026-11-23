"""Blender scene bootstrapper. Flat image planes are references, not auto-rigged puppets."""
import argparse, json, sys
from pathlib import Path
import bpy

def main():
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",required=True)
    args=parser.parse_args(argv)
    manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    fmt=manifest["format"]
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE_NEXT"
    scene.render.resolution_x=int(fmt["width"])
    scene.render.resolution_y=int(fmt["height"])
    scene.render.resolution_percentage=100
    scene.render.fps=int(fmt["fps"])
    scene.frame_start=1
    scene.frame_end=max(1,round(float(fmt["duration_seconds"])*scene.render.fps))
    camera_data=bpy.data.cameras.new("Studio_2D_Camera")
    camera=bpy.data.objects.new("Studio_2D_Camera",camera_data)
    scene.collection.objects.link(camera)
    camera.data.type="ORTHO"; camera.data.ortho_scale=16
    camera.location=(0,0,20); camera.rotation_euler=(0,0,0); scene.camera=camera
    scene.render.image_settings.file_format="PNG"
    scene.render.film_transparent=True
    output=Path(manifest["output_root"]); output.mkdir(parents=True,exist_ok=True)
    scene.render.filepath=str(output/"frame_")
    scene["studio_episode_id"]=manifest["episode_id"]
    scene["studio_manifest"]=str(Path(args.manifest).resolve())
    root=Path(manifest["assets_root"])
    for char in manifest.get("characters",[]):
        char_id=str(char.get("id","unknown"))
        layered=char.get("layered_parts",{})
        if isinstance(layered,dict) and layered:
            # Rigid 2D cutout rig: each supplied transparent PNG is attached
            # to a named bone. Hidden pixels and pivots must be authored in
            # the manifest; this does not infer missing artwork from one PNG.
            arm_data=bpy.data.armatures.new("RigData_"+char_id)
            arm_obj=bpy.data.objects.new("Rig_"+char_id,arm_data)
            scene.collection.objects.link(arm_obj)
            bpy.context.view_layer.objects.active=arm_obj
            arm_obj.select_set(True)
            bpy.ops.object.mode_set(mode="EDIT")
            bones={}
            definitions={
              "root":((0,0,0),(0,1,0),None),
              "torso":((0,1,0),(0,3,0),"root"),
              "head":((0,3,0),(0,4,0),"torso"),
              "upper_arm.L":((-.45,2.8,0),(-1.2,2.0,0),"torso"),
              "forearm.L":((-1.2,2.0,0),(-1.6,1.3,0),"upper_arm.L"),
              "hand.L":((-1.6,1.3,0),(-1.9,1.1,0),"forearm.L"),
              "upper_arm.R":((.45,2.8,0),(1.2,2.0,0),"torso"),
              "forearm.R":((1.2,2.0,0),(1.6,1.3,0),"upper_arm.R"),
              "hand.R":((1.6,1.3,0),(1.9,1.1,0),"forearm.R"),
              "thigh.L":((-.2,1,0),(-.35,0,0),"root"),
              "shin.L":((-.35,0,0),(-.4,-1,0),"thigh.L"),
              "foot.L":((-.4,-1,0),(-.8,-1,0),"shin.L"),
              "thigh.R":((.2,1,0),(.35,0,0),"root"),
              "shin.R":((.35,0,0),(.4,-1,0),"thigh.R"),
              "foot.R":((.4,-1,0),(.8,-1,0),"shin.R")
            }
            for bone_name,(head,tail,parent_name) in definitions.items():
                bone=arm_data.edit_bones.new(bone_name)
                bone.head=head; bone.tail=tail
                if parent_name: bone.parent=bones[parent_name]
                bones[bone_name]=bone
            bpy.ops.object.mode_set(mode="OBJECT")
            for part_name,part in layered.items():
                image_name=part.get("image")
                bone_name=part.get("bone")
                if not image_name or bone_name not in definitions:
                    print("WARNING invalid layered part:",char_id,part_name); continue
                image_path=Path(image_name)
                if not image_path.is_absolute(): image_path=root/image_path
                if not image_path.is_file():
                    print("WARNING missing layered part image:",image_path); continue
                image=bpy.data.images.load(str(image_path),check_existing=True)
                bpy.ops.object.empty_add(type="IMAGE",location=(0,0,0))
                obj=bpy.context.object
                obj.name=char_id+"_"+part_name
                obj.data=image
                obj.empty_display_size=float(part.get("size",1.0))
                obj.parent=arm_obj
                obj.parent_type="BONE"
                obj.parent_bone=bone_name
                offset=part.get("offset",[0,0,0])
                obj.location=(float(offset[0]),float(offset[1]),float(offset[2]))
                obj.rotation_euler[2]=float(part.get("rotation_degrees",0))*3.14159265/180
            arm_obj.select_set(False)
        else:
            name=char.get("image") or char.get("cutout")
            if not name: continue
            path=Path(name)
            if not path.is_absolute(): path=root/path
            if not path.is_file():
                print("WARNING missing character image:",path); continue
            image=bpy.data.images.load(str(path),check_existing=True)
            bpy.ops.object.empty_add(type="IMAGE",location=(0,0,0))
            obj=bpy.context.object; obj.name="CharacterReference_"+char_id
            obj.data=image; obj.empty_display_size=4
    bpy.ops.wm.save_as_mainfile(filepath=str(output/(manifest["episode_id"]+".blend")))
    print("BLENDER_SCENE_READY",output)

if __name__=="__main__": main()
