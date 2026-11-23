# Layered character input for Blender

For a character to bend at joints, provide separate transparent PNG layers rather than one flattened image. Recommended parts:

- head, torso
- upper_arm.L, forearm.L, hand.L
- upper_arm.R, forearm.R, hand.R
- thigh.L, shin.L, foot.L
- thigh.R, shin.R, foot.R

Add a character object to episode.json using the following structure. Image paths are relative to the episode project's assets/ directory. Offsets and sizes are in Blender scene units and must be adjusted to the artwork.

```json
{
  "id": "hero",
  "name": "Hero",
  "layered_parts": {
    "head": {"image":"characters/hero/head.png","bone":"head","offset":[0,0,0],"size":1.4},
    "torso": {"image":"characters/hero/torso.png","bone":"torso","offset":[0,0,0],"size":2.4},
    "left_upper_arm": {"image":"characters/hero/upper_arm_left.png","bone":"upper_arm.L","offset":[0,0,0],"size":1.2},
    "left_forearm": {"image":"characters/hero/forearm_left.png","bone":"forearm.L","offset":[0,0,0],"size":1.0},
    "left_hand": {"image":"characters/hero/hand_left.png","bone":"hand.L","offset":[0,0,0],"size":0.55}
  }
}
```

Repeat for the right arm and both legs. The bone field must match supported names in tools/blender_scene.py. The bridge creates a rigid 2D armature and attaches image planes to bones. It does not infer missing limbs, paint hidden pixels, generate facial expressions, or create finished animation clips. Before production, correct pivots and offsets in Blender and animate/test the armature. Keep a copy of the source artwork and approved rig.
