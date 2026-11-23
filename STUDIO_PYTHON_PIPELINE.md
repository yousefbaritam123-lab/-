# Python production manager — first implementation

This is the first executable foundation for the production workflow. It is deliberately separate from the legacy Maven Toon launcher and does not overwrite it.

## What it does now

- Creates a standardized episode project with assets/audio/render/continuity folders.
- Creates an episode manifest for a 100-second, 9:16, 30 FPS Algerian Arabic episode.
- Validates unique character and shot IDs, known actor/speaker references, and total shot duration.
- Generates a ten-department production work order as JSON.
- Checks whether Python, Node.js, pnpm, FFmpeg and optional Rhubarb are installed.
- Uses only the Python standard library; no Python package installation is needed for these commands.

## Run on Windows

From the repository root:

```powershell
python -m studio.cli doctor
python -m studio.cli init projects/episode-001
python -m studio.cli validate projects/episode-001
python -m studio.cli plan projects/episode-001
python -m unittest discover -s tests -v
```

## Honest boundary

This manager coordinates and validates production data. It does **not** yet draw characters, animate scenes, synthesize voices, or render an MP4. The animation runtime must be integrated and tested separately. The animeStudio repository is currently a candidate only; its license and asset terms must be verified before copying or bundling its source. Its public README documents the skeletal rigs, IK, camera, lighting, lip-sync and Remotion capabilities: https://github.com/denerFernandes/animeStudio

## Next engineering gate

1. Run the Python tests.
2. Establish Node/pnpm and FFmpeg availability on the target laptop.
3. Verify the animation runtime's license and install/build commands.
4. Build a single 10–15 second scene and inspect actual rendered frames before scaling to 100 seconds.
