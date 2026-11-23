# Quality control and episode delivery

The studio treats rendering as an intermediate production stage, not the final result.

## Gated workflow
1. Story, script and director blocking are drafts until reviewed.
2. Assemble a separate episode project; never overwrite the source.
3. Validate episode structure, references, motion tracks, durations and continuity.
4. Render every frame. Resume is permitted, but non-empty files alone do not prove correctness.
5. Run automated QC: complete frame coverage, empty files, sampled PNG decoding and dimensions, continuity/schema validation, and audio presence.
6. Repair the source or affected shots, rerender, and repeat QC.
7. Final encoding is blocked while any hard error remains.
8. Verify the MP4 file and, where ffprobe is installed, H.264 codec, dimensions and duration.
9. Write a delivery manifest only after verification.

## Commands
```powershell
python -m studio.cli validate projects/episode-001
python -m studio.cli render projects/episode-001 --resume
python -m studio.cli qc projects/episode-001
python -m studio.cli finalize projects/episode-001
```

QC writes production/quality_report.json. Finalize refuses to encode when blocking errors exist and writes production/delivery_manifest.json after successful checks.

## Current limits
This is automated engineering QA, not a replacement for artistic review. It cannot yet reliably judge acting quality, story coherence, every bad pose, awkward edits, or subtle sound defects. Image integrity is sampled, while presence and file size are checked for every frame. Future gates should add shot contact sheets, pose/motion anomaly detection, audio loudness and clipping analysis, dialogue coverage, subtitle checks, and explicit human approval.
