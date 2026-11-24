# Blender 2D production backend

## Connected in this branch

- `studio.cli blender-render` launches Blender in background mode.
- The bridge passes the episode cast, locations, shot timings, actor positions and motion tracks through a versioned manifest.
- Blender creates procedural 2D cartoon puppets from curves and meshes: head, eyes, brows, multiple mouth shapes, torso, articulated arms, hands, legs and feet.
- The director's shot camera zoom/pan and actor blocking are applied in Blender. Walk/run cycles and repeated waving are keyframed across each motion segment.
- Location-specific procedural stages are built for neighborhood streets, classrooms, rooftops, parks and beaches; the active set changes with the shot location.
- Rhubarb viseme cues can switch Blender mouth drawings when attached to dialogue lines.
- If `audio/final_mix.wav` exists, the Blender MP4 encoder muxes it as AAC audio.
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

This is a functional first Blender backend, not yet a finished studio-grade animation engine. It builds procedural puppets rather than importing the full Python rig graph. It supports a limited action set, simple cyclic walk/run/wave animation, shot camera moves and basic facial/viseme switching. It does not yet solve production-grade IK, reliable foot planting, complex contact, nuanced facial acting, or layered painted environments. Rhubarb remains an external lip-sync executable and recorded dialogue is still required. The existing Skia renderer remains intact as a fallback.

The 60 catalog profiles share one topology and are not 60 separately hand-drawn models. The Blender integration workflow must pass before this backend is treated as verified.
