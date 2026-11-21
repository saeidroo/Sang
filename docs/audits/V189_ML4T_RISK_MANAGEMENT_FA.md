# V189 — Machine Learning for Trading: Risk Management

## دامنه و منابع

فصل ۱۹ مخزن رسمی Stefan Jansen با هشت بخش موضوعی و یازده پیاده‌سازی اصلی بررسی شد. منبع: [19_risk_management](https://github.com/stefan-jansen/machine-learning-for-trading/tree/main/19_risk_management).

فایل‌های README و کدهای زیر مطالعه شدند:
- `01_var_cvar.py` — Historical، parametric، Cornish-Fisher و simulation VaR/CVaR، آزمون exceedance و تحلیل regime.
- `02_exit_strategies.py` — fixed، trailing، ATR-scaled، ML و hybrid exits؛ مقایسه stop-out و whipsaw.
- `03_position_sizing_mae_mfe.py` — fixed-fractional و inverse-vol sizing، concentration caps، MAE/MFE و scale-out.
- `04_factor_exposure.py` — CAPM و Fama-French factor exposure، rolling beta، HAC و attribution.
- `05_trade_shap_diagnostics.py` — خوشه‌بندی SHAP معاملات ناموفق و ساخت فرضیه تشخیصی.
- `06_stress_testing.py` — historical crisis replay، hypothetical shocks و Student-t Monte Carlo.
- `07_drift_detection.py` — PSI، Wasserstein، domain classifier و monitor هشدار drift.
- `08_ml_exit_signals.py` — معماری دو مدل entry/exit و ارزیابی مسیر واقعی معامله.
- `09_deep_hedging.py` — یادگیری hedge با هدف CVaR و هزینه معامله؛ مقایسه با delta hedge.
- `10_ml4t_backtest_risk_demo.py` — ترکیب position exit rules و portfolio limits شامل drawdown و daily loss.
- `11_systematic_risk_sweep.py` — کالیبراسیون زمانی stop/target/trailing با جداسازی calibration و evaluation.

## قواعد عملی استخراج‌شده

۵۴ قاعده عملی جدید به همان curriculum موجود اضافه شد. محورهای کلیدی:
1. VaR در برابر ES/CVaR، آزمون exceedance، tail uncertainty و regime conditioning.
2. Drawdown depth/duration/recovery و خطر مسیر واقعی equity.
3. Stop-loss، trailing، ATR، MAE/MFE و position sizing بدون leakage.
4. Factor/sector/macro exposure، beta drift و residual risk.
5. Historical، hypothetical، reverse و Monte Carlo stress testing.
6. Volatility targeting، portfolio limits، kill switches و governance.
7. Drift detection، retraining discipline، ML exits، deep hedging و محدودیت SHAP.

## مرز اعتبار

این تغییر فقط قواعد مشورتی را در curriculum موجود ثبت می‌کند. هیچ risk engine، kill switch، stop order، drift monitor یا runtime brain connection در پروژه ساخته یا فعال نشده است. نتایج ETF/crypto و عوامل خارجی، بدون اعتبارسنجی مستقل به بازار یا کارگزار پروژه قابل تعمیم نیستند. کنترل ریسک خودکار یا ارسال سفارش زنده مجاز نشده است.

## کنترل تغییر

- Branch: `fix/v156-cross-timeframe-brain-bus`
- Patch: `source/patches/V156_BOOK_CURRICULUM_SHARED_BRAIN_V2.patch`
- Rule count: ۵۴
- Runtime behavior changed: خیر
- Next chapter: Chapter 20 — Strategy Synthesis
