# V185 — Causal Machine Learning (ML4T Chapter 15)

تاریخ: 2026-11-21

## سورس‌های واقعی فصل بررسی‌شده
منبع رسمی فصل ۱۵: مخزن Stefan Jansen، مسیر `15_causal_estimation`.
فایل‌های منبع بررسی‌شده:
- `01_library_overview.py`: راهنمای انتخاب DoWhy، EconML، CausalML، Tigramite و causal-learn؛ تمایز برآورد اثر از کشف ساختار.
- `02_dowhy_causal_graph.py`: DAG، backdoor adjustment، زمان‌بندی treatment/outcome، دو outcome متفاوت، negative controls و partial-R2 sensitivity.
- `03_econml_dml.py`: Double Machine Learning، residual-on-residual، cross-fitting زمانی، purge/embargo، block permutation و HAC/Driscoll-Kraay.
- `04_dml_crypto_regime.py`: treatment پیوسته، اثر در رژیم‌های نوسان، تعامل treatment×regime، block permutation و کنترل‌های pre-treatment.
- `05_momentum_causal_trading.py`: CausalForestDML، ATE/CATE، مقایسه causal sizing با naive/heuristic و هزینه معاملات.
- `06_fed_announcement_bsts.py`: counterfactual با BSTS، انتخاب کنترل و بررسی spillover، placebo event dates.
- `07_tigramite_time_series.py`: PCMCI، Granger comparison، BH-FDR و bootstrap stability.
- `08_neural_causal_discovery.py`: NOTEARS، VAR-LiNGAM، PCMCI و محدودیت‌های فرضیاتی کشف ساختار.
- `09_adia_causal_benchmark.py`: benchmark مصنوعی، identifiability و خطر varsortability.
- `10_case_study_insights.py`: مقایسه نتایج ثبت‌شده causal در case studyها و HAC/refutation evidence.
- `11_factor_zoo_validation.py`: post-double-selection LASSO و آزمون factor-spanning با outcome مستقل.

راهنمای فصل صریحاً می‌گوید estimator پیچیده نمی‌تواند شکست در شناسایی (identification failure) را جبران کند. DAG و adjustment set باید با فرض‌های روشن شروع شوند؛ DML، BSTS و causal discovery سه سؤال متفاوت را پاسخ می‌دهند. citeturn967929search1turn967929search4

## 55 قاعده عملی افزوده‌شده
1. Start every causal study with an explicit question: unit, treatment, outcome, estimand, target population, intervention contrast and counterfactual.
2. Separate prediction from causation: predictive association can be useful without identifying an intervention effect, and causal identification does not guarantee profitable prediction.
3. Draw a domain-informed DAG before selecting controls; state which arrows are assumptions and which are supported by external mechanism knowledge.
4. Classify candidate variables as pre-treatment confounders, treatment descendants/mediators, colliders, instruments or unrelated variables before adjustment.
5. Adjust for plausible common causes of treatment and outcome; do not automatically control every correlated variable.
6. Do not condition on colliders or their descendants; doing so can open a non-causal path and create selection bias.
7. Do not control for post-treatment mediators when estimating the total treatment effect; doing so changes the estimand and may block part of the effect.
8. Use the backdoor criterion only when the assumed graph supports it; an identified adjustment set is conditional on the graph being credible.
9. Write down the estimand before choosing a library: continuous marginal effect, binary-treatment ATE, subgroup effect/CATE, event impact or lagged causal structure are different targets.
10. Do not binarize a continuous treatment merely to fit a preferred estimator without acknowledging that the estimand changes to a high-versus-low contrast.
11. Check treatment and outcome timing explicitly: confounders must be known before treatment assignment and outcomes must begin after the treatment decision.
12. Reject controls derived from the treatment itself or from future observations unless the estimand and causal graph explicitly justify them.
13. Use Double Machine Learning residualization: estimate outcome and treatment nuisance functions from controls, then estimate the treatment effect from orthogonalized residuals.
14. Use cross-fitting so nuisance predictions for each observation come from models not trained on that observation; in panels, split by complete decision timestamps.
15. Use chronological walk-forward cross-fitting for market data; random K-fold splits can leak future regimes and overlapping forward labels.
16. Apply purge to remove training observations whose outcome-information intervals overlap validation/test intervals, and embargo adjacent dependent observations where needed.
17. Keep nuisance-model tuning, feature selection and effect-heterogeneity choices inside training folds; never select them on the final holdout.
18. Distinguish DML controls W from effect modifiers X: W removes confounding, while X allows treatment effects to vary; putting a confounder in the modifier slot does not make it an adjustment control.
19. Compare DML against naive OLS and transparent linear adjustment; a large change after adjustment is evidence of confounding sensitivity, not automatic proof that DML is correct.
20. Test nuisance-model sensitivity across plausible linear and nonlinear learners; causal estimates that reverse under modest nuisance changes are fragile.
21. Use HAC or panel-robust uncertainty estimators that match the dependence structure; overlapping forward returns and common date shocks invalidate IID standard errors.
22. Set HAC bandwidth with reference to label horizon and dependence, and report the choice; standard errors should reflect overlap and shared cross-sectional shocks.
23. Use block permutation placebos that preserve treatment persistence and relevant panel structure; independent row shuffling is often an unrealistic null.
24. Repeat permutation refutation across defensible block lengths; a result that survives only one arbitrary block size is weak evidence.
25. Use placebo treatments, placebo dates and negative-control outcomes to challenge timing and shared-driver explanations; passing them weakens alternatives but does not prove causality.
26. Run sensitivity analysis for unobserved confounding, such as partial-R2 or robustness values; report how strong an omitted variable must be to change the conclusion.
27. Check subset and specification stability across time windows, assets and regimes; stability is supportive evidence, not identification by itself.
28. Compare the same treatment against outcomes with different mechanistic proximity; a credible effect on a direct mechanism outcome may coexist with weak evidence on broad market returns.
29. Do not infer a tradable directional return effect from evidence that a market mechanism reverts; premium reversion and asset return are distinct outcomes.
30. For heterogeneous effects, define effect modifiers before inspecting results and validate subgroup/CATE stability on later periods; post-hoc regime slicing invites multiple testing.
31. Treat regime-specific ATEs as subgroup averages, not automatically as individual-level CATEs; name the estimand accurately.
32. Only test causal position sizing after the effect model is frozen; compare naive, heuristic and causal scaling on a held-out period under identical costs and constraints.
33. A causal sizing rule cannot rescue a treatment whose effect reverses out of sample; require direction and magnitude stability before using it.
34. For discrete events, define the event timestamp, anticipation window, treatment window, outcome horizon and cumulative effect before fitting the counterfactual.
35. BSTS/event-study controls must track the untreated outcome before the event and remain unaffected by the event; control spillover contaminates the synthetic counterfactual.
36. Validate control spillover per event and per control; a control that reacts to the same macro shock is not an untreated comparison series.
37. Check event-time granularity: daily bars can mix pre-announcement and post-announcement trading, so align to the actual release time and market session.
38. Use pre-period fit diagnostics and posterior predictive checks for BSTS; a visually plausible counterfactual is not sufficient evidence.
39. Run placebo event dates and placebo outcomes; account for other announcements or shocks coinciding with placebo windows.
40. Interpret BSTS credible intervals as conditional on model and control assumptions; they do not include every source of identification uncertainty.
41. Treat PCMCI and other causal-discovery outputs as candidate lagged structures, not verified causal edges; hidden confounding and measurement choices remain.
42. Compare PCMCI with pairwise Granger carefully: Granger tests incremental predictive content conditional on chosen lags, not intervention causality.
43. Apply false-discovery-rate correction across tested variable pairs and lags; uncorrected edge counts are inflated by the search space.
44. Check causal-discovery stability across bootstrap samples, lag limits, frequencies, variable sets and regimes; unstable edges should not become trading rules.
45. Respect time ordering and stationarity assumptions in time-series discovery; structural breaks, mixed frequencies and asynchronous observations can create spurious links.
46. Use NOTEARS and VAR-LiNGAM only with their structural assumptions stated; linearity, non-Gaussianity, acyclicity and noise assumptions affect identifiability.
47. Do not treat an observationally learned DAG as uniquely identified when multiple graphs are Markov-equivalent or when latent confounding is plausible.
48. Benchmark causal-discovery algorithms on synthetic data with known ground truth to test implementation, but do not infer real-market validity from simulator accuracy.
49. Beware simulator artifacts such as varsortability; supervised models may learn the data generator's quirks rather than transferable causal structure.
50. Keep factor-zoo and post-double-selection tests honest: exclude the held-out outcome from the factor/control span and use time-ordered selection.
51. Report causal-run coverage, estimand units, control sets, fold counts, HAC uncertainty and refutation outcomes; missing runs are unavailable evidence, not null effects.
52. Correct for multiple causal hypotheses, outcomes, regimes, lags and specifications; a collection of individually significant tests is not a single confirmed mechanism.
53. Treat causal significance as insufficient for trading: require out-of-sample predictive contribution, execution feasibility, fees, slippage, capacity and risk checks.
54. Keep causal evidence advisory until independent shadow validation; it must not directly override existing brain decisions or change live signal, score, risk or orders.
55. Foreign-market causal findings are methodological references only; treatment mechanisms, confounders and event responses require local identification in the target market.

## جمع‌بندی تصمیمی
- همبستگی و قدرت پیش‌بینی، به‌تنهایی اثر علّی را اثبات نمی‌کنند.
- DML اثر treatment پیوسته را پس از orthogonalization و کنترل confounderهای قابل مشاهده تخمین می‌زند؛ confounding پنهان همچنان ممکن است باقی بماند.
- BSTS counterfactual می‌سازد، اما اعتبار آن به کنترل‌های بدون spillover و کیفیت pre-period وابسته است.
- PCMCI/NOTEARS/Granger ساختارهای کاندیدا می‌دهند؛ خروجی آن‌ها اثبات قطعی causal edge نیست.
- causal effect و predictive alpha دو معیار جدا هستند؛ برای معامله باید هر دو مسیر جداگانه اعتبارسنجی شوند.

## وضعیت TradingAI
- 55 اصل فصل ۱۵ به همان curriculum موجود اضافه شد.
- شاخه و ساختار پروژه تغییر نکرد؛ هیچ مغز یا ماژول تازه‌ای ساخته نشد.
- هیچ مدل causal runtime آموزش یا فعال نشد؛ هیچ داده TradingAI برای benchmark استفاده نشد.
- هیچ سیگنال، امتیاز، ریسک یا سفارشی تغییر نکرد؛ PAPER/Shadow پابرجاست.
- ثبت دانش در patch به‌تنهایی اثبات نمی‌کند runtime مغزها آن را در تصمیم واقعی مصرف می‌کنند.

## مرحله بعد
فصل ۱۶ — Backtesting and Strategy Simulation: شبیه‌سازی رویدادمحور، ترتیب سفارش/پرشدن، benchmark، جلوگیری از look-ahead و اعتبارسنجی بازده قابل تحقق.
