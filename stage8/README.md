# Stage 8 — Historical archive continuity patch

این پوشه یک **بستهٔ وصلهٔ مرحله هشتم** است، نه کپی کامل پروژه و نه نسخهٔ مستقل قابل اجرا.

## سازگاری

- محصول: TradingSignalAIPro **V23.0.152**
- پایهٔ دقیق وصله: آرشیو TradingSignalAIPro_V23.0.152_STAGE7_FIXED.zip
- SHA-256 پایه: 378634404763c9d33f756b0189b8d2dd363bcd97b52f6b5982f94f99f812b301
- خروجی کامل بررسی‌شدهٔ Stage 8: TradingSignalAIPro_V23.0.152_STAGE8_HISTORY_CONTINUITY_FIXED.zip
- SHA-256 خروجی: bd9a020c8870ca0b7099a88587d4c6474eb7c89c925e2e208bc0043d96ec30a3

## محتویات

- market_brain.patch: تغییرات مرحله هشتم روی backend/market_brain.py
- tests/test_v23_0_152_stage8_history_continuity.py: هفت تست جدید
- CHANGELOG_STAGE8_FA.md و AUDIT_STAGE8_REPORT_FA.md: شرح تغییرات و محدودهٔ ممیزی

## اعمال وصله

از ریشهٔ نسخهٔ پایهٔ Stage 7 اجرا شود:

```bash
patch -p1 --dry-run < stage8/market_brain.patch
patch -p1 < stage8/market_brain.patch
```

سپس تست‌های مرحله هشتم را در همان محیط پروژه اجرا کنید. این وصله به تنهایی جایگزین فایل‌ها و پایگاه‌داده‌های نسخهٔ پایه نیست.

## نتیجهٔ اعتبارسنجی ثبت‌شده

- compileall: موفق
- مجموعهٔ متمرکز مرتبط: **115 passed**
- تست‌های جدید Stage 8: **7 سناریو**
- دیتابیس واقعی کاربر و اتصال زندهٔ صرافی‌ها در این ممیزی بررسی نشده‌اند.

**ایمنی:** PAPER ONLY. منطق سفارش واقعی، امتیازها، وزن‌ها، آستانه‌ها و رتبه‌بندی سیگنال‌ها در Stage 8 تغییر نکرده‌اند.
