# گزارش ساخت V23.0.200 — بازیابی مستقل تجربهٔ معاملات بسته‌شدهٔ PAPER

تاریخ: 2026-11-21

## هدف
در V199 مصرف‌کننده‌ها ابتدا تعداد محدودی از شواهد عمومی Knowledge Bus را می‌خواندند و سپس تجربهٔ بسته‌شدهٔ PAPER را از همان فهرست استخراج می‌کردند. اگر packetهای جدیدتر peer سقف عمومی را پر می‌کردند، پروفایل PAPER ممکن بود از context حذف شود.

## تغییر
- تابع `recall_closed_paper_profiles` در `backend/knowledge_bus.py` افزوده شد.
- خواندن از جدول موجود `brain_knowledge` و با فیلتر symbol، market، producer معتبر و دو نوع پروفایل LONG/SHORT انجام می‌شود.
- محدودیت تازگی، تایم‌فریم اختیاری و سقف تعداد رکورد حفظ شده است.
- `closed_paper_experience_for_scope` داده را از اعتبارسنجی قبلی عبور می‌دهد؛ schema، producer، side و neutral/unknown بودن direction کنترل می‌شوند.
- مسیرهای Central Brain، Historical Market Brain، Scout، Price Action و AutoPilot از query مستقل استفاده می‌کنند.
- هیچ جدول، مغز، سرویس یا شاخهٔ معماری جدیدی ساخته نشد.

## محدوده اثر و ایمنی
- تجربهٔ PAPER همچنان NEUTRAL و advisory-only است.
- score، ranking، confidence، model weights، risk limits، signal gates و order execution تغییر نکرده‌اند.
- PAPER ONLY؛ معاملهٔ زنده فعال نشده است.

## آزمون‌ها
- Regression جدید: ۲۴ packet تازه‌تر peer، سقف عمومی ۸ و بازیابی مستقل پروفایل PAPER.
- جداسازی بازار و فیلتر تازگی داده.
- تست‌های Knowledge Bus و brain peer context.
- نتیجه: 46 passed.
- py_compile برای 7 فایل Python موفق.
- Patch dry-run روی مبنای V199 موفق.
- ZIP سالم؛ 1,080 فایل داخل بسته.

## SHA-256
- ZIP: `02ac075a602e11d62944ffe0103bbb04fd1fb562b2f1c038151e5e27a8e068eb`
- Patch: `8fdfe0786ac8c2b39ff40a20d4cd7b214378a6f1f11ea6a765caab27ab54190e`

## محدودیت
این نتایج تست کد و query در محیط آزمون‌اند؛ runtime در نصب ویندوز کاربر، دیتابیس عملیاتی، feed زنده یا بهبود سودآوری را اثبات نمی‌کنند. اجرای کامل test suite هنوز لازم است.
