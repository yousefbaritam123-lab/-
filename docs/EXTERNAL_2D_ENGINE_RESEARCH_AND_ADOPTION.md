# External 2D Animation Engine Research and Adoption

Research date: 2026-11-24
Target: YOUSSEF autonomous 2D series production system.

## Decision

Do not vendor a complete animation editor into the Python/Blender pipeline. The reviewed projects solve different layers of the problem. Adopt compatible algorithms and formats behind small adapters, retain the current episode/story/continuity/QC pipeline, and keep full desktop animation applications as optional external authoring tools.

## Repositories reviewed

| Project | What it contributes | License / redistribution finding | Decision |
|---|---|---|---|
| [Tahoma2D](https://github.com/Tahoma2D/tahoma2d) | Full 2D and stop-motion authoring workflow, based on Toonz; production timeline and drawing tools | Project README says files outside thirdparty and MyPaint brush library use Modified BSD; subdirectories have separate licenses | Study workflow and file interchange. Do not embed the whole C++ desktop application in the Python runtime |
| [OpenToonz](https://github.com/opentoonz/opentoonz) | Mature 2D animation application and production workflow | GitHub API did not provide a definitive SPDX license in this review; verify each relevant component before copying | Reference only until component licensing is verified |
| [Synfig](https://github.com/synfig/synfig) | Vector/bitmap tween animation, layers and deformation-oriented 2D workflow | GPL-3.0 | Study concepts; do not copy source into this project without an explicit project-wide GPL decision |
| [Skele2D](https://github.com/1j01/skele2d) | Named joints/segments, serializable skeleton structures, reusable poses, interpolation and blended animations | GitHub metadata reports MIT | Best small algorithm reference. Its browser/CoffeeScript editor is not a drop-in Python/Blender renderer |
| [Creature WebGL](https://github.com/kestrelm/Creature_WebGL) | Mesh/bone deformation and runtime playback | Important: repository LICENSE.md is a custom Kestrel Moon license. It allows use and modification but expressly restricts distribution of derivative works. It is NOT Apache-2.0 despite the repository metadata | Do not copy or vendor its runtime. Reimplement general deformation concepts independently if needed |
| [Tiny 2D Rig Tools](https://github.com/NickTiny/Tiny-2D-Rig-Tools) | Blender Grease Pencil cut-out rig, armature generation, IK drivers, mouth/hand time offsets and turnaround controls | No clear repository license was found during this review | Do not copy its code. Use feature behavior as a design reference and implement our own Blender adapter |
| [Rhubarb Lip Sync](https://github.com/DanielSWolf/rhubarb-lip-sync) | Audio-to-mouth-cue generation | GitHub metadata did not provide a definitive SPDX license in this review; verify release/package license before redistribution | Keep current optional external executable adapter; do not bundle binaries/source until license and version are verified |
| [Blender Rhubarb Lip Sync add-on](https://github.com/scaredyfish/blender-rhubarb-lipsync) | Maps Rhubarb mouth cues to Blender pose-library keyframes | README explicitly says it is unmaintained and does not work on Blender 3.2+ | Do not integrate this add-on; retain our own cue-to-viseme bridge |
| [Manim Community](https://github.com/ManimCommunity/manim) | Python scene graph, timing, animation composition and deterministic rendering | MIT | Not a character animation engine; useful only for non-character motion graphics if later needed |
| [Motion Canvas](https://github.com/motion-canvas/motion-canvas) | Timeline/editor, code-driven vector animation and voice-over synchronization | MIT | TypeScript/browser renderer; not a drop-in for the Python/Blender character pipeline |
| [Remotion](https://github.com/remotion-dev/remotion) | Programmatic video composition, templates, batch rendering and editing | Repository licensing is not a simple permissive OSS license; check current commercial terms | Not selected for the core engine; possible separate composition service only after license review |

## What is already present in our project

- Deterministic keyframe sampling and looping clips in `studio/rig.py`.
- Cross-fade blending between two clips.
- Two-bone planar IK and proportion-aware joint construction.
- Per-character joint maps and motion tracks.
- Rhubarb JSON parsing and viseme attachment to dialogue shots.
- Blender rendering and final audio/video assembly.
- Technical frame audits and human visual approval gate.

This means copying Skele2D's entire editor would duplicate existing pose/segment concepts while adding a separate JavaScript runtime that does not drive our Blender scene.

## Adopted architecture

1. Keep `studio/rig.py` as the deterministic pose/IK authority.
2. Implement a native Blender cut-out rig adapter in our own code. It will create armature bones, pivots, IK constraints and layered image planes from the extracted source artwork.
3. Use original SVG art and extracted layers. Never replace the cast with generic procedural stick figures.
4. Preserve a whole-character transparent image fallback whenever the source art cannot be segmented safely.
5. Keep Rhubarb as an optional external tool, then map its mouth cues into our own viseme system. Do not rely on the obsolete Blender add-on.
6. Keep Tahoma2D/OpenToonz as optional external authoring tools, not mandatory dependencies of automated rendering.
7. Evaluate mesh deformation only after a redistribution-compatible implementation is selected. Creature WebGL source is not eligible for vendoring under its custom license.

## Required acceptance tests before calling the new rig production-ready

- Neutral-pose composite matches the original character artwork without visible gaps or missing strokes.
- Every arm and leg segment rotates around its intended pivot.
- IK reaches targets within the two-bone reachable range and clamps safely outside it.
- No limb flips unexpectedly during animation or transition blending.
- Feet remain planted during walk/run contact phases.
- Mouth cues follow the real audio timeline and do not drift between shots.
- Character appearance and proportions remain stable across all shots and episodes.
- Rendered sample is visually reviewed; technical frame validity alone is not visual approval.

## Source inspection notes

- Tahoma2D README documents its Modified BSD boundary and separate third-party/brush licenses.
- Skele2D's `BoneStructure`, `Structure`, and `Pose` show a small named-point/segment model and pose interpolation approach.
- Creature WebGL's own LICENSE.md is a custom license; the repository's GitHub license metadata is misleading for redistribution decisions.
- Tiny 2D Rig Tools describes useful IK/driver behavior, but no clear license was located. Its source is not copied.
- The Blender Rhubarb add-on README states it is not compatible with Blender 3.2 and above.

## Adopted components

### Skele2D structure and pose model

- Vendored the upstream `BoneStructure.coffee`, `Structure.coffee`, and `Pose.coffee` reference files under `vendor/skele2d-reference/source/structure/`, with the upstream MIT `LICENSE.txt` and copyright notice.
- Added `studio/skeletal_graph.py`, an independently written Python runtime adapter for named joints, bone segments, serializable skeleton graphs, pose interpolation, loop interpolation, and horizontal/vertical pose flips.
- `studio/svg_character_assets.py` now exports a named-joint graph alongside the existing joint and bone fields in each extracted character rig manifest. The existing legacy fields remain available.
- Added tests for graph serialization, invalid joint references, finite coordinates, pose interpolation, and loop interpolation.
- The CoffeeScript reference files are retained for attribution/reference; the Python adapter is the runtime implementation. The browser editor and its UI are not part of our runtime.

### Earlier loop-seam improvement

`studio/rig.py` independently interpolates the last keyframe back to the first across loop boundaries. A regression test checks continuity around the cycle seam.

This is a real model/runtime integration, not a complete external animation engine import. The Blender scene renderer still uses whole-character raster planes for original artwork; per-limb Blender cut-out animation is not yet integrated or visually approved.
