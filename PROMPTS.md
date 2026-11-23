# Maven Toon prompts (copy, fill in, paste)

Attach `maven-toon.zip` first (and your voice file for prompt 1). Start a NEW chat after turning on the two
settings at claude.ai > Settings > Capabilities.

---

## 1. عندي صوت (with a voice-over)

```
فك ضغط maven-toon.zip المرفق، اقرأ SKILL.md واستخدم السكل حتى تسوي شورت كرتون من التعليق الصوتي المرفق.

الكلام بالضبط مثل ما بالصوت:
[الصق كلامك هنا]

القصة بجملة أو جملتين: [منو، وين، شنو صار، شنو المفاجأة]

اتبع SKILL.md خطوة خطوة: شغّل doctor أول (نزّل الحزم إذا طلب)، حوّل الصوت إلى voice.wav، احفظ الكلام بـ script.txt،
طلّع توقيت الكلمات، اكتب storyboard من الأماكن والشخصيات الموجودة بالمكتبة والإضاءة تمشي ويا القصة،
ورّيني 3 صور تجريبية، بعدين رندر لحد ما يگول DONE، وبعدين join و check وانطيني final.mp4.
```

## 2. ما عندي صوت (captions only)

```
فك ضغط maven-toon.zip، اقرأ SKILL.md وسوّي شورت كرتون بدون صوت، القصة تنحچى بالكابشن بس.
المدة: 15 ثانية.
القصة: [منو، وين، شنو صار، شنو المفاجأة]
اكتب السكربت بالعراقي حسب references/script-ar.md، افحصه بأمر script، وبعدين silent و plan
وورّيني 3 صور، بعدها رندر لحد DONE و join و check وانطيني final.mp4.
```

## 3. ما عندي فكرة (ideas + script first)

```
فك ضغط maven-toon.zip واقرأ SKILL.md و references/script-ar.md.
انطيني 10 أفكار لشورت كرتون عراقي، كل فكرة بسطر ويا الهوك مالها.
أنا أختار وحدة، وانت تكتب السكربت ([15/30] ثانية، [عراقي/فصحى]) وتفحصه بأمر script،
وتكتبلي تحت كل جملة شنو المشهد. لا تسوي الفيديو لحد ما أوافق على السكربت.
```

---

## 1. EN: with a voice-over

```
Unzip the attached maven-toon.zip, read its SKILL.md and use that skill to make a Short from my attached voice-over.

The exact words of the voice-over:
[paste your text here]

The story: [1-2 sentences: who, where, what happens, the twist]

Follow SKILL.md step by step: run doctor first (install the packages if it asks), convert my voice file to
voice.wav, save my words as script.txt, get the word timings, then write the storyboard with the sets and characters
from the library, with the light following the story. Show me 3 stills, then render until DONE, join, check, and give
me final.mp4.
```

## 2. EN: captions only

```
Unzip maven-toon.zip, read SKILL.md and make a 15-second captions-only cartoon Short (no voice).
The story: [who, where, what happens, the twist]
Write the script with the rules in references/STYLE.md, check it with the script command, then silent, plan,
show me 3 stills, render until DONE, join, check, and give me final.mp4.
```

## Tips

- Keep the first one short (15-20 s) and use the sets already in the kit: a new set costs much more of your limit.
- If it stops before DONE, type `continue` (in the same chat). If you hit the free plan limit, wait for the reset
  and type `continue`.
- Change anything after the stills: say what, where and how ("make the cat bigger, next to the samovar").
