# TradingSignalAIPro

نسخهٔ مبنای بررسی‌شده: **V23.0.152 — Stage 6**

> این مخزن هنوز شامل ZIP کامل موتور Python نیست. سورس کامل موتور V23.0.227 در بستهٔ تحویلی محلی نگهداری می‌شود؛ این شاخه، کلاینت Android و گردش‌کار ساخت APK را جداگانه ثبت می‌کند.

## کلاینت Android — V23.0.227

- سورس Android Studio در `android-mobile/` قرار دارد.
- برنامه برای گوشی و تبلت طراحی شده و رابط وب موجود را از طریق WebView نمایش می‌دهد.
- مغزها، مدل‌ها، حافظه و موتور معاملاتی روی سرور Python باقی می‌مانند؛ در Android بازنویسی نمی‌شوند.
- اتصال موبایل فقط از HTTPS و Gateway احراز هویت‌شده انجام می‌شود؛ Flask باید روی loopback بماند.
- گردش‌کار ساخت APK: `.github/workflows/android-apk.yml`.
- پس از اجرای موفق GitHub Actions، فایل Debug APK از بخش Artifacts دریافت می‌شود.
- این کلاینت PAPER ONLY است و سفارش واقعی ارسال نمی‌کند.

## ساخت محلی

- JDK 17، Gradle 8.9 و Android SDK Platform 35 لازم است.
- Windows: `android-mobile/build-apk.bat`
- Linux/macOS: `android-mobile/build-apk.sh`
- راهنمای استقرار: `android-mobile/MOBILE_DEPLOYMENT_FA.md`

## اصول توسعه

- دادهٔ ناقص یا غیرقابل‌اعتماد نباید وارد یادگیری یا معامله شود.
- تغییرات معاملاتی ابتدا در تست و Paper ارزیابی می‌شوند.
- سفارش واقعی بدون مجوز صریح و ممیزی مستقل فعال نمی‌شود.
