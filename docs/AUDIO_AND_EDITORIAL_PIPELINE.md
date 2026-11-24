# Audio and editorial department

## Audio mix plan

Place source audio under the episode project, for example:
- `audio/dialogue/` for recorded character lines
- `audio/music/` for licensed/original score
- `audio/fx/` for effects and ambience

Create `production/audio_mix.json`:

```json
{
  "tracks": [
    {
      "name": "dialogue",
      "gain_db": 0,
      "clips": [
        {
          "file": "audio/dialogue/youssef-line-01.wav",
          "start_seconds": 2.4,
          "end_seconds": 4.9,
          "gain_db": -1
        }
      ]
    },
    {
      "name": "music",
      "gain_db": -12,
      "clips": [
        {
          "file": "audio/music/episode-score.wav",
          "start_seconds": 0,
          "end_seconds": 100
        }
      ]
    },
    {
      "name": "effects",
      "gain_db": -4,
      "clips": [
        {
          "file": "audio/fx/door-close.wav",
          "start_seconds": 16.2,
          "end_seconds": 17.4
        }
      ]
    }
  ]
}
```

Then run:

```powershell
python -m studio.cli audio-mix projects/episode-001
```

The mixer combines timed clips, groups dialogue/music/ambience/effects, automatically ducks music under dialogue, applies loudness and peak limiting, and writes a 48 kHz stereo 24-bit `audio/final_mix.wav` plus a report. Source paths are restricted to the episode folder. Do not use music or sound recordings unless you have rights to use them.

## Subtitles

Dialogue lines need `text`, `speaker`, `start_seconds`, and `end_seconds` values relative to their shot. Export subtitles:

```powershell
python -m studio.cli subtitles projects/episode-001
```

Optional speaker labels:

```powershell
python -m studio.cli subtitles projects/episode-001 --include-speaker
```

## Editorial timeline

```powershell
python -m studio.cli edit-plan projects/episode-001
```

This always creates `production/edit_plan.json` with shot boundaries and exact frame numbers. If OpenTimelineIO is installed from `requirements-editorial.txt`, it also creates an OTIO timeline referencing the final video and audio mix.

## Current limits

These tools do not write a finished screenplay, generate actors' voices, or decide whether a performance is emotionally convincing. The user can record dialogue or supply a compatible Piper Arabic voice model for local TTS. Rhubarb can derive mouth cues from recorded audio; Blender can now switch its basic mouth drawings at those cues. This is a working pipeline layer, not yet a complete professional sound or animation department.
