# وضعیت واقعی پیاده‌سازی

آخرین بازبینی: 2026-11-20

## مخزن و سورس
- مخزن: saeidroo/Sang
- شاخهٔ اصلی: main (دست‌نخورده)
- شاخهٔ کاری: v23.0.153-rebuild
- ZIP سورس در GitHub ثبت شده است: `source/TradingSignalAIPro_V23.0.153_UI_STAGE2.zip`
- همان سورس به‌صورت فایل گفتگو نیز بررسی شد: `TradingSignalAIPro_V23.0.153_UI_STAGE2(2).zip`
- پوشهٔ ریشهٔ داخل ZIP نام `TradingSignalAIPro_V23.0.152_AUDIT` دارد؛ اختلاف نام بسته و پوشه باید در تطبیق منشأ نسخه حل شود.

## ممیزی سورس انجام‌شده
- مسیرهای ذخیره/ارزیابی Scout در `backend/storm_learning.py` شناسایی شدند.
- مسیر Forecast/Outcome در `backend/market_brain.py` شناسایی شد.
- مسیر ثبت معاملات بسته‌شده و رویدادهای یادگیری Paper در `backend/paper_live.py` شناسایی شد.
- مسیر فراخوانی Scout به ماژول‌های Storm Learning و Market Brain در `backend/scout.py` مشاهده شد.
- دیتابیس‌های `storm_learning.sqlite3`، `market_brain_feedback.sqlite3` و `candles.sqlite3` داخل ZIP وجود نداشتند.
- در schemaهای بررسی‌شده فیلد صریح model_version/model_build_id برای انتساب کامل prediction به نسخهٔ مدل دیده نشد.
- بنابراین وجود زنجیره‌های کدی تأیید شده، اما وجود و سلامت داده‌های واقعی و انتساب کامل به نسخهٔ مدل هنوز تأیید نشده است.

گزارش جزئیات: [V152_BASELINE_AUDIT.md](V152_BASELINE_AUDIT.md)

## اسناد ثبت‌شده
- `docs/ARCHITECTURE_V153.md`
- `docs/GOVERNANCE_AND_BASELINES.md`
- `docs/ROADMAP_V153.md`
- `docs/V152_BASELINE_AUDIT.md`

## موارد باز
- تعیین مسیر مؤثر دیتابیس‌ها در محیط واقعی اجرا.
- تهیهٔ نسخهٔ read-only یا کپی امن از دیتابیس‌های واقعی.
- بررسی integrity، جدول‌ها، تعداد رکوردها، بازهٔ زمانی، pending/resolved/missing و امکان بازیابی.
- بازسازی زنجیرهٔ Prediction → Outcome و بررسی پیوند model version.
- ساخت Observed Baseline فقط در صورت وجود دادهٔ عملیاتی معتبر.
- تطبیق اختلاف نام نسخهٔ ZIP و پوشهٔ داخلی.
- بررسی اتصال اجرایی Evidence Adapter، Event Ledger و Decision Context؛ این موارد هنوز نباید متصل فرض شوند.

## قانون گزارش
«طراحی‌شده»، «کدنویسی‌شده»، «تست‌شده»، «متصل‌شده» و «دارای دادهٔ عملیاتی معتبر» وضعیت‌های جداگانه‌اند.
**وجود تست موفق، اثبات عملکرد موفق نیست.**
تا تکمیل ممیزی داده، تغییر ML/RL، وزن‌ها، thresholdها، ranking، voting یا منطق معاملاتی انجام نمی‌شود. PAPER ONLY.
