# Quality control and episode delivery

The studio treats rendering as an intermediate production stage, not the final result. The technical corrector is part of the production run, not a separate manual cleanup step.

## Automated technical correction

1. Preflight validates the episode schema, character/location references, motion tracks, continuity and dialogue timing. Invalid creative inputs are reported, not silently rewritten.
2. The frame renderer retries a failed frame up to three total attempts, deletes partial files, and decodes each PNG before accepting it. Resume skips only PNGs that decode and match the configured dimensions.
3. The production coordinator catches render exceptions instead of terminating the whole episode. It audits every expected frame, removes missing/corrupt/wrong-size/blank outputs, then resumes only the damaged frames for up to the configured repair rounds.
4. Audio QC opens the final WAV and checks stereo layout, 48 kHz, 24-bit PCM, full data payload and duration against the episode.
5. Encoding first revalidates every PNG. FFmpeg writes to a temporary MP4, retries once with a safer preset after a failed attempt, fully decodes the result, and only then replaces the final output.
6. Final QC checks H.264, frame dimensions and duration when ffprobe is available. A missing/invalid audio mix, any defective frame, or a failed encode blocks delivery.
7. The system writes production/production_run.json with repair rounds, failures and the final audit. It writes a delivery manifest only after all technical gates and human visual approval pass.

## Commands

```powershell
python -m studio.cli validate projects/episode-001
python -m studio.cli render projects/episode-001 --resume
python -m studio.cli qc projects/episode-001
python -m studio.cli production-run projects/episode-001 --repair-rounds 3
python -m studio.cli finalize projects/episode-001
```

`production-run` is the recommended end-to-end command. It performs bounded automatic repairs; it does not loop forever. If a defect remains after the repair budget, it blocks delivery and records the cause instead of exporting a broken video.

## Limits that remain

Technical correction does not mean artistic perfection. The corrector can catch file, decode, dimensions, blank-frame, audio-container, timing and encoding failures. It cannot yet reliably determine whether acting looks natural, a hand pose is anatomically convincing, a joke lands, a character's emotion is right, or a shot is aesthetically strong. Human visual approval remains mandatory and must only be recorded after the episode is actually watched.

The system does not silently modify story content, dialogue meaning, character identity or shot composition to hide a defect. Such changes require a production-level decision and a new visual review.
