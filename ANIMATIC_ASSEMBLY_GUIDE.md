# Storyboard-to-animatic assembly

The `assemble` command now connects the serial outline, director storyboard, motion tracks, canonical character assets, and the existing frame renderer without modifying the source episode.

## End-to-end command sequence

Run from the repository root after installing `requirements.txt`:

```powershell
python -m studio.cli init projects/episode-001
python -m studio.cli story-next projects/episode-001
python -m studio.cli storyboard projects/episode-001
python -m studio.cli assemble projects/episode-001
```

Assembly creates a separate project under:

```
projects/episode-001/production/assembled/episode-001-animatic/
```

The assembled directory contains its own `episode.json`, a copy of the continuity ledger, and copies of `assets/` and `audio/`. It is validated before the command succeeds. The original `episode.json` is never changed, and an existing assembly is never overwritten.

Then render and encode using the new directory:

```powershell
python -m studio.cli validate projects/episode-001/production/assembled/episode-001-animatic
python -m studio.cli render projects/episode-001/production/assembled/episode-001-animatic --frames 0:300
python -m studio.cli render projects/episode-001/production/assembled/episode-001-animatic --resume
python -m studio.cli encode projects/episode-001/production/assembled/episode-001-animatic
```

The first render command is a short 10-second preview. The resume command renders the remaining frames. At 100 seconds and 30 FPS, the complete episode contains 3,000 frames.

## What this closes

- Storyboard shots are no longer stranded in a separate JSON file.
- Character IDs, locations, camera settings, semantic motion tracks, beat metadata, and dialogue arrays are transferred into the renderer's episode schema.
- Character rigs and the motion library are copied alongside the draft so relative asset paths still resolve.
- Continuity validation runs against the assembled episode.
- Source project preservation and no-overwrite behavior are covered by automated tests.

## What it does not claim

The assembly is a renderable blocking animatic, not a finished screenplay. The current story stage still supplies structural beats rather than authored Algerian Arabic dialogue. Empty dialogue remains empty; no fake voice, lip sync, or final sound mix is inserted. The final render still requires review and the full 100-second 1080×1920 acceptance test.
