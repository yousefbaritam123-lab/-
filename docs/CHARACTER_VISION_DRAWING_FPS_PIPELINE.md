# Character vision, drawing and FPS pipeline

This document records the currently implemented and intentionally optional stages.

## 1. Character image preparation

Run:

```powershell
python -m studio.cli prepare-character input.png projects/episode-001/assets/characters/imported hero_01
```

The image preparation stage removes the background with optional `rembg`. If MediaPipe is installed, it estimates human pose landmarks and attempts to save a person-segmentation mask beside the transparent cutout. The generated manifest records whether a mask was actually produced.

Important limitations:
- MediaPipe Pose is trained for human body poses and can fail on stylized/cartoon characters.
- A segmentation mask is not a rig and does not split a flat image into independently movable body parts.
- Hidden pixels behind joints, pivots, facial controls and layer separation still require artwork preparation and review.
- Do not treat an empty landmark list as a successful character rig.

Optional install:

```powershell
pip install -r requirements-optional.txt
```

## 2. Drawing and animation backend

The current Blender backend creates 2D-style characters from procedural curves and meshes. It is not yet a Grease Pencil drawing pipeline and does not yet import automatically separated layered character artwork. Keep this distinction explicit: a Blender render succeeding proves the scene rendered, not that a hand-drawn production rig is complete.

The next drawing-backend milestone is a version-pinned Blender Grease Pencil adapter with a real sample scene, round-trip asset tests and visual artifact review before it becomes the default. Until then, the current Blender procedural renderer and Skia renderer remain the stable paths.

## 3. FPS interpolation

After creating the source MP4, optionally run:

```powershell
python -m studio.cli interpolate projects/episode-001 --fps 60
```

The command uses FFmpeg's motion-compensated `minterpolate` filter and writes a separate file such as `renders/episode-60fps.mp4`. It never overwrites the source video. Target FPS must be an integer multiple of the episode FPS (2x to 4x).

This is an optional post-process. It can create smoother temporal sampling, but it cannot fix incorrect poses, anatomy, foot sliding, collisions, bad timing or inconsistent character art. Inspect the interpolated result for warped edges and ghosting before publishing.

RIFE is not installed or wired into this repository yet. It remains a possible optional accelerator after a reproducible model/runtime and hardware test are available. The built-in FFmpeg path avoids downloading a large neural model on the user's Ryzen laptop.
