---
name: maven-toon
description: Maven Toon, by Maven (@maven.iqq). Makes vertical 1080x1920 cartoon Shorts (15-70 s) in a rich 2D style - round-headed ink characters with detailed costumes (including an Iraqi / Arab cast - hajji in shmagh, hajjiya in abaya, teacher, students, tea seller, farmer, doctor, footballer - plus cat and camel), painted parallax sets (tea house, souq, Tigris riverside, classroom, Baghdad rooftop and 11 more), light that follows the story, a camera that never stops, and Arabic or English captions on the word onsets. Writes the script too (Iraqi or fusha Arabic, or English). CPU only, works in the Claude phone app sandbox and on a PC. Use when asked to write, plan, render or fix a 2D cartoon Short, a Maven Toon video, a story Short from a voice-over, or a captions-only Short.
---

# Maven Toon

Turns `voice.wav` + `script.txt` (+ optional `music.*` the owner supplied) into `final.mp4`: 1080x1920, 30 fps,
-14 LUFS, burned-in captions (Arabic right to left in Lalezar, English in Poppins). No voice? `script.txt` alone makes
a captions-only Short. No script? Write it first (step 1). Everything is pip-installable and CPU-only.

Commands use `python toon.py ...` from the skill folder. On this PC (Maven's), use
`D:\reels\tools\maven-toon-venv\Scripts\python.exe` (skia, numpy, imageio-ffmpeg, faster-whisper installed).

## 0. Setup: run doctor first (every new machine, sandbox or chat)

```bash
python toon.py doctor                     # checks skia-python, numpy, imageio-ffmpeg (+ ffmpeg); optional ones listed
pip install -r requirements.txt           # only if doctor says packages are missing (or: python toon.py doctor --install)
python toon.py doctor                     # must end with DOCTOR OK before anything else
```

If doctor says pip cannot reach the package index, or `pip install` fails with a network error, stop and tell the
user exactly this (in their language): "Turn on Code execution and file creation and Use internet while making files
in Settings > Capabilities on claude.ai in your browser (not in the app), then start a NEW chat." In Arabic:
"فعّل Code execution and file creation و Use internet while making files من Settings > Capabilities بموقع claude.ai
بالمتصفح (مو بالتطبيق)، وبعدين افتح محادثة جديدة."

* Use `python` as written; on macOS/Linux use `python3` if `python` is missing; on Windows never `python3` (it opens
  the Microsoft Store stub), use `python` or `py`.
* Never ask for a Hugging Face token or any key. Never open or print `.env` files. Nothing is uploaded anywhere.
* **Phone / cloud sandbox:** every step finishes in under ~4 minutes. `render` is time-boxed (`--budget 200`, use
  `--budget 90` if commands are cut at 2 min) and resumable: run it again until it prints `DONE`. `--workers 2` on 2
  CPUs. Ask the user to keep the app open. If the sandbox resets, ask for the zip again, run doctor, write the script
  and storyboard back from the chat, redo `words`/`silent`, then `plan` and `render`. Never ask them to start over.
* **PC:** raise `--workers` to the cores you want to use.

## 1. Script (when the user has a story, an idea, or nothing yet)

Read `references/script-ar.md` (Arabic: Iraqi by default, fusha on request) or `references/STYLE.md` (English).
- No idea yet: give 10 one-line ideas with their hooks (script-ar.md section 10); the user picks one.
- Ask the length (15 s for a first try) if not given. Arabic voice ~2.1 words/s: 15 s ≈ 30 words, 30 s ≈ 60.
- Write `script.txt`, one sentence per line, in the shape: hook (≤ 7 words, a strange fact, no question) → context →
  escalation (بس / فـ / وبعدين) → turn (`تدري ليش؟` / "You see,") → short payoff, ideally a callback.
- Check it: `python toon.py script PROJECT --seconds 15` and fix everything it lists.
- Show the user the script and a one-line shot note per sentence (set / mood / who does what) before the voice is
  made. If the user already has a recorded voice, the words are fixed: copy them exactly, never "improve" them.

## 2. Project folder

Make each project folder OUTSIDE the skill folder (copy `examples/chai-ar` or `examples/demo`, or start empty):
```
myshort/
  voice.wav        the narration (starts at 0.0 s); captions only: `silent` writes a silent one
  script.txt       the exact words, one sentence per line
  music.mp3        OPTIONAL, only a track the owner supplied (never fetch music)
  storyboard.json  you write this in step 4
```
Voice files in other formats (mp3, m4a, ogg): convert with the bundled ffmpeg:
`python -c "import imageio_ffmpeg,subprocess,sys;subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-i',sys.argv[1],'-ac','1','-ar','48000',sys.argv[2]])" in.mp3 myshort/voice.wav`

## 3. Word timings

**With a voice:** `python toon.py words myshort` -> `words.json`. Arabic is detected from script.txt (`--lang ar`);
whisper `small` (multilingual) runs with the script as a hint, Arabic letters are compared without diacritics.
Order: an existing words.json is kept (`--force` redoes it); `--from timings.json` (ElevenLabs "with timestamps" or a
word,start,end CSV/JSON) is imported; else whisper (downloads once into `<project>/.models`); else the built-in
aligner (no download, prints a WARNING, captions may be slightly less exact). The script's spelling always wins.
On a strong PC `--model large-v3-turbo` gives the best Arabic times.

**No voice (captions only):** `python toon.py silent myshort --duration 15` writes a silent voice.wav, reading-pace
timings (Arabic 2.0 words/s, English 2.3) and words.json, and prints the `end_pad` for the storyboard.

Print the words with their index; you need the indices for the storyboard.

## 4. Write storyboard.json (the creative step)

Read `references/STYLE.md` (the look) and `references/LIBRARY.md` (every set, mood, character, pose, expression,
prop, hold item and framing shorthand). `examples/chai-ar/storyboard.json` (Arabic) and `examples/demo` (English)
are complete examples.

* **Scenes change only when the set or the light changes.** Light = act structure: `day`/`interior` setup, `night`
  for tension/secrets/waiting, `dream` for memories, `golden` for the explanation ("تدري ليش؟" / "You see"),
  `sunset`/`dawn` for the ending. Aim for a darker middle (50-70 %) and a more saturated ending.
* **keys**: one framing per sentence or clause (`{"w": word_index, "frame": ...}`); the director adds beats every
  ~0.86 s, eases moves over 19 frames and keeps faces whole. Tightest `h` 800. Push-ins about 2:1 over pull-outs.
  An extreme close-up of the key object inside the first second. `"calm": true` on the explanation scene.
* **frame** = `[cx, cy, h]` in set pixels, or `"wide"`, `"two"`, `"<actor>"`, `"<actor>:face"`, `"<actor>:full"`.
* **cast**: `type`, `x`, `y` (feet), `scale`, `z` (the set's ground plane, see LIBRARY.md), `pose`, `expr`, `face`,
  `dir`, optional `prop`. Animals: `cat`, `camel`, `dino`. Same-z actors draw in list order (far ones first).
* **acts**: per-word changes: `pose`, `expr`, `x`/`y` (walks there), `talk` (mouth flaps for quoted lines), `hold`
  (`tea`, `tray`, `book`, `phone`, `ball`, `samoon`, `money`, `dates`, `misbaha`, `sign:نص`, `tag:نص`,
  `newspaper:سطر|سطر`, `earth`), `prop`.
* Arabic story: `"lowercase": false`. Explanations live **inside the set** (a sign, a tag, the chalkboard via
  `"set_args": {"board": "..."}`, a newspaper), never a floating card.

## 5. Plan, stills, critic loop

```bash
python toon.py plan myshort              # -> plan.json, prints beats/min and caption count
python toon.py stills myshort            # -> stills/*.png (one per scene + every 3rd beat)
```
Look at every still. Score each 1-10 on characters, set detail, light, depth and caption readability; fix anything
under 8 (framing keys, actor placement, mood, a prop hidden behind a plane, a caption over a face). Show the user 3
stills before the full render. `stills --at 3.2,7.5` renders exact times.

## 6. Render (resumable), join, check

```bash
python toon.py render myshort --workers 2     # repeat until it prints DONE
python toon.py join myshort                   # -> final.mp4 (voice + optional music bed ~14 dB under, -14 LUFS)
python toon.py check myshort                  # format, loudness, pacing, captions, faces cut by an edge
```
First render bakes the sets (~1 min, cached in `<project>/.cache`), then ~0.1 s per frame per core.

## 7. Hand-off

Give the user `final.mp4`, the title (the hook in ≤ 6 words), a one-line description with hashtags, and, if they want
music, where it should sit (they add it in their editor, or put their own `music.mp3` in the project and re-run
`join`). On Maven's PC, sound effects come from the `real-sfx` skill and the master must stay -14 LUFS / -1.5 dBTP.

## Other commands

`python toon.py library OUT [--sets a,b] [--moods day,night] [--cast]` preview sheets of sets and cast.
`python toon.py bench PROJECT` seconds per frame.

## Rules

* Characters, sets and logos stay original. Never imitate an existing show, channel, character or brand.
* Only music the owner put in the folder. Never download music.
* Captions: 1-2 words, centred at 70 % height in the safe zone; the renderer draws them, add no other text overlays.
* If a still looks flat: a near-foreground object, a practical light, or a stronger light change. Not more text.
* Facts in a script must be true; list sources for the user under the script.

## Files

`toon.py` launcher. `engine/` (character.py + cast_iq.py characters and animals, sets.py/outdoor.py/interiors.py/
prehistoric.py + sets_iq.py sets, setkit.py/textures.py/props.py pieces, light.py moods, scene.py camera, director.py
beats and captions, text.py Latin + Arabic text, words.py timings, silent.py, scriptcheck.py, library.py, render.py,
audio.py, checks.py/qa.py). `references/` style, script guide, library, preview sheets. `rights/` licences.
`PROMPTS.md` ready-to-paste prompts for the phone.
