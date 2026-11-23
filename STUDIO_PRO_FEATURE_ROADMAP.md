# Studio Pro — Advanced Production Roadmap

## New optional modules

- studio.image_character: prepares a transparent cutout and pose-landmark guide from a reference image. Optional extras: rembg + onnxruntime for background removal; mediapipe + opencv-python for pose landmarks. A flat picture is not a complete articulated puppet: limb layers, hidden pixels, pivots, hands and face controls still need manual review and painting.
- studio.lipsync: runs the external Rhubarb Lip Sync executable and converts mouth cues to the renderer's viseme names. It requires real dialogue audio. Missing Rhubarb causes a clear error instead of invented mouth motion.
- studio.story: creates an episode beat outline from persistent continuity. It does not advance continuity or claim to write polished Algerian dialogue autonomously.
- studio.blender_bridge + tools/blender_scene.py: optional Blender background-mode bridge. Blender is installed separately, not with pip. The bridge currently creates a 2D scene, camera, timeline, project file and optional image-reference planes. Full layered puppet rig import, Grease Pencil authoring and shot-level Blender animation remain a next milestone.

## Suggested local setup

Core: python -m pip install -r requirements.txt
Optional image preparation: python -m pip install rembg onnxruntime mediapipe opencv-python
External tools: install Blender 4.x and add blender.exe to PATH; install Rhubarb Lip Sync and add rhubarb.exe to PATH; install FFmpeg for final audio/video packaging.

## Quality gates

1. Inspect transparent cutout edges and pose landmarks; manually separate body parts before skeletal rigging.
2. Validate front/side poses, hands and facial references; preserve a versioned canonical asset.
3. Compare Rhubarb cues against supplied dialogue audio; correct dialect-specific pronunciation manually where needed.
4. Author reusable layered locations (background, midground, foreground, props, atmosphere) and test parallax/camera moves.
5. Approve each episode outline and script; apply explicit continuity updates only after editorial approval.
6. Render 3,000 frames at 1080x1920/30fps in resumable batches. Do not assume free CI is an unlimited render farm.

## Honest current status

These adapters and planners are foundations, not proof of a finished professional pipeline. The 100-second 1080x1920 output remains an end-to-end acceptance test. The Blender bridge has a rigid layered-puppet import path, but does not yet generate final animated shots from the episode timeline.
