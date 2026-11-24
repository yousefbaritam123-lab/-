# Production start — Youssef animated series

## Production target
- 100 seconds per episode.
- Portrait 9:16, 1080x1920, 30 FPS (3,000 frames).
- Arabic-Algerian dialogue, persistent character identity, wardrobe and story continuity.
- Episode delivery is blocked until frame/audio checks and a real human visual review pass.

## Current engine boundary
- The Python/Skia path can render the current procedural character rigs and produce resumable frames.
- Tahoma2D v1.6.3 is downloaded and installed in CI, and its `tcomposer` batch renderer is available.
- The bridge prepares source artwork packages for Tahoma2D. It does not synthesize a native `.tnz` scene or a Plastic mesh/skeleton.
- Youssef and Adam source sheets are currently reference artwork; they are not complete cut-out animation rigs. Preserve them unchanged while the character department builds independently moving layers.
- Blender remains a legacy fallback. Do not switch the whole series to Tahoma2D until a real Tahoma2D scene renders and the character pilot passes visual review.

## Start a local episode project
```powershell
python -m pip install -r requirements.txt
python -m studio.cli doctor
python -m studio.cli init projects/episode-001
python -m studio.cli validate projects/episode-001
python -m studio.cli story-next projects/episode-001
python -m studio.cli storyboard projects/episode-001
python -m studio.cli tahoma2d-prepare projects/episode-001
```

Review and complete the outline/storyboard, then prepare voice assets and the audio mix. Do not render the full 100-second episode until the storyboard, character assets, and dialogue have been reviewed.

## Engine pilot and render
For the current procedural fallback:
```powershell
python -m studio.cli render projects/episode-001 --frames 0:300
python -m studio.cli encode projects/episode-001
python -m studio.cli qc projects/episode-001
```

For Tahoma2D, first open the prepared source package in Tahoma2D, create and save a genuine native scene, build/test the Plastic rig, then run:
```powershell
python -m studio.cli tahoma2d-render projects/episode-001/production/tahoma2d/episode-001.tnz projects/episode-001/renders/tahoma2d/episode-001.tif --start-frame 1 --end-frame 300 --threads 4
```

## Delivery gates
`production-run` checks every expected frame, retries defective frames, checks the final audio mix, and requires a human visual approval record. Never run `visual-approve` on behalf of a reviewer. A passing CI run proves only the checks actually executed; it does not prove artistic quality or a completed Plastic rig.
