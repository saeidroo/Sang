# V187 — Portfolio Construction (ML4T Chapter 17)

تاریخ: 2026-11-21

## منابع رسمی بررسی‌شده
راهنمای فصل ۱۷ و کدهای واقعی Python در مخزن Stefan Jansen بررسی شدند:
- `01_portfolio_metrics.py`: سنجه‌های بازده/ریسک، drawdown و benchmark-relative.
- `02_mean_variance_optimization.py`: efficient frontier، max-Sharpe، min-variance و مقایسه با heuristicها.
- `03_robust_optimization.py`: Ledoit-Wolf shrinkage، risk parity، minimum variance و minimum conditional drawdown.
- `04_kelly_criterion.py`: Kelly از binary wager تا continuous/multi-asset portfolio.
- `06_hierarchical_risk_parity.py`: clustering، quasi-diagonalization و recursive bisection.
- `07_conformal_position_sizing.py`: interval-width sizing و مقایسه با equal-weight و score-weighting.
- `08_library_comparison.py`: مقایسه PyPortfolioOpt، Riskfolio-Lib و skfolio با moments مشترک و allocationهای frozen.
- `09_allocator_comparison.py`: مقایسه کنترل‌شده EW، inverse-vol، shrinkage MVO و HRP با signal مشترک و holdout.
- `11_dl_portfolio_allocation.py`: تخصیص مستقیم end-to-end با objective شارپ.
- `12_vlstm_portfolio.py`: variable-selection + LSTM و turnover-aware policy.
- `13_deepm_regime_robust.py`: DeePM و SoftMin برای جریمه‌کردن پنجره‌های ضعیف.

## 48 قاعده عملی افزوده‌شده
1. Treat portfolio construction as a distinct mapping from forecasts and risk estimates to feasible holdings; a good prediction is not yet an investable portfolio.
2. Write an allocator term sheet before fitting: objective, input estimates, estimation window, rebalance schedule, eligible universe, constraints, leverage, turnover penalty and fallback behavior.
3. Separate alpha estimation, risk estimation, allocation, execution and risk overlay so each layer can be evaluated and diagnosed independently.
4. Keep the prediction stream fixed when comparing allocators; otherwise model and allocation effects become confounded.
5. Establish equal-weight and inverse-volatility baselines before optimization; add volatility targeting and simple score weighting where relevant.
6. Use the same dates, universe, signals, capital, costs, rebalance schedule and constraints for every allocator comparison.
7. Fit expected returns and covariance using only information available at the allocation timestamp; never use full-sample estimates in historical weights.
8. Estimate means and covariance on matched windows and document window length, frequency, missing-data policy and annualization convention.
9. Recognize that mean-variance optimization is highly sensitive to expected-return estimation error; small input changes can create extreme and unstable weights.
10. Compare maximum-Sharpe, minimum-variance and constrained alternatives; do not treat one optimizer objective as universally best.
11. Use covariance shrinkage, such as Ledoit-Wolf, as an estimation regularizer; record the target and fit it only on the training window.
12. Consider factor or structured covariance when asset count is large relative to observations; validate factor stability and residual correlation.
13. Impose economically justified bounds on individual weights, group exposures, gross/net leverage, concentration and short positions.
14. Treat constraints as part of the allocator specification, not post-hoc clipping that silently changes the optimizer's solution.
15. Penalize turnover or distance from current holdings when rebalancing costs matter; evaluate the resulting cost-performance trade-off.
16. Use risk parity or equal-risk contribution to diversify risk contributions, not as a claim that nominal weights or returns are equal.
17. Check marginal and component risk contributions; a portfolio with many holdings can still be dominated by one correlated risk cluster.
18. Understand HRP as clustering, quasi-diagonalization and recursive bisection; its benefit is robustness to noisy covariance inversion, not guaranteed superior returns.
19. Test HRP sensitivity to distance metric, linkage method, covariance window and cluster stability; avoid treating one dendrogram as ground truth.
20. Compare HRP with shrinkage MVO and simple heuristics on identical walk-forward folds.
21. Interpret inverse-volatility weights as a simple risk scaling rule; they do not account for correlations or expected returns.
22. Volatility targeting scales aggregate exposure toward a risk budget; cap leverage and test realized volatility overshoot during jumps and regime shifts.
23. Use score weighting only after defining score calibration, sign handling, normalization, clipping and treatment of negative or missing scores.
24. Normalize weights under explicit long-only or long-short rules; distinguish net exposure from gross exposure.
25. Kelly maximizes expected log wealth under its assumptions; estimated inputs can make full Kelly leverage dangerously large.
26. Use fractional Kelly and explicit leverage caps as conservative variants; stress estimation error, tail risk and drawdown before any sizing use.
27. Do not convert raw model confidence directly into leverage unless calibration and mapping are validated out of sample.
28. Conformal-width sizing can use wider predictive intervals as a proxy for greater uncertainty; verify coverage by entity, regime and time before relying on it.
29. Conformal interval width is not automatically a volatility or covariance estimate; compare it with equal-weight and score-weighted baselines.
30. Keep conformal calibration chronological and horizon-aware; exclude overlapping or unresolved calibration outcomes through appropriate embargo.
31. Evaluate portfolio shape as well as returns: concentration, HHI, active share, diversification, risk contributions and leverage stability.
32. Use benchmark-relative metrics such as information ratio and active share only with a clearly specified benchmark and investable universe.
33. Report gross/net performance, turnover, drawdown, exposure, concentration, risk contribution and weight stability together; Sharpe alone is insufficient.
34. Measure allocator stability across folds, seeds, windows and small perturbations of expected returns/covariance; unstable weights are an implementation risk.
35. Freeze each allocator's weights or decision rule before scoring the subsequent evaluation window; do not refit on the evaluation outcomes.
36. Select the allocator inside development/validation data and open the final holdout only once for confirmation.
37. Count allocator families, objectives, constraints, windows, hyperparameters and post-hoc metric choices as research trials; allocator selection itself can overfit.
38. Use multiple-testing-aware inference when many allocation variants have been explored; the best observed Sharpe is selection-biased.
39. Do not cherry-pick a crisis interval after seeing factor correlations; distinguish predeclared stress analysis from retrospective storytelling.
40. Treat historical factor diversification evidence as sample- and regime-dependent; correlations can rise in crises and across asset classes.
41. Compare optimizer libraries on matched moments, objectives and constraints; reconcile solutions within solver tolerance before comparing their backtests.
42. Translate vectorized target weights into execution-aware daily holdings and verify that turnover, cash and constraints reconcile with the simulator.
43. Deep end-to-end allocation entangles prediction, sizing, turnover and risk in one objective; benchmark it against simple heuristics and disclose the changed task.
44. Use chronological validation for deep portfolio policies; avoid random splits and ensure each training sample's return horizon is resolved before validation.
45. Treat differentiable Sharpe and SoftMin/worst-window objectives as training objectives, not proof of robust future performance; inspect all rolling windows.
46. Assess deep allocator sensitivity to seeds, architecture, training window, regime composition and loss design; retain simpler methods absent repeatable gains.
47. Do not compare a direct policy that consumes raw features against a classical allocator consuming frozen forecasts as if their information sets were identical.
48. Keep allocator outputs advisory until independent validation with realistic costs, capacity, constraints and shadow execution; no curriculum rule may directly activate live orders or risk changes.

## نتیجه برای TradingAI
- 48 اصل به همان curriculum مشترک موجود افزوده شد؛ هیچ شاخه یا مغز جدیدی ایجاد نشد.
- فقط Patch آموزشی تغییر کرد؛ optimizer یا portfolio allocator در runtime ساخته یا فعال نشد.
- هیچ signal، score، position، risk یا order زنده‌ای تغییر نکرد.
- ثبت قواعد در GitHub به‌تنهایی ثابت نمی‌کند مغزهای runtime آن‌ها را بارگذاری یا در تصمیم‌گیری مصرف می‌کنند.
- نمونه‌ها و نتایج فصل بر ETFها، CME futures و داده‌های خارجی تکیه دارند؛ قواعد بازار ایران باید با محدودیت‌های واقعی بازار مقصد اعتبارسنجی شوند.

## گام بعد
فصل ۱۸ — Transaction Costs.
