# Character pack: 60 procedural extras + articulated hero rig

## What is included

- `assets/characters/cast_60/catalog.json`: 60 distinct procedural character profiles. Each profile has its own palette, proportions and optional scarf while sharing the same compatible humanoid skeleton and motion library.
- `assets/characters/youssef/character.toon.json`: the canonical Youssef appearance and continuity lock. Do not replace it with a generated extra.
- `studio/rig.py`: deterministic keyframe rig, optional end-effector IK targets, joint limits, face controls, and five stylized digit endpoints per hand.

## Runtime controls

An animation pose may optionally include any of these local-space targets:

- `left_hand_target_x`, `left_hand_target_y`
- `right_hand_target_x`, `right_hand_target_y`
- `left_ankle_target_x`, `left_ankle_target_y`
- `right_ankle_target_x`, `right_ankle_target_y`
- `left_ik_bend`, `right_ik_bend` (positive/negative bend side)

When a complete target pair is supplied, the rig solves the elbow or knee with the two-bone solver. Targets are clamped to the limb's reachable range by the solver. Without targets, the existing keyframed animation remains the default.

## Available built-in actions

`idle`, `walk`, `run`, `wave`, `talk`, `jump`, `point`, `think`, `celebrate`, `sad`, `surprised`, `dodge`, `impact_react`.

Face controls include blink, gaze X/Y, brow, emotion, and numeric mouth shapes. Dialogue lines may optionally contain timed `visemes` cues relative to `start_seconds`; supported shapes are `REST`, `A`, `E`, `I`, `O`, `U`, `CLOSED`, `SMILE`, and `FROWN`. This is cue-driven stylized mouth animation, not automatic phoneme extraction from audio. For audio-derived timing, generate cue timestamps with Rhubarb or another licensed speech-analysis tool and attach them to the dialogue line.

Clip changes can crossfade by adding actor metadata such as `transition: {"from_action":"idle","start_seconds":0.0,"duration_seconds":0.25}` while setting the actor's target `action` to the destination clip.

## Honest limitations

The 60 entries are reusable procedural variants, not 60 individually illustrated character sheets. They share one skeleton topology. Hands expose five digit endpoints but are still rendered as simple strokes, not detailed polygonal hands. IK is available for explicit hand/ankle targets. The renderer now anchors the support foot during walk/run cycles and compensates for actor root travel and vertical bob. This is a deterministic two-bone foot-lock approximation, not a full animation constraint graph, physically based contact solver, or production-grade motion retargeting. The reference poster is concept art and is not itself a runtime asset.

## Validation

Run `python -m unittest discover -s tests -v` from the repository root.
