# گزارش ساخت V23.0.203 — منشأ پیش‌بینی تا نتیجه

تاریخ: 2026-11-21
مبنای کد: ZIP واقعی V23.0.202 با SHA-256 برابر 29c4dbcee2a9c7a89a39b0488948067f46f40e414b263404222628cae9396078.

## تغییر
- جدول موجود brain_forecasts اکنون producer، source_context_json و prediction_direction را نگه می‌دارد.
- رکوردهای تاریخی با producer پیش‌فرض historical_market_brain مهاجرت می‌کنند؛ دادهٔ قدیمی حذف یا بازنویسی نمی‌شود.
- forecast_provenance یک مسیر ممیزی فقط‌خواندنی برای پیوند prediction_id با horizon، pattern_signature، market_regime، direction، observed_return و outcome می‌دهد.
- Scout این خروجی را در market_brain_forecast_provenance ارائه می‌کند.
- این مسیر فقط برای Historical Market Brain اثبات شده؛ تعمیم آن به همهٔ مغزها در این نسخه ادعا نمی‌شود.

## آزمون‌ها
- تست‌های متمرکز provenance، feedback، directional signal feedback، Knowledge Bus، AutoPilot و UI: 57 passed.
- py_compile برای backend/market_brain.py، backend/scout.py، backend/api.py و main.py موفق.
- full suite در این مرحله اجرا نشد؛ full-suite نتیجه‌ای ادعا نمی‌شود.
- Patch dry-run روی V202 تمیز موفق؛ 18 فایل بررسی شد.
- ZIP integrity موفق؛ 1,124 فایل؛ Manifest دارای 1,124 ورودی.

## ایمنی
- فقط ممیزی/ردیابی read-only؛ بدون تغییر score، ranking، confidence، model weights، risk یا execution.
- PAPER ONLY؛ هیچ معاملهٔ زنده‌ای فعال نشده است.

## Artifact checksums
- ZIP SHA-256: a9c5d1ed5295e59fc03a77c758a9f458eb000bc0e344db61728d69950d04c418
- Patch SHA-256: ac972278a377f7d7eedc619610f45bfb80fb77e2d333600bb1feb0f8d718c51b
