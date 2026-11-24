# Autonomous studio team — implementation status

This status distinguishes working software from planned departments. A library being installed does not count as a working department until the pipeline calls it and tests the result.

| Department | Implemented capability | Remaining work |
|---|---|---|
| Executive production | Project setup, task plan, continuity and delivery gates | Scheduling, resource estimates and per-department approval queue |
| Story room | Serialized 8-beat outline seeded by unresolved continuity threads | A connected story model for original full Algerian-dialect dialogue and creative revision |
| Screenwriting QA | Speaker validation, line timing, overlap and speaking-rate checks; report blocks bad scripts | Human review for humor, natural dialect, character voice and emotional quality |
| Direction | Eight-shot blocking, actor staging, shot sizes, focus actor, camera presets and cut notes | More varied coverage, action continuity and human/director approval |
| Character art | 60 catalog appearance/proportion profiles, canonical character sheets and Blender procedural puppets | Hand-authored unique designs, layered assets and richer environments |
| Animation | Shared rig, IK primitive in Python, 25 motion presets, timed tracks; Blender cyclic walk/run/wave, facial drawings and Rhubarb cue switching | Full IK/retargeting in Blender, contact/foot planting, hand poses, nuanced acting and transition polish |
| Camera and staging | Skia and Blender shot zoom/pan, actor positions and movement tracks | Lens language, multi-plane parallax and advanced camera choreography |
| Audio | Optional Piper local TTS adapter, timed clip mixer, dialogue/music/effects buses, dialogue-driven music ducking, loudness and peak limiting | Arabic voice model selection and dialect testing, detailed sound design and human mix approval |
| Lip sync | Rhubarb adapter maps recorded audio cues to visemes; Blender and Skia can consume cue data | Better phoneme mapping, face deformation and automatic cue quality review |
| Editing and subtitles | SRT export, exact frame edit plan, optional OpenTimelineIO timeline, FFmpeg H.264/AAC output | Full multi-track NLE project, transitions, subtitle burn-in and final human editorial pass |
| Technical QA | Full-frame decode/dimension/blank checks, audio gate, script QA, repair rounds and delivery manifest | Motion/scene semantic QA and reliable automated artistic evaluation |
| Artistic review | Explicit human sign-off is mandatory; technical reports do not impersonate artistic review | Repeatable human review checklist and structured notes/revision workflow |

## New commands

```powershell
python -m studio.cli doctor
python -m studio.cli script-qa projects/episode-001
python -m studio.cli audio-mix projects/episode-001
python -m studio.cli subtitles projects/episode-001
python -m studio.cli edit-plan projects/episode-001
python -m studio.cli blender-render projects/episode-001
```

## Production order

1. Generate story outline and director blocking.
2. Write dialogue and run `script-qa`.
3. Record dialogue and run Rhubarb lip sync where needed.
4. Prepare the timed audio mix and export subtitles/edit plan.
5. Render through Blender; the Skia renderer remains a fallback.
6. Run full technical QA and repair render defects.
7. A human watches the full video and approves or sends notes.
8. Only then finalize delivery.

## Explicit non-claims

The team is not yet a self-governing human-equivalent studio. It does not autonomously invent consistently excellent dialogue, produce original voice performances, judge whether every acting choice is emotionally right, or guarantee zero artistic errors. Those capabilities need a connected creative model, more complete character assets and human review. Do not mark an episode visually approved unless it was actually watched.
