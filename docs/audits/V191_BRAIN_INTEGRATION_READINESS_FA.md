# V191 — ممیزی آمادگی اتصال دانش مشترک به مغزهای TradingAI

تاریخ: 2026-11-21  
شاخه: `fix/v156-cross-timeframe-brain-bus`  
HEAD مبنا: `13ccf9e4ca7b307e4763d608eaa4844a887c064b`

## هدف ممیزی

بررسی اینکه دانش کتاب‌های Murphy، Nison، Grimes و دورهٔ Machine Learning for Trading در چه نقاطی از جریان فعلی مغزها قرار گرفته و آیا واقعاً پیش از تصمیم هر مغز در دسترس و قابل استفاده است یا خیر. این گزارش عمداً بین «patch موجود»، «تغییر ثبت‌شده در artifact نسخه»، «کد اعمال‌شده» و «رفتار runtime اثبات‌شده» تفاوت می‌گذارد.

## یافته‌های قطعی از مخزن

### 1. Knowledge Bus و تبادل بین مغزها

فایل `source/patches/V156_CROSS_TIMEFRAME_BRAIN_BUS.patch` مسیرهای زیر را هدف می‌گیرد:
- `backend/knowledge_bus.py`: امکان بازیابی شواهد تایم‌فریم‌های دیگر با `include_other_timeframes`.
- `backend/api.py`: افزودن شواهد همکاران به context تحلیل.
- `backend/autopilot.py`: افزودن شواهد مشترک به decision context.
- `backend/price_action_learning.py`: انتقال شواهد چندتایم‌فریمی به packet تحلیل Price Action.
- `backend/scout.py`: بازیابی شواهد سایر مغزها برای Scout.

این patch یک artifact در GitHub است؛ وجود آن به معنی اعمال‌شدن روی سورس اجرایی فعلی نیست.

### 2. مشورت پیش از تصمیم مغز مرکزی

گزارش V160 می‌گوید در artifact نسخهٔ V23.0.160، `backend/api.py` دانش همکاران را پیش از فراخوانی Central Brain بازیابی می‌کند و `backend/brain.py` تعارض را مستقل بررسی می‌کند. نتیجهٔ تعارض می‌تواند abstention/HOLD باشد، نه افزایش score، confidence یا risk.

اما همان گزارش تصریح می‌کند سورس کامل V23.0.160 در commit گیت‌هاب ثبت نشده و فقط گزارش وضعیت ثبت شده است.

### 3. زمینهٔ تاریخی و نتایج Paper

گزارش‌های V163 تا V165 تغییرات ادعاشده در artifactهای نسخه را شرح می‌دهند:
- V163: اشتراک زمینهٔ تاریخی موجود در packetهای تولیدکننده؛ Knowledge Bus فقط آخرین packet هر کلید را نگه می‌دارد و آرشیو نامحدود رویداد نیست.
- V164: انتشار خلاصهٔ خنثی نتایج Matured PAPER به‌عنوان evidence تاریخی؛ خارج‌کردن آن از محاسبات هم‌جهتی/تعارض.
- V165: انتقال برچسب‌های شکستِ از قبل ثبت‌شده مانند `opposite_move` و `no_follow_through`؛ بدون استنتاج علت از outcome خام.

این موارد نیز در این مخزن گزارش نسخه هستند، نه سورس کامل قابل build.

### 4. Curriculum کتاب‌ها

Patch `V156_BOOK_CURRICULUM_SHARED_BRAIN_V2.patch` فقط فایل `backend/price_action_learning.py` را هدف می‌گیرد. محتوای Murphy، Nison، Grimes و ML4T در یک فیلد آموزشی ساختاریافته قرار می‌گیرد و از طریق packet مربوط به Price Action قابل ارائه می‌شود.

بنابراین از روی این patch نمی‌توان نتیجه گرفت تمام مغزها کل curriculum را دریافت می‌کنند یا هر مغز پیش از تصمیم خود آن را بازیابی می‌کند. برای این ادعا باید مصرف‌کنندگان واقعی و مسیرهای pre-decision هر مغز جداگانه در سورس نهایی بررسی شوند.

### 5. محافظ‌های موجود

- `V156_KNOWLEDGE_TIMESTAMP_GUARD.patch`: رد timestamp بیش از ۵ دقیقه در آینده و clamp کردن skew کوچک.
- `V156_BRAIN_CONFLICT_ABSTENTION_TEST.patch`: حفظ شواهد متناقض یک منبع، اما abstain از رأی جهت‌دار آن منبع.
- قواعد معماری V153: دریافت evidence با مصرف در scoring یکی نیست؛ unknown/missing/stale/invalid نباید به صفر یا neutral تبدیل شوند.
- PAPER ONLY و Shadow Firewall همچنان الزامی‌اند.

## وضعیت منبع اجرایی و مانع فعلی

در شاخهٔ بررسی‌شده فقط ZIP نسخهٔ `V23.0.153_UI_STAGE2` وجود دارد؛ README و Implementation Status نیز می‌گویند سورس کامل نسخه‌های بعدی در مسیرهای اجرایی GitHub sync نشده است. جست‌وجوی فایل‌های در دسترس Library برای نام دقیق `TradingSignalAIPro_V23.0.165_CROSS_BRAIN_FAILURE_DIAGNOSIS.zip` نتیجه‌ای نداد. بنابراین این ممیزی به فایل ZIP نسخهٔ 165 دسترسی اجرایی پیدا نکرد و هیچ فایل backend از آن استخراج یا ویرایش نشد.

## تصمیم فنی

اتصال کامل curriculum به همهٔ مغزها در این مرحله **اثبات نشده** است. به‌جای افزودن شاخه، مغز یا لایهٔ جدید، مسیر کم‌ریسک بعدی چنین است:

1. دریافت سورس واقعی V23.0.165 (یا نسخهٔ جدیدتر مورد استفاده) و ثبت SHA-256 و manifest.
2. اعمال patchهای موجود به‌صورت کنترل‌شده روی همان سورس، پس از تطبیق base revision و بررسی conflict؛ از اعمال کورکورانهٔ patch خودداری شود.
3. ترسیم فهرست producer/consumer برای مغزهای موجود و مشخص‌کردن نقطهٔ دقیق pre-decision هر کدام.
4. افزودن فقط فراخوانی مشترک/بازیابی curriculum به مصرف‌کنندگان موجود، بدون تغییر scoring، ranking، voting، confidence، risk یا order behavior.
5. تست‌های قراردادی: تبادل دوطرفه، منع self-consumption، freshness/timestamp، تعارض و abstention، تفکیک timeframe/market، و جلوگیری از duplicate evidence.
6. آزمون Shadow parity: خروجی تصمیم با Knowledge Bus خاموش و روشن باید یکسان بماند و `decision_scoring_consumed = 0`.

## نتیجه

- GitHub patches audited: بله.
- وجود مسیرهای تبادل دانش در patchها: بله.
- اتصال واقعی curriculum به تمام مغزهای نسخهٔ اجرایی: اثبات‌نشده.
- اجرای runtime یا build نسخهٔ 165: انجام‌نشده؛ ZIP در دسترس این بررسی نبود.
- تغییر score/weights/risk/trading: خیر.
- Live trading: غیرفعال؛ PAPER ONLY.

این گزارش وضعیت واقعی را ثبت می‌کند و ادعای پیاده‌سازی یا آموزش runtime ایجاد نمی‌کند.
