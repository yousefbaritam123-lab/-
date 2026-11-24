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

For the named Youssef and Adam sheets, the package preserves the original design sheet, exports a full reference, and splits the existing arm/leg strokes at their authored vertices into canvas-aligned SVG levels. It also exports the existing head, costume and face shapes as separate levels and records joint landmarks. This is source-preserving vector segmentation, not new drawing. Important art limitation: the current model sheets are simplified line-art; Youssef's sheet has a red scarf but no authored shirt/trouser silhouette, while Adam has a blue torso shape but no separate sleeves or hands. The colors in character.toon.json do not create missing SVG artwork. The Plastic mesh/skeleton and native .tnz scene still need to be authored and tested in Tahoma2D.

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

The repository can now prepare canvas-aligned vector levels for Youssef and Adam, preserve their original sheets, record joint landmarks, install and launch Tahoma2D in CI, and detect the official batch renderer. It still does not automatically construct Plastic meshes/skeletons or create a native .tnz scene. A real character scene must be authored in Tahoma2D, batch-rendered, and visually reviewed before the full episode pipeline can switch over.
