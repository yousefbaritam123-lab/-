# YOUSSEF — Character & Motion Bible

Canonical reference pack for the autonomous Algerian daily-life 2D series. This project is separate from MYSTERY PIXEL.

## Cast
- Youssef: protagonist; warm rounded face, fixed eye spacing, cream shirt, dark trousers, red shoes and permanent red neckerchief. Curious, kind, stubborn, brave but not fearless.
- Adam: recurring friend starter design; oval face, blue jacket, dark trousers; loyal, observant and dry-humored.
- Add family, neighbors and temporary characters as separate IDs with their own rig, model sheet and continuity rules. Do not overcrowd an episode.

## Asset authority
- assets/characters/<id>/character.toon.json is the machine-readable identity source.
- design_sheet.svg is the artist/reviewer model sheet.
- assets/motions/motion_library.json contains reusable motion beats.
- assets/locations/*/location.json defines environment style and continuity.

## Animation rules
Every action needs anticipation, readable key pose, follow-through and recovery. Plant feet on contact; use opposing arm/leg phases; add head lag and secondary scarf motion. Dialogue needs timed mouth cues and varied restrained gestures. Jump is crouch, takeoff, apex, landing compression, settle. Keep screen direction consistent across cuts.

## Production team workflow
Story editor defines intent and emotional change. Character designer checks identity locks. Director chooses clips and acting beats. Animator refines arcs, contacts and timing. Layout artist uses stable environment layers and prop IDs. Editor checks pacing. QC compares frames to model sheets and continuity state.

## Learning loop
Only approved corrections become reusable motion variants or notes. Log episode, shot, reviewer decision and reason in production/approved_learning_log.json. The system does not automatically train a neural model; it accumulates reusable approved assets, clips and documented corrections. Never let an unreviewed generated frame overwrite canonical designs.

All SVG and JSON files here are original project assets authored for this repository.