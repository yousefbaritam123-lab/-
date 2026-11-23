# Character Rig V2 — production notes

## Runtime controls

The 2D rig now exposes a consistent joint graph per character:

- Torso, neck and head pivot
- Left/right shoulder, elbow, wrist, palm and three simplified finger rays
- Left/right hip, knee, ankle/foot and toe direction
- Facial controls: blink, gaze X/Y, brow, mouth-open and emotion

All limb lengths are read from each character's `proportions` object. Character-specific `joint_limits` constrain shoulder, elbow, hip and knee rotations before the renderer builds the pose.

## New animation clips

`point`, `think`, `celebrate`, `sad`, and `surprised` supplement the existing idle, walk, run, wave, talk, jump, dodge and impact reactions.

Clips are deterministic and interpolate keyframes with smooth easing. Non-looping clips hold their final pose; looping clips wrap by duration. Unknown clip names safely fall back to idle.

## Face and hands

The renderer draws wrist-to-palm connections and finger rays, angles shoes with the foot/toe direction, supports gaze offsets, periodic blinks, eyebrow changes, mouth-open cues and a simple smile/frown curve.

## Current limitations (do not overstate)

- `solve_two_bone` is available as a planar two-segment IK primitive and is unit-tested, but the current default animation path is still primarily keyframe-angle driven.
- There is no persistent world-space foot planting / ground-contact solver yet.
- Hands are stylized three-ray shapes, not a full five-digit hand mesh with individual phalange rigs.
- Face animation is procedural and limited; it is not phoneme-level lip sync and does not infer emotion from recorded speech.
- No automatic motion retargeting or physics simulation is implemented.

## Editing a character

Each character's `character.toon.json` defines its stable appearance, proportions and joint limits. Keep identity-defining values (head silhouette, eye spacing, signature clothes and palette) stable. Add new clips to `studio/rig.py` defaults and the production motion library when they become approved shared motions. Add tests for every new joint control or clip.
