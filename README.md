# حلقات الستيكمان | Stickman Episodes

مشروع فيديو قصير أصلي: **آخر قطعة خبز**.

- المدة: 72 ثانية (1:12)
- المقاس: عمودي 9:16، بدقة 720×1280
- الأسلوب: رسوم Stickman ثنائية الأبعاد مرسومة برمجياً
- الصوت: تعليق عربي مولّد محلياً عبر espeak-ng مع خلفية موسيقية أصلية بسيطة
- الناتج: `output/last_piece_of_bread.mp4`

## إنتاج الفيديو
كل Push إلى الفرع `main` يشغّل GitHub Actions تلقائياً. بعد انتهاء التشغيل، افتح تبويب **Actions** ثم افتح آخر تشغيل وحمّل Artifact باسم `stickman-episode-mp4`.

يمكن تشغيله محلياً بعد تثبيت Python 3 وFFmpeg وespeak-ng:

```bash
pip install -r requirements.txt
python render.py
```

> ملاحظة: الفيديو يُبنى داخل GitHub Actions كـ Artifact ZIP؛ لا يُحفظ ملف MP4 مباشرة في Git بسبب حجمه.
