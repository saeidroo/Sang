# V156 — یکپارچه‌سازی وضعیت زنده پردازشگرها

## هدف
تفکیک «پردازشگر واقعاً زنده است؟» از «آخرین شاهد/داده تازه چه زمانی ثبت شده؟» و نمایش وضعیت مستقل برای سه چرخه:
- Historical Market Brain
- History Backfill
- Storm Scout

Storm Learning پردازشگر مستقل نیست؛ در چرخه Scout اجرا می‌شود و نباید به‌عنوان worker جداگانه زنده گزارش شود.

## تغییرات
- `backend/market_brain.py`: ثبت heartbeat، زمان شروع/پایان worker، محاسبه سن heartbeat و وضعیت `active / stale / stopped / not_started` بر اساس thread واقعی.
- `backend/historical.py`: نگهداری reference واقعی thread دریافت تاریخچه، heartbeat در پیشرفت صفحات/نمادها، و وضعیت زنده/کهنه/متوقف.
- `backend/scout.py`: heartbeat حلقه Scout و زمان شروع/پایان؛ تفکیک `scanning` از `active` (حلقه بیدار ولی در فاصله انتظار).
- `tests/test_v23_0_156_processor_heartbeat.py`: آزمون وضعیت زنده و stale برای هر سه پردازشگر.

## اعمال پچ
این patch افزایشی است و باید پس از پچ‌های قبلی V156 به‌ترتیب زیر اعمال شود:
1. `V156_CROSS_TIMEFRAME_BRAIN_BUS.patch`
2. `V156_PROCESSOR_HEARTBEAT_HEALTH.patch`
3. `V156_KNOWLEDGE_EVIDENCE_FRESHNESS.patch`
4. `V156_PROCESSOR_HEALTH_UNIFICATION.patch`

از ریشه پروژه:
`patch -p1 < V156_PROCESSOR_HEALTH_UNIFICATION.patch`

## اعتبارسنجی محلی
- `python -m compileall -q backend main.py` — موفق
- `node --check frontend/app.js` — موفق
- تست‌های V154/V155/V156 به‌علاوه تست جدید — **26 passed**
- dry-run patch روی V156 پس از اعمال سه patch قبلی — موفق

## محدودیت‌ها
- اجرای زنده با دیتابیس و شبکه واقعی کاربر انجام نشده است.
- heartbeat مربوط به Historical Brain هنگام مراحل سنگین، با پیشرفت مراحل/نمادها به‌روزرسانی می‌شود؛ یک عملیات داخلی بسیار طولانی بدون پیشرفت می‌تواند به‌صورت محافظه‌کارانه `stale` شود.
- Scout heartbeat در چرخه انتظار هر ثانیه تازه می‌شود؛ هنگام اسکن، آخرین heartbeat اسکن حفظ می‌شود. آستانه stale برابر دو برابر فاصله اسکن یا حداقل ۱۸۰ ثانیه است.
- هیچ سفارش واقعی، سیگنال معاملاتی یا پارامتر ریسک تغییر نمی‌کند. PAPER ONLY.
- این شاخه فقط patch و گزارش نگه می‌دارد؛ سورس پروژه به‌صورت مستقیم جایگزین یا merge نشده است.
