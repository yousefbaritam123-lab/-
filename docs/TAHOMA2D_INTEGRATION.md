# Tahoma2D engine integration

## Engine installation in CI

The studio-tahoma2d-engine.yml workflow downloads the official Tahoma2D v1.6.3 Linux package from the upstream release, verifies its SHA-256 digest, installs it on an Ubuntu runner, launches the desktop application under Xvfb, and checks that the native tcomposer batch renderer is available.

The application binary is deliberately not committed to this repository: the official Linux package is hundreds of megabytes. CI downloads the pinned upstream release when the engine workflow runs.

Run the workflow manually from GitHub Actions:
https://github.com/yousefbaritam123-lab/-/actions/workflows/studio-tahoma2d-engine.yml

## Character asset preparation

    python -m studio.cli tahoma2d-prepare projects/episode-001

This exports original SVG artwork and available articulated source segments into:

    projects/episode-001/production/tahoma2d/characters/

The package includes a full-character reference, canvas-aligned vector layers, joint/bone metadata where available, and an import guide. It does not fabricate a native Tahoma2D project or claim the Plastic rig is already complete.

## Native Tahoma2D batch rendering

After the character is imported and rigged in Tahoma2D and the scene is saved as a native .tnz file, render it through the official tcomposer executable:

    python -m studio.cli tahoma2d-render projects/episode-001/production/tahoma2d/episode-001.tnz projects/episode-001/renders/tahoma2d/episode-001.tif --start-frame 1 --end-frame 300 --threads 4

The renderer uses the upstream tcomposer batch interface (source, -o, -range, -step, -multimedia, -nthreads) and writes a command/stdout/stderr log beside the output.

## Production handoff status

- Tahoma2D is the selected primary character-animation authoring engine.
- Python continues to own story, continuity, script QA, audio, subtitles, editorial assembly and delivery gates.
- Tahoma2D owns native Plastic mesh/skeleton authoring and animation rendering.
- FFmpeg/MoviePy remain available for final encode and editorial assembly.
- Blender is retained only as a legacy optional path until a Tahoma2D pilot is visually accepted.

## Honest current boundary

The repository can now prepare character vector assets, install and launch Tahoma2D in CI, detect the official batch renderer, and invoke tcomposer on an authored .tnz scene. It does not yet automatically construct Plastic meshes/skeletons or create a valid native .tnz scene from the character manifest. That must be completed in Tahoma2D and validated with a real rendered character test before the entire episode pipeline can switch over.
