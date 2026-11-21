# V188 — Machine Learning for Trading: Transaction Costs

## دامنه و منابع

فصل ۱۸ مخزن رسمی Stefan Jansen با تمرکز بر هزینه معامله به‌عنوان قید سرتاسری چرخه ML4T بررسی شد؛ از ارزیابی سیگنال و ساخت پرتفوی تا اجرا، TCA و پایش اقتصادی. منبع اصلی: [18_transaction_costs](https://github.com/stefan-jansen/machine-learning-for-trading/tree/main/18_transaction_costs).

README فصل و پیاده‌سازی‌های Python زیر بررسی شدند:
- `01_cost_taxonomy.py` — اجزای هزینه، واحدها، برنامه کارمزد و آلفای سربه‌سر.
- `02_spread_estimation.py` — Corwin–Schultz و Roll، اعتبارسنجی با quote و تفاوت رتبه‌بندی با دقت سطح.
- `03_market_impact_calibration.py` — square-root impact، participation، Kyle lambda و ظرفیت؛ تفکیک داده قابل اندازه‌گیری از ضرایب سناریویی.
- `04_vwap_twap_execution.py` — زمان‌بندی TWAP/VWAP و برآورد منحنی حجم درون‌روزی.
- `05_almgren_chriss_optimal_execution.py` — temporary/permanent impact، timing risk و implementation shortfall.
- `06_ml4t_execution_demo.py` — مدل‌های no/linear/square-root/power-law impact و محدودیت volume point-in-time.
- `07_ml4t_volume_participation.py` — سقف participation، partial fills و اجرای سفارش روی بازه‌های واقعی.
- `08_ml_dynamic_execution.py` — اجرای پویا/RL در مقایسه با baselineهای ثابت.
- `09_frequency_tradeoff.py` — تعامل فرکانس، turnover، signal decay و net Sharpe.
- `10_gross_vs_net_performance.py` — waterfall هزینه معامله، تأمین مالی، borrow و هزینه‌های صندوق.
- `11_cost_cliff.py` — آستانه‌ای که turnover هزینه را بر آلفا غالب می‌کند.
- `12_commission_slippage_comparison.py` — مدل‌های کارمزد و slippage در واحدهای مختلف.
- `_cost_analysis.py` — توابع مشترک تخمین spread، ADV، impact، capacity و breakeven.

## قواعد استخراج‌شده

۵۴ قاعده عملی به همان curriculum مشترک اضافه شد. محورهای اصلی:
1. طبقه‌بندی هزینه‌های explicit، implicit، capacity و financing با حفظ واحد و lineage.
2. تخمین و اعتبارسنجی spread و impact؛ جلوگیری از تبدیل نادرست حجم/واحد و leakage.
3. مدل‌های linear، square-root و power-law و تحلیل ظرفیت با participation و ADV نقطه‌زمانی.
4. TWAP، VWAP، partial fills، volume participation و کنترل زمان‌بندی.
5. چارچوب Almgren–Chriss، temporary/permanent impact، timing risk و implementation shortfall.
6. TCA، gross-to-net waterfall، break-even turnover، cost cliff و guardrails.
7. آزمون chronological برای execution ML/RL و منع ارتقای خودکار به معاملات زنده.

## مرز اعتبار و ایمنی

این تغییر فقط دانش/قواعد مشورتی را به فایل curriculum موجود اضافه می‌کند. هیچ cost engine، execution adapter یا runtime brain bus ساخته یا فعال نشده است؛ هیچ معامله زنده یا تغییر خودکار ریسک مجاز نیست. ضرایب آموزشی و نتایج بازارهای خارجی، تخمین معتبر برای صرافی/کارگزار یا دارایی‌های پروژه محسوب نمی‌شوند. اعتبارسنجی واقعی مستلزم داده سفارش و fill متعلق به همان بازار، واحدهای درست، آزمون shadow و مقایسه با baselineهای منجمد است.

## کنترل تغییر

- Branch: `fix/v156-cross-timeframe-brain-bus`
- Curriculum patch: `source/patches/V156_BOOK_CURRICULUM_SHARED_BRAIN_V2.patch`
- Rule count: ۵۴
- Runtime behavior changed: خیر
- Next curriculum chapter: Chapter 19 — Risk Management
