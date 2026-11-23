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
