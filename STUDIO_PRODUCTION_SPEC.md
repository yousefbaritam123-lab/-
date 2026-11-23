# Stickman Animation Studio Pro — Production Specification

## Product goal

Build a free-first, locally renderable 2D animation production system for serialized vertical episodes. It must produce coherent, edited episodes—not slideshow videos or unrelated AI images.

## Episode contract

- Canvas: 1080 × 1920 (9:16)
- Frame rate: 30 fps
- Target duration: 100 seconds (3,000 frames)
- Language: Algerian Arabic dialogue and narration
- Delivery: MP4 (H.264 video + AAC audio), plus project source and render diagnostics
- Character continuity: stable character IDs, immutable visual reference sheets, reusable rigs, persistent wardrobe/voice/personality definitions, and episode-to-episode story state

## Production departments (automated pipeline)

1. **Story editor** — episode premise, hook, conflict, escalation, payoff, continuity checks against prior episodes.
2. **Screenwriter** — dialogue and narration in natural Algerian Arabic; timed dialogue lines and speaker IDs.
3. **Director** — converts the script into shots, blocking, staging, screen direction, camera intent, and shot durations.
4. **Character department** — creates and validates layered vector artwork, reusable skeletons, face controls, mouth visemes, hands, and wardrobe variants.
5. **Animation department** — keyframes, IK, anticipation, follow-through, arcs, holds, walk/run cycles, gestures, secondary motion, and expression changes.
6. **Background / layout** — reusable locations, foreground/midground/background layers, parallax, props, and lighting continuity.
7. **Camera department** — shot framing, motivated pans, pushes, tracking, cuts, transitions, and safe composition for 9:16.
8. **Sound department** — dialogue, narration, ambience, Foley, effects, and licensed/user-provided music; ducking and loudness normalization.
9. **Editorial** — shot assembly, rhythm, transitions, captions, audio mix, and final encoding.
10. **Quality control** — missing assets, character drift, clipping, foot sliding, bad lip sync, silent gaps, audio peaks, flicker, continuity errors, and export validation.

## Technical direction

Use a proven open-source animation runtime instead of writing a skeletal renderer from scratch.

- **Animation core candidate:** animeStudio (deterministic SVG character rigs, IK, animation clips, scene documents, cinematic camera, lighting, cartoon FX, lip-sync helpers, and Remotion rendering). It is the strongest match for scriptable, repeatable episode generation. Before vendoring or redistributing code, verify its explicit license and third-party asset terms.
- **Authoring/editor candidate:** Rigby2D (MIT OR Apache-2.0 source; skeletal editor, meshes, IK, physics, audio/lip-sync and film export). Use as an optional rig-authoring tool if its file/runtime interoperability is practical. Do not assume its demo artwork or trademarks are reusable.
- **Video assembly:** Remotion for deterministic composition and FFmpeg for final audio/video encoding and validation.
- **Project orchestration:** TypeScript/Node.js CLI with JSON schemas for episodes, characters, scenes, shots, dialogue, and continuity state.
- **No paid API dependency:** all core rendering and assembly must run locally. Optional AI writing or voice services must be replaceable; never make the renderer depend on them.

## Non-negotiable engineering rules

- Never regenerate a character's appearance from scratch for each shot.
- Every character has a stable ID and a versioned canonical rig/reference sheet.
- Every episode stores a machine-readable continuity record (events, relationships, wardrobe, injuries, locations, props, unresolved threads).
- Every shot is reproducible from its source files and configuration.
- Every render is resumable and logs frame ranges, failures, and checks.
- Use PNG frames or lossless intermediate output for line-art; avoid lossy intermediate encoding.
- Do not fabricate sound assets or use copyrighted music without permission.
- Keep the current Maven Toon files untouched until the replacement pipeline passes a complete test render.

## Definition of professional quality

A feature is not considered complete merely because it exists. It must pass a rendered test scene and visual/audio review. The first quality gate is a 10–15 second pilot containing: two characters, a location with layered depth, a dialogue exchange, at least one camera move, expressive acting, lip-sync, Foley/ambience, and a clean final export.

## Implementation milestones

1. Audit current repository, licenses, runtime compatibility, and machine requirements.
2. Establish the new TypeScript project and dependency lockfile on this branch.
3. Build one canonical stickman rig and one reusable location.
4. Render the 10–15 second pilot and run automated QC.
5. Add the episode compiler (script → storyboard → shots → animation cues).
6. Add continuity database and reusable character/location library.
7. Scale to the 100-second episode contract only after the pilot passes.

## Hardware-aware defaults

Target the user's Windows laptop class (Ryzen 5 4500U, 16 GB RAM) with conservative render concurrency and resumable frame batches. Keep 1080 × 1920 / 30 fps as the delivery target, but allow low-resolution previews for iteration. Cloud CI is for tests and packaging, not assumed to provide unlimited free video rendering.
