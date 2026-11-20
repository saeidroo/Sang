# TradingSignalAIPro — دیده‌بان طوفان

**نسخهٔ اجرایی هدف: V23.0.153 — UI Stage 2**

این مخزن محل بازسازی کنترل‌شده و ادامهٔ توسعهٔ TradingSignalAIPro است. شاخهٔ بازسازی فعلی:
**v23.0.153-rebuild**

> توجه: سورس ZIP کامل V23.0.153 هنوز به این مخزن منتقل نشده است. فایل‌های فعلی این شاخه، معماری و نقشهٔ اجرا را تثبیت می‌کنند؛ آن‌ها به معنی انتقال یا اتصال کد اجرایی نیستند.

## اسناد اصلی
- [معماری هدف V153](docs/ARCHITECTURE_V153.md)
- [قانون صفر، Baseline و حاکمیت تغییر مدل](docs/GOVERNANCE_AND_BASELINES.md)
- [نقشهٔ اجرایی مرحله‌ای](docs/ROADMAP_V153.md)
- [وضعیت واقعی پیاده‌سازی](docs/IMPLEMENTATION_STATUS.md)

## اصول غیرقابل‌مذاکره
- پامپ و دامپ هر دو جهت معتبر کشف فرصت‌اند.
- unknown / missing / stale / invalid نباید به صفر یا خنثی تبدیل شوند.
- دریافت Evidence با مصرف آن در scoring یکی نیست.
- در Shadow Mode هیچ Evidence جدیدی حق تغییر score، ranking، رأی مغز مرکزی، فیلتر ورود یا Paper Trading را ندارد.
- هیچ نتیجه‌ای مستقیماً وزن‌ها یا رفتار مدل را تغییر نمی‌دهد.
- تغییر مدل فقط از مسیر Registry → Evaluation → Comparison → Approval → Deployment.
- اجرای سفارش فقط Paper است؛ Live Trading خارج از محدوده است.
- هیچ نسخه‌ای بدون شواهد قابل تکرار بهتر از baseline اعلام نمی‌شود.

## نسخه‌ها
- هدف اجرایی: V23.0.153 UI Stage 2.
- V23.0.152: مرجع تاریخی برای مقایسه و ممیزی، نه هدف فعلی.
- V153.2.1 Evidence/Event Contract Pack: سند قرارداد؛ اتصال اجرایی آن هنوز اثبات نشده است.

## شروع کار
1. ZIP کامل V23.0.153 را به مخزن منتقل کنید.
2. SHA-256 و manifest فایل‌ها را ثبت کنید.
3. تست‌های پایه را در محیط تمیز اجرا کنید.
4. سپس ممیزی و اتصال Evidence/Event Ledger را در Shadow Mode آغاز کنید.

وضعیت دقیق هر مرحله در [Implementation Status](docs/IMPLEMENTATION_STATUS.md) ثبت می‌شود.
