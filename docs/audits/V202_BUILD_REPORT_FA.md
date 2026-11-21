# گزارش ساخت V23.0.202 — تداوم انتشار حلقه یادگیری

تاریخ: 2026-11-21
مبنای کد: بستهٔ واقعی V23.0.201؛ ZIP ورودی با SHA-256 برابر 2fc130987dd45a22a039cbfab7a02132874d28285eedea380e721a923b6929d3 اعتبارسنجی شد.

## یافتهٔ ممیزی
- بستن دستی موقعیت PAPER پروفایل بسته‌شده را منتشر می‌کرد.
- خروج خودکار در مسیر تازه‌سازی موقعیت (_refresh_open_positions که از get_state فراخوانی می‌شود) رویداد یادگیری را ثبت و پروفایل محلی را بازسازی می‌کرد، اما انتشار Knowledge Bus در همان چرخه تضمین نبود.
- خروج ناشی از replay کندل (replay_position_candles) نیز ledger و پروفایل را به‌روزرسانی می‌کرد، اما انتشار پس از commit را انجام نمی‌داد.
- مسیر Funding Sync برای Perp از قبل پس از reconciliation انتشار انجام می‌داد؛ رویدادهای Perp تا SYNCED شدن وارد یادگیری نمی‌شوند.

## تغییرات
- get_state بسته‌شدن‌های تازهٔ موقعیت را از snapshot اولیه تشخیص می‌دهد و پس از اتمام refresh، پروفایل‌های یادگیری را به Knowledge Bus موجود منتشر می‌کند. وضعیت انتشار در پاسخ با کلید learning_publication قابل مشاهده است.
- replay_position_candles در صورت خروج، پس از commit تراکنش SQLite پروفایل را منتشر می‌کند و نتیجهٔ انتشار را برمی‌گرداند.
- هیچ جدول، brain، سرویس یا شاخهٔ تصمیم جدیدی اضافه نشده است.
- هیچ تغییری در signal، confidence، score، model weights یا ریسک انجام نشده است؛ دادهٔ peer همچنان advisory-only باقی می‌ماند.

## آزمون‌ها
- مجموعهٔ متمرکز حلقه یادگیری، replay، مدیریت موقعیت، AutoPilot، Knowledge Bus و قرارداد UI/version: 84 passed، 1 skipped.
- py_compile برای فایل‌های Python تغییرکرده: موفق.
- Patch dry-run روی سورس تمیز V201: موفق.
- ZIP integrity: موفق؛ 1,085 فایل؛ Manifest دارای 1,085 ورودی.
- full suite اجرا شد اما collection برای 10 ماژول API به دلیل نبود Flask در محیط متوقف شد (ModuleNotFoundError: flask)؛ بنابراین full suite سبز نیست.

## Artifact checksums
- ZIP SHA-256: 29c4dbcee2a9c7a89a39b0488948067f46f40e414b263404222628cae9396078
- Patch SHA-256: 45b97e9260fb9d74a22945c5f2b5ecf126945b2f9b7e1be3984ef3450af20bb6

## ایمنی و محدودیت
- PAPER ONLY؛ سفارش واقعی غیرفعال است.
- Perp تا تکمیل Funding Sync از رویداد یادگیری کنار گذاشته می‌شود؛ انتشار پروفایل قبلی به‌تنهایی به معنای ثبت outcome جدید نیست.
- تست واحد اثبات runtime روی سیستم کاربر، وجود دادهٔ کافی یا سودآوری نیست.
