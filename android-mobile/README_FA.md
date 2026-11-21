# TradingSignalAI Pro Mobile — Android

کلاینت Android برای گوشی و تبلت که رابط موجود پروژه را از سرور دریافت می‌کند. مغزها، مدل‌ها، حافظه، دیتابیس و موتور معاملاتی در Python روی میزبان باقی می‌مانند.

## ساخت APK
- Windows: اجرای `build-apk.bat`
- Linux/macOS: اجرای `./build-apk.sh`
- GitHub Actions: اجرای workflow با نام **Build TradingSignalAI Pro Android APK** و دریافت Artifact.
- نیازمندی ساخت محلی: JDK 17، Gradle 8.9 و Android SDK Platform 35.

## معماری و ایمنی
- WebView فقط رابط وب موجود را نمایش می‌دهد؛ منطق معاملاتی کپی یا بازنویسی نمی‌شود.
- آدرس سرور باید HTTPS باشد.
- رمز Basic Auth در SharedPreferences ذخیره نمی‌شود.
- گواهی TLS نامعتبر به‌صورت fail-closed رد می‌شود.
- Flask باید روی 127.0.0.1 بماند و فقط از Gateway احراز هویت‌شده Caddy قابل دسترسی باشد.
- این نسخه PAPER ONLY است و سفارش واقعی ارسال نمی‌کند.
- MT5 روی میزبان Windows اجرا می‌شود؛ موبایل فقط داشبورد/کنترل رابط سرور را ارائه می‌کند.
