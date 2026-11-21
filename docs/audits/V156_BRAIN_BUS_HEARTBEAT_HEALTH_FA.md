# V156 — Brain Bus, Processor Heartbeat & Evidence Freshness

## تغییرات
- اشتراک شواهد بین تایم‌فریم‌ها با opt-in صریح در Knowledge Bus.
- Scout، Autopilot و Price Action شواهد تایم‌فریم‌های دیگر را فقط به‌صورت زمینه مشورتی می‌خوانند؛ جهت سیگنال، امتیاز، ریسک و اندازه موقعیت تغییر نمی‌کند.
- Price Action worker heartbeat، زمان شروع/پایان، زنده‌بودن thread و تشخیص heartbeat منقضی‌شده دارد.
- حالت‌های liveness: idle، active، stale، worker_exited_unexpectedly و finished؛ آستانه stale برابر ۱۲۰ ثانیه است.
- اصلاح معنای وضعیت Knowledge Bus: «شاهد تازه» دیگر به‌عنوان «مغز فعال/پردازشگر بیدار» معرفی نمی‌شود. کلیدهای قدیمی برای سازگاری حفظ شده‌اند و معنای آن‌ها صریحاً recent evidence است.
- Knowledge Bus به‌تنهایی وضعیت زنده‌بودن workerها را گزارش نمی‌کند؛ برای آن باید heartbeat مستقل هر پردازشگر ثبت شود.
- معاملات واقعی غیرفعال باقی می‌مانند.

## اعتبارسنجی روی آرشیو pristine V156 پس از اعمال متوالی سه patch
- ۲۳ تست نسخه‌های V154/V155/V156: موفق.
- python -m compileall -q backend main.py: موفق.
- node --check frontend/app.js: موفق.
- dry-run هر سه patch و apply متوالی: موفق.

## محدودیت‌ها
- این خروجی patch set روی شاخه مستقل است؛ source روی main اعمال یا merge نشده است.
- اتصال به آرشیو زنده کاربر و اجرای پردازشگرها روی داده واقعی از این محیط تأیید نشده است.
- قابلیت‌ها advisory-only و PAPER ONLY هستند؛ real_orders_enabled=false.
