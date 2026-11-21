# V181 — خط مبنای خطی، ارزیابی و عدم‌قطعیت در ML4T

تاریخ: 2026-11-21

## منابع رسمی بررسی‌شده
- فصل ۱۱: The ML Pipeline
- `02_regularization_paths.py`
- `03_logistic_classification.py`
- `04_nested_cv_hpo.py`
- `05_shap_analysis.py`
- `06_conformal_prediction.py`

## اصول افزوده‌شده به همان curriculum مشترک
1. پیش از مدل پیچیده، OLS/Ridge/LASSO/Elastic Net به‌عنوان baseline با fold، label، feature و هزینه یکسان مقایسه شوند.
2. Ridge برای سیگنال‌های ضعیف و پخش‌شده میان featureهای همبسته، LASSO برای فرضیه sparsity و Elastic Net برای ترکیب sparsity و گروه‌های همبسته قابل آزمون‌اند؛ این انتخاب‌ها قانون قطعی نیستند.
3. استانداردسازی مدل خطی regularized داخل هر training fold fit شود و همان state به داده‌های بعدی اعمال شود.
4. شبکه alpha از پیش تعریف و به‌صورت landscape بررسی شود؛ plateau پایدار از قله تیز و شکننده بهتر است.
5. انتخاب hyperparameter با nested walk-forward انجام شود: inner برای انتخاب، outer برای برآورد؛ holdout نهایی از همه انتخاب‌ها دور بماند.
6. در regression علاوه بر خطای پیش‌بینی، IC/ICIR، ثبات رتبه، turnover و نتیجه پس از هزینه‌ها سنجیده شوند.
7. در classification، baseline اکثریت کلاس، توازن کلاس، AUC و precision/recall گزارش شود؛ accuracy تنها کافی نیست.
8. احتمال‌ها فقط روی بخش calibration زمانیِ جدا از fit کالیبره شوند و reliability در fold و regime بررسی شود.
9. ضریب و SHAP attribution توضیح رفتار مدل‌اند، نه اثبات علیت؛ تمرکز و ثبات اهمیت feature در foldها و رژیم‌ها بررسی شود.
10. در مدل خطی، SHAP با رابطه coefficient × انحراف feature از background کنترل شود؛ تغییر background، مرجع توضیح را تغییر می‌دهد.
11. پوشش conformal باید در طول زمان و رژیم نوسان پایش شود؛ exchangeability در بازار مالی تضمین دائمی ندارد.
12. بازه عدم‌قطعیت، احتمال کالیبره‌شده و توضیح مدل تا عبور از دروازه اعتبارسنجی مستقل نباید اندازه موقعیت یا ریسک را تغییر دهند.

## ملاحظات برای TradingAI
- این موارد به همان patch آموزشی V156 افزوده شدند؛ هیچ مدل جدیدی به runtime اضافه نشد.
- نتیجه تجربی فصل روی ETFها به بازار/داده TradingAI تعمیم داده نمی‌شود.
- هیچ تستی روی سورس اجرایی TradingAI انجام نشد و کیفیت مدل فعلی تأیید نشده است.
- سیگنال، امتیاز، ریسک و سفارش تغییر نکردند؛ PAPER/Shadow تنها.

## مرحله بعد
فصل ۱۲: Gradient Boosting و مدل‌های جدولی پیشرفته؛ تمرکز بر مقایسه با baseline خطی، کنترل Optuna و nested walk-forward، بدون فعال‌سازی در runtime.
