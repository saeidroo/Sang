# ممیزی اولیهٔ Baseline نسخهٔ 152 / بستهٔ V153 UI Stage 2

## دامنه و محدودیت
این گزارش بر پایهٔ بررسی مستقیم سورس داخل فایل ZIP با نام `TradingSignalAIPro_V23.0.153_UI_STAGE2(2).zip` است. پوشهٔ ریشهٔ داخل ZIP با نام `TradingSignalAIPro_V23.0.152_AUDIT` ارائه شده است. این اختلاف نام باید در تطبیق منشأ نسخه بررسی شود؛ نام ZIP به‌تنهایی نسخهٔ واقعی کد اجرایی را اثبات نمی‌کند.

هیچ‌یک از سه فایل دیتابیس زیر داخل ZIP پیدا نشد:
- `storm_learning.sqlite3`
- `market_brain_feedback.sqlite3`
- `candles.sqlite3`

نبود فایل در ZIP، نبود آن روی رایانه یا سرور کاربر را ثابت نمی‌کند. تا زمان دریافت و بررسی نسخهٔ واقعی دیتابیس‌ها، هیچ شمارش رکورد، سلامت داده یا Observed Baseline قابل ادعا نیست.

## یافته‌های سورس: زنجیره‌های ثبت و نتیجه

### 1) Scout / Storm Learning
ماژول: `backend/storm_learning.py`

مسیر پیش‌فرض دیتابیس:
`<project-root>/data/storm_learning.sqlite3`

متغیر محیطی قابل تنظیم:
`TEKAR_STORM_LEARNING_DB`

جداولی که کد ایجاد می‌کند:
- `scout_sightings`: نماد، زمان مشاهده، قیمت، امتیاز، فاز، جهت، وضعیت تأیید، الگو و رژیم بازار.
- `scout_price_observations`: قیمت‌های مشاهده‌شده با نماد و زمان.
- `scout_outcomes`: نتیجهٔ هر مشاهده در افق‌های 1h، 4h، 24h، 3d و 7d.
- `scout_pre_pump_events` و `scout_pre_pump_outcomes`: رخدادهای مستقل پیش از حرکت و نتیجه‌های افقی آن‌ها.
- `scout_learning_meta`: نشانگر مهاجرت برچسب‌های جهت‌دار.

در `backend/scout.py`، مسیر اسکن به `storm_learning.record_scan(...)` و سپس `storm_learning.annotate(...)` متصل است. نتیجه‌ها با قیمت‌های بعدی مشاهده‌شده resolve می‌شوند؛ در نبود مشاهده، وضعیت missing/pending حفظ می‌شود.

محدودیت ردیابی: در schema اصلی sighting/outcome دیده‌شده، شناسهٔ نسخهٔ مدل یا شناسهٔ یکتای نسخهٔ پیش‌بینی وجود ندارد. بنابراین زنجیرهٔ «این پیش‌بینی با این نسخهٔ مدل» به شکل کامل اثبات نشده است.

### 2) Historical Brain
ماژول: `backend/market_brain.py`

مسیر آرشیو کندل:
`~/.trading_ai_models/history/candles.sqlite3`

قابل تنظیم با:
`TRADING_AI_HISTORY_DB`

مسیر پیش‌فرض feedback:
`market_brain_feedback.sqlite3` در کنار مسیر آرشیو کندل؛ قابل تنظیم با `TRADING_AI_BRAIN_FEEDBACK_DB`.

تابع `record_feedback` جدول `brain_forecasts` را ایجاد/استفاده می‌کند. رکورد شامل symbol، horizon، created_ts، due_ts، start_price، predicted_up/down، observed_ts، observed_return، outcome، pattern_signature و market_regime است. Forecastهای واجد شرایط ثبت می‌شوند و پس از موعد با قیمت‌های مشاهده‌شده ارزیابی می‌شوند. نتیجه‌های بدون مشاهده به `missing_observation` تبدیل می‌شوند.

همچنین جدول `directional_signal_feedback` برای بازخورد مستقل سیگنال‌های جهت‌دار Scout وجود دارد و مسیر فراخوانی آن در `backend/scout.py` دیده شد.

محدودیت ردیابی: در schema مشاهده‌شدهٔ `brain_forecasts` نیز فیلد صریح model_version یا model_build_id وجود ندارد. وجود pattern_signature و market_regime جایگزین شناسهٔ نسخهٔ مدل نیست.

### 3) Paper Execution
ماژول: `backend/paper_live.py`

مسیر پیش‌فرض:
`~/.trading_ai_models/paper_live.sqlite3`

قابل تنظیم با:
`TRADING_AI_PAPER_LIVE_DB`

جداول مرتبط:
- `paper_live_trades`: دفتر معاملات شبیه‌سازی‌شده.
- `paper_learning_events`: نتیجهٔ معاملهٔ بسته و تطبیق‌یافته؛ trade_id کلید اصلی است و context_json زمینهٔ ورود را نگه می‌دارد.
- `paper_learning_profiles`: پروفایل‌های تجمیعی که از رویدادها دوباره ساخته می‌شوند.
- `paper_live_meta` و `paper_equity_history`.

تابع `_record_learning_event` فقط پس از بسته‌شدن و تطبیق کامل معامله رویداد یادگیری را ثبت می‌کند؛ برای معاملات آتی با جریان funding ناقص، ثبت یادگیری متوقف می‌شود. export و replay زمانی نیز در کد وجود دارد.

محدودیت ردیابی: در schema مشاهده‌شدهٔ `paper_learning_events` فیلد صریح prediction_id یا model_version وجود ندارد. باید بررسی شود که context_json در عمل چه شناسه‌هایی را نگه می‌دارد؛ تا آن زمان پیوند دقیق معامله به پیش‌بینی و نسخهٔ مدل تأیید نشده است.

## پاسخ فعلی به سؤال Prediction → Outcome
- **در سطح کد:** مسیرهای ثبت و ارزیابی نتیجه برای Scout، Historical Brain و Paper وجود دارند.
- **در سطح دادهٔ واقعی:** هنوز تأیید نشده؛ فایل‌های SQLite در بسته موجود نیستند و دیتابیس‌های محیط اجرا بررسی نشده‌اند.
- **در سطح انتساب به نسخهٔ مدل:** schemaهای بررسی‌شده فیلد صریح model_version/model_build_id ندارند؛ بنابراین زنجیرهٔ کامل «پیش‌بینی مشخص ← نسخهٔ مدل مشخص ← نتیجهٔ واقعی» هنوز اثبات نشده است.

## کارهای بعدی ممیزی
1. از محیط اجرای واقعی، مسیر مؤثر هر دیتابیس را از متغیرهای محیطی و تنظیمات runtime مشخص کنیم.
2. بدون تغییر دیتابیس اصلی، نسخهٔ read-only/کپی امن تهیه کنیم.
3. برای هر DB: وجود، اندازه، زمان آخرین تغییر، integrity check، جدول‌ها، تعداد رکوردها، بازهٔ زمانی، تعداد pending/resolved/missing و تکراری‌ها را گزارش کنیم.
4. پیوندها را با شناسه‌های واقعی بررسی کنیم: Scout sighting_id، Brain forecast id، Paper trade_id و context_json.
5. وجود شناسهٔ نسخهٔ مدل، زمان تولید، افق، جهت، قیمت مبنا و outcome را جداگانه ارزیابی کنیم.
6. Observed Baseline را فقط از زنجیره‌های واقعی و قابل بازیابی بسازیم؛ دادهٔ replay/backtest جداگانه با برچسب Reconstructed Baseline بماند.

## هشدار ارزیابی
**وجود تست موفق، اثبات عملکرد موفق نیست.** تست موفق فقط نشان می‌دهد رفتار مشخص‌شده در همان تست اجرا شده است؛ به‌تنهایی Accuracy، کیفیت پیش‌بینی، سودآوری یا برتری نسبت به baseline را اثبات نمی‌کند.

تا تکمیل ممیزی داده و ساخت baseline:
- ML/RL جدید ساخته یا بازآموزی نشود.
- وزن‌ها، thresholdها، ranking، voting و entry filter تغییر نکنند.
- حافظهٔ یادگیری جدید به‌عنوان جایگزین دادهٔ تاریخی اضافه نشود.
- PAPER ONLY حفظ شود.
