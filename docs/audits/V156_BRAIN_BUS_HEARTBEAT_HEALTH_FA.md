# V156 — Processor Heartbeat & Cross-Timeframe Brain Bus

## تغییرات
- بازیابی و حفظ بسته اتصال بین‌تایم‌فریمی مغزها: recall بین تایم‌فریم‌ها فقط با گزینه صریح فعال می‌شود؛ تایم‌فریم منبع هر شاهد حفظ می‌شود.
- Scout، Autopilot و Price Action می‌توانند شواهد تایم‌فریم‌های دیگر را فقط در زمینه/یادداشت مشورتی بخوانند؛ منطق سیگنال، امتیاز، ریسک و اندازه موقعیت تغییر نمی‌کند.
- وضعیت پردازشگر اعتبارسنجی تاریخی Price Action اکنون heartbeat، زمان شروع/پایان، زنده‌بودن thread، سن heartbeat و حالت liveness را گزارش می‌کند.
- حالت‌های liveness: idle، active، stale، worker_exited_unexpectedly و finished.
- به‌روزرسانی وضعیت worker زیر RLock انجام می‌شود تا خواندن هم‌زمان snapshot ناقص نگیرد.
- آستانه stale برابر ۱۲۰ ثانیه است. زنده‌بودن thread به‌تنهایی به‌عنوان سلامت پردازشگر گزارش نمی‌شود.

## تست‌ها
- ۲۶ تست هدفمند: موفق.
- python -m compileall -q backend main.py: موفق.
- python -m py_compile برای ماژول‌های تغییرکرده: موفق.
- node --check frontend/app.js: موفق.
- زنجیره patch اتصال بین‌تایم‌فریمی سپس heartbeat روی آرشیو pristine V156: dry-run هر دو موفق؛ apply هر دو موفق؛ شش فایل نهایی دقیقاً با working tree آزمایش‌شده مطابقت دارند.

## محدودیت‌ها
- این خروجی یک patch set روی شاخه مستقل است؛ source روی main دست‌نخورده است.
- اتصال به آرشیو زنده کاربر و اجرای پردازشگر روی داده واقعی هنوز از این محیط قابل تأیید نیست.
- تمام قابلیت‌ها PAPER ONLY و advisory-only هستند؛ real_orders_enabled=false.
