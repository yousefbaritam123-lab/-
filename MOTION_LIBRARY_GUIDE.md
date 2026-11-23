# Reusable Motion Library

The Studio renderer now supports per-character motion timelines inside each shot. The same motion preset is retargeted to each character's existing rig proportions and appearance; it does not replace the character model.

## Available motion presets

| Preset | Purpose |
|---|---|
| `stand`, `wait` | Neutral standing / waiting |
| `walk`, `run`, `sneak` | Locomotion |
| `greet`, `wave`, `agree`, `disagree` | Social reactions |
| `talk`, `explain`, `listen`, `point` | Conversation acting |
| `think`, `shrug`, `apologize` | Gesture and intent |
| `laugh`, `celebrate`, `celebrate_small`, `sad`, `surprised` | Emotions |
| `jump`, `dodge`, `hit_react`, `kick` | Physical actions |

Presets are semantic aliases over the shared keyframed rig clips. Some add pose offsets (for example, `explain` opens the hands and raises the arms). They are reusable starting performances, not motion-capture-quality acting.

## Add a timeline to a shot

Add `motion_tracks` keyed by character ID. Segment times are local to the shot, in seconds. Segments must not overlap and must stay inside the shot duration.

```json
{
  "id": "shot-004",
  "duration_seconds": 8,
  "actors": ["youssef", "adam"],
  "motion_tracks": {
    "youssef": [
      {"start": 0, "end": 2.5, "action": "walk"},
      {"start": 2.5, "end": 4, "action": "greet", "transition_seconds": 0.2},
      {"start": 4, "end": 8, "action": "explain", "transition_seconds": 0.2}
    ],
    "adam": [
      {"start": 0, "end": 4, "action": "wait"},
      {"start": 4, "end": 8, "action": "listen", "transition_seconds": 0.2}
    ]
  }
}
```

The timeline is random-access safe: rendering frame 700 before frame 100 does not depend on previously rendered frames. `transition_seconds` crossfades from the preceding segment. Segment-level `pose` values can override individual rig controls.

## Where the files live

- `assets/motions/motion_library.json`: editable motion data and semantic preset catalogue.
- `studio/motion_library.py`: preset resolution, timeline selection and validation.
- `studio/renderer.py`: applies the chosen performance to each actor while preserving their individual rig proportions.
- `examples/pilot-15s/episode.json`: working example with timed motion sequences.

Run `python -m studio.cli validate <project>` before rendering. The motion library currently reuses and combines the project's existing procedural keyframed clips; expanding it with polished, independently authored animation takes and contact-aware two-character choreography is the next quality step.
