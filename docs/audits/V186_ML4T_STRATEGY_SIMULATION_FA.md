# V186 — Backtesting and Strategy Simulation (ML4T Chapter 16)

تاریخ: 2026-11-21

## منبع رسمی و فایل‌های بررسی‌شده
فصل ۱۶ مخزن Stefan Jansen با عنوان Strategy Simulation در مسیر `16_strategy_simulation` بررسی شد. فایل‌های واقعی:
- `README.md`: پروتکل بک‌تست، vectorized/event-driven، baseline، metrics، regime analysis و search-aware inference.
- `01_backtest_first_principles.py`: simulator شفاف با Polars/NumPy، next-open fill، proportional fees، cash constraint و benchmark هم‌زمان.
- `02_futures_backtesting.py`: multiplier، per-contract costs، overnight sessions، margin و futures accounting.
- `05_stateful_strategies.py`: Kelly sizing وابسته به P&L، pair legs وابسته به fill واقعی و drawdown circuit breaker.
- `06_framework_parity.py` و `07_engine_divergence_anatomy.py`: مقایسه array و sequential engine، کنترل fill ordering، rounding، commission headroom و اثر تنظیمات.
- `09_performance_reporting.py`: gross/net، benchmark همسان، exposure، closed trades و reconciliation هزینه‌ها.
- `11_sharpe_ratio_inference.py`: عدم قطعیت Sharpe، skewness، kurtosis و serial dependence.
- `12_dsr_validation.py`: Deflated Sharpe Ratio و Probability of Backtest Overfitting با CSCV.
- `13_ras_protocol.py`: Rademacher complexity و RAS bounds.
- `14_cost_sensitivity.py`: break-even cost و حساسیت بازده به فرض هزینه.
- `15_lean_engine_parity.py` و `18_vectorbt_engine_parity.py`: مقایسه frameworkها و اعلام صریح محدودیت asset support.

## 48 قاعده عملی افزوده‌شده
1. بک‌تست را تلاش برای رد استراتژی بدان، نه اثبات سودآوری.
2. زمان سیگنال، دسترسی داده، universe، rebalance، sizing، order، fill، هزینه، محدودیت و benchmark را پیش از ارزیابی ثابت کن.
3. vectorized را برای transitions از پیش معلوم و event-driven را برای state وابسته به cash، position، fill، P&L یا order pending انتخاب کن.
4. یکسان بودن سیگنال به معنی یکسان بودن اجرای دو engine نیست؛ event order، fill، rounding، cash و valuation را مقایسه کن.
5. پیش از مدل پیچیده یک baseline ساده و قابل ممیزی بساز.
6. سیگنال را فقط پس از زمان واقعی دسترسی همه ورودی‌ها تولید کن؛ اجرا زودتر از اولین رویداد قابل معامله ممنوع.
7. استفاده از close به‌عنوان fill سیگنالی که با همان close ساخته شده، بدون مدل closing auction واقع‌بینانه ممنوع.
8. target weights، submitted، accepted، partial fill و final position را stateهای مجزا بدان.
9. cash، quantity، cost basis، realized/unrealized P&L، fees، margin و equity را در ledger رویدادبه‌رویداد ثبت و reconcile کن.
10. ترتیب قطعی market data، signal، submit، fill، fee، position update و valuation را برای timestamp مشترک مشخص کن.
11. fill در next-open یا رویداد قابل اجرا را صریح مدل کن و gap بین مشاهده و اجرا را لحاظ کن.
12. semantics سفارش market/limit/stop/stop-limit شامل trigger، priority، expiry و gap را تعریف کن.
13. ترتیب لمس high/low در OHLC معلوم نیست؛ اگر stop و target هر دو لمس شدند، محافظه‌کارانه حل کن یا داده ریزتر بگیر.
14. partial fill و سفارش باقیمانده را مدل کن؛ تکمیل کامل سفارش را مفروض نگیر.
15. spread، commission، venue fee، tax، slippage، impact، funding و borrow را فقط در صورت کاربرد لحاظ و هر هزینه را یک بار اعمال کن.
16. حساسیت هزینه و break-even cost را گزارش کن؛ یک fee خوش‌بینانه کافی نیست.
17. slippage و impact را در صورت وجود داده به اندازه سفارش، volatility، spread و liquidity وابسته کن.
18. participation، volume، lot/tick، price limit، short، borrow و margin constraints را مطابق بازار اعمال کن.
19. حجم روزانه را معادل نقدشوندگی قابل مصرف یک سفارش ندان.
20. برای futures multiplier، point value، expiry، roll و session را لحاظ کن؛ continuous adjusted price ابزار اجرای واقعی نیست.
21. برای perpetuals funding، mark price، liquidation و maintenance margin را لحاظ کن.
22. corporate actions، split، dividend، delisting، symbol change و roll را در داده و ledger سازگار اعمال کن.
23. universe تاریخی را point-in-time بساز؛ constituentهای امروز باعث survivorship bias می‌شوند.
24. revised fundamentals، انتشار دیرهنگام و membership آینده را به گذشته نبر.
25. labelهای هم‌پوشان را با PnL واقعی portfolio اشتباه نگیر؛ سرمایه فقط یک مسیر واقعی را یک‌بار تجربه می‌کند.
26. بازده را از holdings قبلی و fills واقعی بساز؛ target همان دوره را روی بازدهی قبل از امکان اجرا اعمال نکن.
27. benchmark را با تاریخ، universe، سرمایه، ارز، rebalance و constraints یکسان مقایسه کن.
28. cash benchmark را وقتی استراتژی می‌تواند نقد بماند لحاظ و exposure را گزارش کن.
29. gross و net را کنار هم بیاور و اختلاف را با اجزای هزینه reconcile کن.
30. CAGR، volatility، Sharpe، drawdown، turnover، exposure، hit rate، tail losses و time-in-market را گزارش کن.
31. Sharpe سالانه‌شده به‌تنهایی کافی نیست؛ serial correlation، skew، kurtosis و طول نمونه مهم‌اند.
32. برای returns وابسته، uncertainty مناسب به کار ببر و فرض IID را بی‌دلیل نپذیر.
33. regime slicing را از قبل تعریف کن؛ پس از مشاهده نتیجه فقط دوره‌های مطلوب را انتخاب نکن.
34. cost sensitivity، benchmark، placebo و stress period برای به چالش کشیدن توضیح اقتصادی به کار ببر.
35. همه strategy/feature/threshold/parameter/reporting trials را بشمار؛ انتخاب بهترین، selection bias می‌آورد.
36. DSR را با trial count و non-normal moments صادقانه به کار ببر؛ اصلاح آماری تضمین نیست.
37. PBO/CSCV را با candidate-return matrix و افشای فرض‌ها اجرا کن؛ جایگزین chronological validation نیست.
38. RAS را diagnostic جداگانه با واحد native-frequency و فرض‌هایش گزارش کن.
39. انتخاب پارامتر فقط در development؛ walk-forward و final holdout زمانی برای تأیید یک‌باره.
40. هزینه، fill، benchmark یا accounting را برای سودده نشان دادن candidate دستکاری نکن؛ هر تغییر پروتکل آزمایش تازه است.
41. parity را با سیگنال، داده، تاریخ، سرمایه و هزینه همسان انجام بده و trade-level fills و valuation timestamps را reconcile کن.
42. divergence را با تغییر یک setting در هر بار تحلیل کن و مطمئن شو setting واقعاً در code path اثر دارد.
43. event log بازتولیدپذیر شامل data timestamp، signal، target، order، fill، fee، position، cash و equity نگه دار.
44. آمار closed-trade را از mark-to-market جدا کن؛ open position در equity/exposure هست ولی در win rate معاملات بسته نیست.
45. warm-up و missing dates را آشکار گزارش کن؛ تاریخ‌های نامطلوب را بی‌صدا حذف نکن.
46. ارزش اقتصادی prediction را پس از position conversion، turnover، cost و constraints بسنج؛ IC به‌تنهایی کافی نیست.
47. نتایج engine و هزینه بازار خارجی را روش‌شناسی بدان، نه مکانیک قابل انتقال؛ قواعد و داده بازار مقصد باید جداگانه اعتبارسنجی شوند.
48. برابری دو engine فقط سازگاری پیاده‌سازی تحت پروتکل مشترک را نشان می‌دهد؛ صحت داده، شناسایی edge یا سودآوری آینده را اثبات نمی‌کند. تا پایان shadow validation هیچ سفارش یا کنترل ریسک زنده‌ای فعال نشود.

## نتیجه برای TradingAI
- 47 اصل به همان curriculum موجود اضافه شد؛ شاخه یا مغز جدید ایجاد نشد.
- فقط فایل patch آموزشی تغییر کرد؛ هیچ backtester یا execution engine جدیدی ساخته/فعال نشد.
- هیچ runtime model، signal، score، risk یا order تغییر نکرد.
- این ثبت دانش به‌تنهایی ثابت نمی‌کند مغزهای runtime آن را مصرف می‌کنند.
- تمام نتایج فصل کتاب نمونه‌های روش‌شناختی‌اند؛ نه بک‌تست روی داده پروژه و نه گواهی سودآوری TradingAI.

## گام بعد
فصل ۱۷ — Portfolio Construction.
