# گزارش ساخت V23.0.201 — استانداردسازی تعارض شواهد بین مغزها

تاریخ: 2026-11-21
مبنای کد: بستهٔ V23.0.200، استخراج‌شده از سورس واقعی پروژه.

## تغییرات
- تابع مشترک `summarize_directional_evidence` در Knowledge Bus موجود اضافه شد.
- Central Brain، Historical Market Brain، AutoPilot و Scout از خلاصه‌ساز یکسان استفاده می‌کنند.
- packet تکراری از یک producer به رأی مستقل تبدیل نمی‌شود.
- تعارض درون یک producer از تعارض بین producerها جدا گزارش می‌شود.
- Neutral و Unknown رأی جهت‌دار نیستند.
- Central Brain و AutoPilot در صورت تعارض داخلی یک producer نیز abstain می‌کنند.
- Scout و Historical Market Brain فقط context ممیزی دریافت می‌کنند.
- هیچ تغییری در score، ranking، confidence، model weights، risk scaling یا order execution اعمال نشده است.

## آزمون‌ها
- مجموعهٔ هدفمند و regression مربوط به Knowledge Bus/UI/version: 52 passed.
- مجموعهٔ اضافی مغز و بازار: 64 passed و 1 deselected.
- یک تست health API به علت نبود dependency محیطی Flask اجرا نشد؛ خطای گزارش‌شده `ModuleNotFoundError: flask` است.
- py_compile برای فایل‌های تغییرکرده موفق.
- Patch dry-run روی سورس V200 موفق.
- ZIP سالم؛ 1,083 فایل داخل بسته.

## Artifact checksums
- ZIP SHA-256: `2fc130987dd45a22a039cbfab7a02132874d28285eedea380e721a923b6929d3`
- Patch SHA-256: `fe85fd362571a0322a4aceedf99943047bc0d441b13df6b6cdd46f1c2787fed5`

## محدودیت
این تست‌ها کد و مسیرهای آزموده‌شده را بررسی می‌کنند؛ runtime روی ویندوز کاربر، دیتابیس عملیاتی، feed زنده یا سودآوری را اثبات نمی‌کنند. اجرای کامل suite با dependencies نصب‌شده همچنان لازم است. PAPER ONLY؛ معاملهٔ زنده فعال نشده است.
