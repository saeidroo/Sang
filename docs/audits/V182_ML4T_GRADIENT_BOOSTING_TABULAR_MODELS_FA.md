# V182 — Gradient Boosting و مدل‌های جدولی پیشرفته در ML4T

تاریخ: 2026-11-21

## منابع رسمی و کدهای بررسی‌شده
- فصل ۱۲ و راهنمای رسمی آن
- `01_ensemble_foundations.py`: Random Forest در برابر XGBoost، LightGBM و CatBoost
- `02_gbm_comparison.py`: مقایسه کتابخانه‌ها، CPU/GPU، ظرفیت و محدودیت‌ها
- `03_dl_vs_gbm.py`: LightGBM، MLP، TabM و TabPFN در walk-forward
- `04_optuna_tuning.py` و `05_cross_library_hpo.py`: TPE، pruning، early stopping و HPO بین کتابخانه‌ها
- `06_optuna_multi_asset.py`: هدف‌های چندگانه و انتقال تنظیمات بین دارایی‌ها
- `08_shap_analysis.py` و `09_xai_limitations.py`: TreeSHAP، تعامل‌ها، drift و Rashomon effect
- `11_conformal_gbm.py`: calibration زمانی، purge و embargo
- `12_case_study_insights.py`: مقایسه چندمطالعه‌ای با baseline خطی و TabM

## اصول افزوده‌شده به همان curriculum مشترک
1. Treat a single decision tree as a high-variance baseline; bagging reduces variance by averaging, while boosting sequentially fits residual structure and may amplify noise.
2. Require every GBM to beat the Chapter 11 linear baseline on identical point-in-time features, labels, folds, universe, execution assumptions and net-of-cost metrics.
3. Compare XGBoost, LightGBM and CatBoost by data shape, categorical handling, compute, inference latency, regularization and reproducibility; reputation is not evidence.
4. Control tree capacity jointly through depth/leaves, minimum child samples, row/feature subsampling, learning rate, boosting rounds and L1/L2 regularization.
5. Treat LightGBM leaf-wise growth and num_leaves as capacity controls; constrain leaves and minimum data per leaf for noisy or limited samples.
6. Use CatBoost categorical processing only with point-in-time-valid categories, fold-local fitting and explicit handling of unseen categories.
7. Match objective to task: regression for return forecasts, classification for direction/events, ranking for cross-sectional ordering; evaluate the actual portfolio decision.
8. Test monotonic constraints only when a defensible domain relationship exists, against unconstrained models on identical temporal folds.
9. Use early stopping on a chronological validation tail inside training; outer validation and final holdout must not select boosting iterations.
10. For panels, split and score by complete timestamps, never arbitrary row offsets that divide one decision timestamp across partitions.
11. Use Optuna TPE with a fixed, logged compute budget; record trials, seeds, folds, objectives, pruning states, failures and software versions.
12. Prune only when intermediate scores are comparable; noisy early IC may discard slower-learning candidates, so audit pruning sensitivity against a no-pruning run.
13. Aggregate HPO objectives across multiple chronological walk-forward folds; preserve label-horizon purge and embargo at every boundary.
14. Inspect multi-objective frontiers such as IC versus turnover or net return versus drawdown; document trade-offs instead of arbitrary scalar weights.
15. Treat Pareto candidates as a shortlist, not a winner certificate; compare costs, capacity, tail risk and fold stability.
16. Treat cross-asset hyperparameter transfer as a hypothesis and validate it on destination-asset development folds.
17. Count library, objective, features, parameter ranges, seeds, checkpoints and pruning policy as model selection; keep all choices inside development data.
18. Inspect learning curves and checkpoint trajectories; sharp peaks, holdout decay and seed-sensitive rankings indicate possible overfit.
19. Use TreeSHAP, permutation importance and native importance as complementary, method-dependent views, not interchangeable truths.
20. Mean absolute SHAP is attribution magnitude, not direction, causality or economic value; inspect signed dependence, interactions and out-of-sample contribution.
21. Check SHAP stability across folds, seeds and near-equivalent models; Rashomon effect means similar predictions can have different attributions.
22. Monitor feature-distribution drift and SHAP-attribution drift chronologically; attribution change is a diagnostic, not proof of strategy failure.
23. Perform SHAP-based feature pruning only inside development folds; retrain and confirm later, without using outer-test explanations for selection.
24. Compare TabM/TabPFN with tuned GBMs and linear baselines on matched walk-forward folds, including compute, inference, sample limits, calibration and temporal shift.
25. For TabPFN, account for license, weight access and supported sample/feature regime; zero-shot inference does not establish validity in a new market.
26. Use the final holdout once after freezing model family, hyperparameters, features, checkpoints and explanation policy.
27. Do not promote a model based on one best fold or gross metric; require repeated out-of-sample, net-of-cost and operational evidence.

## ملاحظات TradingAI
- اصول فصل ۱۲ به همان patch آموزشی موجود افزوده شد؛ ماژول یا مغز جدید ساخته نشد.
- هیچ مدل XGBoost/LightGBM/CatBoost/TabM/TabPFN به runtime اضافه یا فعال نشد.
- هیچ HPO، آموزش مدل یا SHAP روی داده TradingAI اجرا نشد.
- نتایج ETF و سایر case studyهای ML4T به بازار ایران تعمیم داده نمی‌شوند.
- سیگنال، امتیاز، ریسک و سفارش تغییر نکردند؛ PAPER/Shadow تنها.
- این دانش به‌صورت قواعد مشورتی در curriculum ثبت شده؛ استفاده مؤثر runtime هنوز اثبات نشده است.

## مرحله بعد
فصل ۱۳: Deep Learning for Time Series؛ مقایسه LTSF-Linear، LSTM/TCN و معماری‌های جدید با کنترل پیچیدگی و اعتبارسنجی زمانی.
