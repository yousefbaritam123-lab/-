# Studio Pro — executable animation engine architecture

## Production direction

The repository now has a Python orchestration layer and a first deterministic Skia renderer. The target remains a serialized animation studio, not a one-shot demo.

### Runtime responsibilities

- **Python production manager**: episode manifests, continuity state, department work orders, validation, frame scheduling and QC reports.
- **Skia renderer**: rasterizes vector scenes frame-by-frame with anti-aliasing, layered environments, reusable character records, simple procedural acting and camera transforms.
- **FFmpeg**: encodes frame sequences into H.264 MP4.
- **TypeScript animation runtime**: reserved for a later integration only after an upstream license and package compatibility have been verified.

## Current renderer scope

- 9:16 1080×1920 output contract at 30 FPS.
- Deterministic shot timeline and per-shot camera transforms.
- Reusable character IDs and per-shot overrides.
- Procedural idle, walk, run, wave, talk and jump poses.
- Layered sky, clouds, hills and ground with simple parallax motion.
- PNG frame output so rendering can be resumed by frame range.
- H.264 encoding through imageio-ffmpeg.

## Tahoma2D integration status

The `studio.tahoma2d_bridge` adapter exports the original Youssef and Adam sheets into canvas-aligned SVG levels. Existing arm and leg polylines are split only at vertices already authored in the source; original sheets are preserved and joint landmarks are recorded. Run `python -m studio.cli tahoma2d-prepare projects/episode-001` after `init`.

This is a vector asset handoff, not an automatic native `.tnz` scene generator. No Plastic mesh or skeleton has yet been authored. Tahoma2D v1.6.3 is installed and launched in CI, and its `tcomposer` interface is detected, but a real character scene has not yet been rendered through it.

The current source sheets are simplified line-art, not finished production character art. Youssef's SVG does not draw the cream shirt or dark trousers described in its model-sheet notes; Adam has a blue torso but no separately drawn sleeves or hands. The bridge deliberately does not invent or repaint these missing parts. The character-art department must complete approved source artwork, then the rigging department can build and test Plastic rigs.

Blender remains a legacy optional backend until the Tahoma2D character pilot passes a real render and visual review.

## Important limitations

This is a working foundation, not a finished studio. The renderer currently uses a procedural stickman rig and does not yet provide full skeletal IK, authored vector character rigs, robust Arabic text shaping, advanced lip-sync, multi-track audio mixing, or professional background painting. Those are planned engine modules and must be implemented and tested separately.

## Render commands

```powershell
pip install -r requirements.txt
python -m studio.cli doctor
python -m studio.cli init projects/episode-001
python -m studio.cli validate projects/episode-001
python -m studio.cli render projects/episode-001 --frames 0:300
python -m studio.cli render projects/episode-001
python -m studio.cli encode projects/episode-001
```

A frame range is start-inclusive and end-exclusive. Rendering a range does not delete earlier frames; this allows a long episode to be rendered in batches.
