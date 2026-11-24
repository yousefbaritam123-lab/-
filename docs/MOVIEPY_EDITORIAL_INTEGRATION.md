# Optional MoviePy editorial compositor

The studio keeps its native Skia/Blender frame renderers and FFmpeg encoder as
the default production path. MoviePy is an optional finishing engine for
assembling already-rendered shots, applying crossfades, and replacing/mixing
the final audio track.

## Install

```bash
python -m pip install -r requirements-editorial.txt
```

MoviePy is MIT-licensed. Its dependency is optional and is not installed by
the core `requirements.txt`.

## Timeline

Create `production/moviepy_timeline.json`:

```json
{
  "fps": 30,
  "output": "renders/moviepy-final.mp4",
  "audio": "audio/final_mix.wav",
  "clips": [
    {
      "source": "renders/shot-001.mp4",
      "start_seconds": 0,
      "end_seconds": 8.5,
      "transition_in_seconds": 0
    },
    {
      "source": "renders/shot-002.mp4",
      "start_seconds": 1,
      "end_seconds": 7,
      "transition_in_seconds": 0.35
    }
  ]
}
```

All media paths must stay inside the episode project. Every shot must have the
same resolution. Transition durations must fit inside both adjacent trimmed
clips. The optional audio path replaces the composed source audio.

Run:

```bash
python -m studio.cli moviepy-compose projects/episode-001
```

Or provide a different timeline:

```bash
python -m studio.cli moviepy-compose projects/episode-001 --timeline production/custom_timeline.json
```

## Scope and limitations

This is an editorial compositor, not a character animation engine. It does not
create poses, split character art, or replace Blender. The input MP4 shots must
already exist. The core pipeline remains usable without MoviePy. Full video
decode, shot-level visual quality review, and human approval remain separate
delivery gates.
