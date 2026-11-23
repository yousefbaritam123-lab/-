# Maven Toon

**Version 1.0** by Maven (Instagram @maven.iqq, YouTube maveniqq). A Claude skill that writes and renders vertical
2D cartoon Shorts: round-headed ink characters (with an Iraqi / Arab everyday cast), painted parallax sets (tea house,
souq, Tigris riverside, classroom, Baghdad rooftop and more), light that follows the story, a camera that never
stops, and Arabic (right-to-left) or English captions timed to every word.

* Input: a story idea, or `script.txt`, plus optionally `voice.wav` and your own `music.*`.
* Output: `final.mp4`, 1080x1920, 30 fps, -14 LUFS.
* Runs on CPU with `pip install -r requirements.txt` on Windows, macOS, Linux and in the Claude phone app sandbox.
  Rendering is resumable in short time-boxed runs (about 5 minutes for a 60 s Short on 2 cores).

## On your phone (Claude app)

1. In a browser, at claude.ai > Settings > Capabilities, turn on **Code execution and file creation** and
   **Use internet while making files** (package managers is enough). Then start a NEW chat in the app.
2. Attach `maven-toon.zip` (don't unzip it) and, if you have one, your voice file.
3. Paste a prompt from `PROMPTS.md`, fill in your words or your idea, send. Type `continue` if it stops before DONE.

## On a PC

```bash
python -m venv .venv && .venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python toon.py doctor
python toon.py silent examples/chai-ar --duration 15   # captions-only Arabic example (no voice needed)
python toon.py plan examples/chai-ar
python toon.py stills examples/chai-ar
python toon.py render examples/chai-ar --workers 4     # repeat until DONE
python toon.py join examples/chai-ar
python toon.py check examples/chai-ar
```
With a voice: put `voice.wav` next to `script.txt` and run `python toon.py words <project>` instead of `silent`.
Write and check a script: `python toon.py script <project> --seconds 30`.
See the kit: `python toon.py library out --cast`.

## What gets installed and downloaded

* pip installs skia-python, numpy, imageio-ffmpeg (includes an ffmpeg executable, GPL), faster-whisper and Pillow,
  about 400 MB. Use a virtual environment so nothing touches your system Python.
* The first `words` run with a voice downloads one speech model from huggingface.co into `<project>/.models`:
  `small` (multilingual, Arabic, ~480 MB) or `small.en` (English). `silent`, `words --from FILE` and
  `words --offline` download nothing. Nothing is ever uploaded.

## Rights

Free to use for your videos, including monetised ones. The Maven parts may not be sold or re-shared except through
Maven's link: `rights/MAVEN-RIGHTS.txt`. The engine underneath is based on toon2d-shorts (MIT,
`rights/toon2d-shorts-MIT.txt`); fonts are OFL; third-party details in `rights/THIRD_PARTY.md`.
