# گزارش ساخت V23.0.205 — ثبت مشورت واقعی مغزها

تاریخ: 2026-11-21
مبنای کد: ZIP واقعی V23.0.204_SHARED_MATURED_OUTCOMES؛ SHA-256 ورودی: da8dad2ff76b21d6b695ef24649136a91fda61faa4d0c75307e759084a250849

## تغییرات
- recall_matured_paper_outcomes اکنون شناسهٔ packet منبع را هم برمی‌گرداند.
- تابع record_matured_outcome_consultation در همان جدول موجود brain_knowledge رسید مشورت را ثبت می‌کند؛ جدول یا سرویس جدیدی ایجاد نشده.
- Historical Market Brain، AutoPilot و Scout هنگام دریافت تجربهٔ بالغ‌شدهٔ معتبر رسید مصرف ثبت می‌کنند.
- matured_outcome_usage_summary تعداد دفعات مراجعه و packetهای منبع یکتا را به تفکیک مصرف‌کننده گزارش می‌کند.
- receiptها neutral و advisory-only هستند و از query تجربه‌های بالغ‌شده جدا می‌مانند.
- یک اصلاح سازگاری نیز انجام شد: publisher خروجی matured outcomes هر دو کلید قدیمی و کلید سخت‌گیرانهٔ may_change_signal_score_risk_or_execution=false را منتشر می‌کند تا recall آن‌ها را رد نکند.

## آزمون‌ها
- مجموعهٔ اصلی V205 و regressionهای مرتبط: 52 passed.
- مجموعهٔ تکمیلی feedback، market peer context، Knowledge Bus، forecast و UI contracts: 63 passed.
- py_compile برای knowledge_bus.py، market_brain.py، autopilot.py، scout.py، api.py و main.py موفق.
- patch dry-run روی سورس تمیز V204 موفق.
- ZIP integrity موفق؛ 1,115 مسیر شامل فایل و پوشه؛ Manifest شامل 1,098 فایل.
- Full suite اجرا نشده است.

## محدودیت و ایمنی
- این نسخه «مواجهه/خواندن context» را اندازه می‌گیرد، نه استفادهٔ شناختی قطعی، اثر علّی بر تصمیم یا بهبود دقت پیش‌بینی.
- receiptها آخرین وضعیت را در کلید یکتای موجود برای هر نماد/بازار/تایم‌فریم/مصرف‌کننده نگه می‌دارند؛ تعداد مراجعه تجمعی است و شناسهٔ حداکثر 50 منبع یکتا حفظ می‌شود.
- هیچ تغییر در score، confidence، model weights، risk یا execution انجام نشده است.
- PAPER ONLY؛ معاملهٔ زنده فعال نشده است.

## Checksums
- ZIP SHA-256: 0539d92ed20c35d67e32ef77260e16983b611a79f9d5c8b4d57749291c23de93
- Patch SHA-256: 2bfb7cb55c5a6c0d60c530b3721ab2b605fd0d52a8c096a6efc7a8824b6ecbfa
