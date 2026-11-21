# گزارش ساخت V23.0.204 — حافظهٔ مشترک تجربه‌های بالغ‌شده

تاریخ: 2026-11-21
مبنای کد: ZIP واقعی V23.0.203_FORECAST_PROVENANCE؛ SHA-256 ورودی مطابق گزارش V203.

## یافته و تغییر
- V203 منشأ پیش‌بینی Historical Market Brain را ثبت می‌کرد، و V202 خروجی‌های بسته‌شده را به Knowledge Bus می‌رساند؛ با این حال، خواندن aggregate موفقیت/شکست‌های Scout از سقف عمومی peer recall مستقل نبود.
- تابع recall_matured_paper_outcomes در Knowledge Bus موجود اضافه شد. این query اختصاصی است و packetهای جدیدتر دیگر نمی‌توانند این تجربه‌ها را از context حذف کنند.
- فقط knowledge_type=matured_paper_outcomes، جهت NEUTRAL و payloadهای دارای advisory_only=true و may_change_signal_score_risk_or_execution=false پذیرفته می‌شوند.
- Historical Market Brain و AutoPilot این context را دریافت می‌کنند؛ Scout نیز خروجی آن را برای نمادهای اسکن‌شده آشکار می‌کند.
- تجربه شامل aggregateهای success/failure و failure labelهای از پیش ثبت‌شده است؛ علت جدیدی از روی داده استنباط نمی‌شود.
- هیچ جدول، brain یا سرویس جدیدی اضافه نشده است.

## آزمون‌ها
- مجموعهٔ اصلی شامل تست جدید، feedback، Knowledge Bus، closed PAPER, UI و version contract: 55 passed.
- مجموعهٔ تکمیلی بازار، forecast provenance و feedback: 48 passed.
- py_compile برای knowledge_bus.py، market_brain.py، autopilot.py، scout.py، api.py و main.py موفق.
- Patch dry-run روی سورس تمیز V203 موفق؛ 14 فایل تغییرکرده/اضافه‌شده بررسی شد.
- ZIP integrity موفق؛ 1,090 فایل؛ Manifest دارای 1,090 ورودی.
- Full suite اجرا نشده است.

## ایمنی و محدودیت
- تجربه‌های مشترک صرفاً advisory/audit context هستند؛ هیچ تغییری در score، confidence، model weights، risk یا execution ایجاد نمی‌کنند.
- دریافت context به‌تنهایی اثبات نمی‌کند که تمام مغزها آن را در runtime مصرف می‌کنند؛ این نسخه مسیرهای مشخص‌شده را متصل می‌کند.
- PAPER ONLY؛ معاملهٔ زنده فعال نشده است.

## Artifact checksums
- ZIP SHA-256: da8dad2ff76b21d6b695ef24649136a91fda61faa4d0c75307e759084a250849
- Patch SHA-256: cb03a887e5342a1833c25f711e8b27fbd882c73400e597d36fce216cf5c452bb
