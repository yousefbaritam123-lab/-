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
        name=char.get("image") or char.get("cutout")
        if not name: continue
        path=Path(name)
        if not path.is_absolute(): path=root/path
        if not path.is_file():
            print("WARNING missing character image:",path); continue
        image=bpy.data.images.load(str(path),check_existing=True)
        bpy.ops.object.empty_add(type="IMAGE",location=(0,0,0))
        obj=bpy.context.object; obj.name="CharacterReference_"+str(char.get("id","unknown"))
        obj.data=image; obj.empty_display_size=4
    bpy.ops.wm.save_as_mainfile(filepath=str(output/(manifest["episode_id"]+".blend")))
    print("BLENDER_SCENE_READY",output)

if __name__=="__main__": main()
