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

Face controls include blink, gaze X/Y, brow, mouth-open amount and emotion. The renderer currently draws stylized eyes and mouth states; it is not yet phoneme-accurate lip-sync.

## Honest limitations

The 60 entries are reusable procedural variants, not 60 individually illustrated character sheets. They share one skeleton topology. Hands expose five digit endpoints but are still rendered as simple strokes, not detailed polygonal hands. IK is now available for explicit hand/ankle targets, but there is not yet a full animation constraint graph, automatic foot planting across root motion, or production-grade motion retargeting. The reference poster is concept art and is not itself a runtime asset.

## Validation

Run `python -m unittest discover -s tests -v` from the repository root.
