# V190 — Machine Learning for Trading: Strategy Synthesis

## دامنه و منابع

فصل ۲۰ مخزن رسمی Stefan Jansen بررسی شد. این فصل ۹ case study را در یک pipeline استاندارد از داده و feature تا label، model، prediction، portfolio، هزینه، risk overlay و holdout کنار هم قرار می‌دهد. هدف آن رتبه‌بندی ساده Sharpe نیست؛ تشخیص این است که هر مرحله چگونه سیگنال را تقویت یا تضعیف می‌کند.

منبع فصل: [20_strategy_synthesis](https://github.com/stefan-jansen/machine-learning-for-trading/tree/main/20_strategy_synthesis)

README و هشت پیاده‌سازی Python زیر خوانده شدند:
- `01_aggregate_synthesis.py` — تجمیع registryهای case study، کامل بودن داده‌ها، canonical lineage، rank-1 و مقایسه paired validation/holdout.
- `02_feature_evaluation.py` — feature triage، adjusted p-values و Benjamini–Hochberg FDR.
- `03_signal_quality.py` — IC، پایداری و مقایسه familyها با کیفیت سیگنال.
- `04_signal_to_strategy.py` — تبدیل IC به Sharpe، breadth، cadence و translation در holdout.
- `05_portfolio_allocation.py` — مقایسه allocatorها با سیگنال ثابت و اثر کیفیت ranking.
- `06_cost_survival.py` — cost sweep، breakeven، cost margin و حساسیت turnover/frequency.
- `07_regime_risk.py` — risk overlay و تفکیک افت عملکرد در regimeها.
- `08_recommendations.py` — gateهای feature، signal، portfolio، cost، risk و holdout و ledger توصیه‌ها.

نوت‌بوک‌های متناظر نیز در فهرست رسمی فصل بررسی شدند؛ کدهای Python مبنای استخراج قواعد بودند. خود notebookها یا case studyهای upstream در این مرحله اجرا نشده‌اند؛ بنابراین هیچ عدد عملکردی از نتایج ثبت‌شده به‌عنوان نتیجه اجرای پروژه گزارش نمی‌شود.

## قواعد عملی استخراج‌شده

۵۳ قاعده جدید به همان curriculum موجود افزوده شد. محورهای اصلی:
1. استانداردسازی pipeline کامل و حفظ lineage هر configuration از train تا holdout.
2. FDR و feature triage؛ تفکیک معنی‌داری آماری از اثر اقتصادی و پایداری.
3. سنجش کیفیت سیگنال با IC/ICIR، fold consistency، uncertainty و holdout persistence.
4. تفکیک signal quality از تبدیل سیگنال به استراتژی و اثر breadth/cadence/allocator.
5. سنجش cost survival، breakeven، cost margin و ظرفیت با واحدهای صحیح.
6. جداسازی prediction decay، portfolio-translation decay و regime/structural break.
7. causal credibility، multiple testing، holdout discipline و اولویت‌بندی iteration بعدی.

## مرز اعتبار و اجرا

این مرحله فقط دانش تصمیم‌یار را به Patch مشترک موجود اضافه می‌کند. هیچ case study یا notebook اجرا نشده و هیچ نتیجه‌ای از این فصل به‌عنوان عملکرد واقعی TradingAI ادعا نمی‌شود. هیچ runtime brain bus، مدل synthesis، تغییر وزن سیگنال، کنترل ریسک خودکار یا سفارش زنده ساخته یا فعال نشده است. برای هر توصیه اجرایی، registry کامل، داده point-in-time، هزینه واقعی بازار هدف، holdout مستقل و shadow validation لازم است.

## کنترل تغییر

- Branch: `fix/v156-cross-timeframe-brain-bus`
- Patch: `source/patches/V156_BOOK_CURRICULUM_SHARED_BRAIN_V2.patch`
- New principles: ۵۳
- Runtime behavior changed: خیر
- ML4T Chapter 20: پایان فصل‌های اصلی این مسیر کتاب
