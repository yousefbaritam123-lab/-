# Blender 2D production backend

## Connected in this branch

- `studio.cli blender-render` launches Blender in background mode.
- The bridge passes the episode cast, locations, shot timings, actor positions and motion tracks through a versioned manifest.
- Blender creates procedural 2D cartoon puppets from curves and meshes: head, eyes, torso, articulated arms, hands, legs and feet.
- The 60-profile cast catalog supplies appearance and proportion variants when an actor ID or `cast_id` matches a catalog profile.
- Blender renders a numbered PNG sequence. The bridge decodes every expected frame, checks its dimensions, writes `render_integrity.json`, and encodes H.264 MP4 using FFmpeg.
- The Python test suite checks the manifest and script syntax. A separate GitHub Actions workflow installs Blender and renders a real two-second sample.

## Local use

Install Blender and make sure its executable is on PATH. Then run:

```powershell
python -m pip install -r requirements.txt
blender --version
python -m studio.cli validate projects/episode-001
python -m studio.cli blender-render projects/episode-001 --blender blender
```

Expected output:
- `renders/blender/episode-blender.mp4`
- `renders/blender/frames/frame_000001.png` onward
- `renders/blender/render_integrity.json`
- `renders/blender/<episode-id>.blend`

## Honest limitations

This is the first functioning Blender production backend, not yet a finished studio-grade animation engine. It builds procedural puppets rather than importing the full Python rig graph. It currently supports a limited set of action poses and basic keyframes; it does not yet solve production-grade IK, foot planting, complex contact, facial acting, automatic Arabic lip sync, or layered painted environments. Dialogue audio is not yet mixed into this Blender MP4. The existing Skia renderer remains intact as a fallback.

The 60 catalog profiles share one topology and are not 60 separately hand-drawn models. The Blender integration workflow must pass before this backend is treated as verified.
