# Production readiness — Youssef animated series

Status is intentionally split into technical readiness and artistic readiness. A green CI job is not a quality certificate.

## What is verified

- The 15-second Skia pilot renders and encodes to H.264 at 540×960, 30 FPS.
- The 10-second technical test produced 300 decodable 540×960 frames and a 10-second H.264 MP4.
- Tahoma2D v1.6.3 installs in the GitHub Actions Linux runner; its GUI starts under Xvfb and the \`tcomposer\` command interface is detected.
- Youssef and Adam source SVGs are preserved byte-for-byte and exported into canvas-aligned SVG parts. The arm and leg strokes are separated at vertices already present in the source drawing. Joint landmarks and a manifest are generated.
- Python tests, art-direction benchmark, Blender legacy integration, pilot render, and Tahoma2D installation/asset-preparation workflows have passed on the tested commit.

## Not yet production-ready

1. **Character art** — current source sheets are simplified line-art. Youssef's source does not actually draw the cream shirt or dark trousers described in its text/metadata; Adam's blue torso exists, but sleeves and hands are not separately illustrated. The preparation tool does not invent or repaint those missing details.
2. **Character rigs** — vector parts are exported, but no Plastic mesh or skeleton has been authored in Tahoma2D. No neutral-pose, wave, walk, turn, or deformation test has passed.
3. **Native Tahoma2D scene** — no genuine project \`.tnz\` containing the cast and rig has been authored and rendered. The current Tahoma2D CI workflow verifies installation, GUI startup and asset preparation only.
4. **Final output specification** — the current pilots are 540×960 preview renders, not the 1080×1920, 30 FPS episode master.
5. **Audio** — the 10-second technical test is silent. Dialogue voice performance, timing, ambience, effects, music mix and Arabic subtitle review are not certified by that test.
6. **Artistic review** — the pilot contact sheet shows the current result is still a basic animatic with limited acting and repeated poses. It is useful for validating the pipeline, not for publication.

## Required departments before the first publishable episode

- **Character art:** complete the approved source drawings without changing identity locks; create separate deformable clothing, hair, hands and face/expression levels where the source art supports them. Any new artwork must be reviewed against the official character references.
- **Rigging:** author Plastic meshes/skeletons in Tahoma2D; verify neutral pose, front/side turns where available, walk, run, wave, talk, hand contact and cloth stability.
- **Animation/layout:** establish shot blocking, camera continuity, acting beats, background depth and secondary motion. Reject frozen or repeated acting where motion is required.
- **Dialogue/audio:** produce approved Algerian Arabic dialogue, lip-sync cues, ambience, effects and final mix; verify intelligibility and sync.
- **Editorial/QC:** inspect every shot and the full episode, check continuity, Arabic captions, frame integrity, audio peaks/clipping, output dimensions and encode; require a real reviewer approval before finalization.

## Safe start command sequence

Use a new isolated episode project; do not overwrite the 15-second pilot:

\`\`\`powershell
python -m studio.cli init projects/episode-001
python -m studio.cli story-next projects/episode-001
python -m studio.cli storyboard projects/episode-001
python -m studio.cli tahoma2d-prepare projects/episode-001
python -m studio.cli validate projects/episode-001
python -m studio.cli script-qa projects/episode-001
\`\`\`

This starts pre-production and asset preparation. Do not render a full 100-second master until the character rigs, storyboard, voices and scene assets pass their respective reviews.

## Honest completion rule

A project is **ready for animation production** only after at least one actual Tahoma2D \`.tnz\` scene renders the approved character rig and passes visual review. It is **ready for episode delivery** only after the full 1080×1920 master, complete audio, frame/audio QC and human visual approval pass. The current repository has not reached either gate yet.
