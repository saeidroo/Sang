# راه‌اندازی نسخه موبایل TradingSignalAI Pro

## معماری
- APK فقط رابط Android/WebView است؛ هیچ مغز، مدل، دیتابیس یا کلید صرافی داخل گوشی کپی نمی‌شود.
- موتور V23.0.227 روی Windows/Linux همان سرور/کامپیوتر اجرا می‌ماند.
- موبایل فقط از HTTPS و Gateway احراز هویت‌شده Caddy به سرور وصل می‌شود.
- Flask فعلی روی 127.0.0.1:8765 باقی می‌ماند؛ آن را روی 0.0.0.0 باز نکنید.
- نسخه فعلی PAPER ONLY است.

## آماده‌سازی سرور
1. پروژه اصلی را طبق README نصب کنید.
2. موتور را روی loopback اجرا کنید: `python main.py --browser --host 127.0.0.1 --port 8765`.
3. Caddy v2 را روی همان ماشین نصب و `deploy/Caddyfile.example` را به Caddyfile تبدیل کنید.
4. متغیرهای محیطی را تنظیم کنید:
   - TRADING_AI_DOMAIN: دامنه‌ای که DNS آن به IP سرور اشاره می‌کند.
   - TRADING_AI_MOBILE_USER: نام کاربری غیرقابل حدس.
   - TRADING_AI_MOBILE_PASSWORD_HASH: هش تولیدشده با `caddy hash-password`.
5. پورت 443 را در فایروال باز کنید. پورت 8765 باید فقط loopback بماند.
6. Caddy را اجرا و ورود به `https://دامنه` را آزمایش کنید.
7. در APK همین URL را وارد کنید.

## ساخت خودکار APK در GitHub
1. فایل‌های پروژه را در مخزن قرار دهید.
2. در تب Actions گردش‌کار **Build TradingSignalAI Pro Android APK** را اجرا کنید.
3. پس از موفقیت، Artifact با نام `TradingSignalAIPro-Android-debug` را دریافت کنید.
4. خروجی Debug فقط برای تست است؛ برای انتشار عمومی باید با کلید Release اختصاصی امضا شود.

## ساخت محلی
- Android Studio: پوشه `android-mobile` را باز کنید؛ SDK Platform 35 و JDK 17 لازم است.
- Windows: `build-apk.bat`
- Linux/macOS: `./build-apk.sh`
- خروجی: `app/build/outputs/apk/debug/app-debug.apk`

## محدودیت‌ها
- بدون سرور روشن، دامنه و TLS معتبر، برنامه به موتور وصل نمی‌شود.
- Basic Auth فعلی تک‌کاربره است؛ برای چند کاربر یا نقش‌های مختلف باید هویت اختصاصی اضافه شود.
- MetaTrader 5 روی Windows میزبان اجرا می‌شود.
- ارسال سفارش واقعی در این نسخه وجود ندارد.
