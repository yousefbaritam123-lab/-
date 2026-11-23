# 15-second pilot render

This is a short-form **preview project**, not a replacement for the 100-second series episode target.

## Render locally (Windows PowerShell)

```powershell
python -m pip install skia-python imageio-ffmpeg Pillow
python -m studio.cli init projects/pilot-15s
Copy-Item examples/pilot-15s/episode.json projects/pilot-15s/episode.json -Force
Copy-Item examples/pilot-15s/continuity.json projects/pilot-15s/continuity.json -Force
python -m studio.cli validate projects/pilot-15s
python -m studio.cli render projects/pilot-15s --resume
python -m studio.cli encode projects/pilot-15s
```

The init command copies the canonical character rigs and motion library into the project. Output: `projects/pilot-15s/renders/episode.mp4`.

The pilot is a silent visual test. Dialogue is shown as Arabic captions when Pillow's RAQM text layout is available; recorded dialogue, lip-sync from real audio, Foley and final sound mix remain separate production work.
