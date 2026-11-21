# V183 — Deep Learning for Time Series (ML4T Chapter 13)

تاریخ: 2026-11-21

## منبع اصلی و فایل‌های واقعی بررسی‌شده
راهنمای رسمی فصل ۱۳ و سورس نوت‌بوک‌های Jupytext:
- `01_core_architectures.py`: MLP، 1D-CNN، LSTM، GRU و مقایسه هزینه/پنجره
- `02_nbeats_interpretable.py`: N-BEATS generic/interpretable و خطر extrapolation
- `03_great_debate.py`: Linear، D-Linear، N-Linear در برابر Transformer و shuffle diagnostic
- `04_transformers.py`: PatchTST و iTransformer، patching، channel independence و attention
- `05_tcn.py`: causal dilated convolution و receptive field
- `06_tsmixer.py`: mixing روی محور زمان و feature
- `07_mamba_ssm.py`: selective state-space model
- `08_cnn_image_encoding.py`: Gramian Angular Field و Markov Transition Field
- `09_foundation_models.py`: Chronos/TinyTimeMixer zero-shot در برابر Ridge/LSTM
- `10_uncertainty.py`: MC Dropout، deep ensembles و conformal calibration
- `11_library_landscape.py`: تفاوت پیاده‌سازی و قابلیت مقایسه
- `12_case_study_insights.py`: مقایسه نتایج ثبت‌شده روی fold/dateهای همسان

## اصول افزوده‌شده
1. Explain why LSTM/GRU recurrence has sequential computation costs and why longer context does not guarantee useful information or improved forecasts.
2. Define the task before choosing architecture: direct cross-sectional prediction with sequential inputs is different from univariate or multivariate multi-step forecasting.
3. Build a baseline ladder on identical data and target: last-value/naive, Ridge or LTSF-Linear, then MLP/1D-CNN, recurrent, TCN/TSMixer and attention/state-space models.
4. Keep target dates fixed when changing lookback length or architecture; assign examples by target timestamp, not by the number of generated windows.
5. Align each input window strictly before its target; purge examples whose forward-label resolution crosses train/validation/test boundaries and keep all assets for a timestamp together.
6. Use expanding or rolling walk-forward folds for research conclusions; a single chronological split is a teaching diagnostic, not sufficient production evidence.
7. Fit scaling, normalization, imputation and feature selection only on the training window; apply frozen state to validation and test without using future observations.
8. Distinguish forecasting price levels from returns: level trends can make extrapolation appear strong while the trading task may concern stationary or near-stationary returns.
9. Treat N-BEATS trend/seasonality basis components as constrained model decompositions, not causal discoveries or proof that the series contains those economic factors.
10. Inspect N-BEATS extrapolation outside the training range; training-window normalization may leave later trend values outside the fitted scale.
11. Use LTSF-Linear, D-Linear and N-Linear as mandatory baselines before transformer adoption; complexity must earn its place with repeated out-of-sample gains.
12. Run a time-order shuffle diagnostic: compare both forecast error change and prediction movement; if predictions barely change, the model may not use temporal order.
13. Do not infer that all transformers fail from one benchmark; record dataset, target, context, horizon, features and split protocol when interpreting the linear-versus-transformer debate.
14. PatchTST turns short temporal patches into tokens and can reduce attention sequence length; channel-independent modeling is a design choice whose cross-feature interactions must be assessed.
15. iTransformer treats each variable's history as a token to model cross-variate relationships; attention weights are model internals, not causal influence or reliable feature importance.
16. Temporal Fusion Transformer is suited to covariate-rich multi-horizon settings; only genuinely known-in-advance future covariates may enter future decoder inputs.
17. TCN must use causal convolutions with correct padding/trimming; dilation expands receptive field, while residual connections and normalization affect optimization, not target availability.
18. TSMixer mixes the time and feature axes with dense layers; compare its parameter count and compute with attention and linear baselines at the same context and feature dimensions.
19. Mamba/selective state-space models offer a different long-sequence computation path; a simplified educational implementation is not assumed equivalent to the reference implementation.
20. Image encodings such as Gramian Angular Fields or Markov Transition Fields can discard return level/range through per-window normalization; evaluate whether discarded information matters to the target.
21. Foundation-model zero-shot outputs may forecast a different quantity or horizon from the trading label; describe such comparisons as ranking probes unless target and horizon are explicitly aligned.
22. Treat pretraining contamination as a distinct leakage channel that chronological train/test splitting cannot detect; investigate data provenance, cutoff dates and benchmark overlap.
23. Compare foundation models against task-specific Ridge and recurrent baselines using the same input context, point-in-time features, timestamps and target definition.
24. MC Dropout and deep ensembles estimate predictive spread but do not automatically provide calibrated coverage; assess empirical coverage by time fold and regime.
25. Conformal intervals require calibration residuals from a separate chronological segment with appropriate purge; financial non-stationarity and dependence weaken exchangeability guarantees.
26. Do not translate uncertainty estimates into position sizing or risk changes until coverage, calibration, net-of-cost value and regime robustness pass a separate shadow validation gate.
27. Compare model families only on matching case-study folds, dates, label horizons and sample coverage; report missing architecture coverage rather than silently comparing easier subsets.
28. Treat per-fold dispersion as descriptive rather than a confidence interval; use an appropriate dependence-aware estimator such as HAC for uncertainty in daily IC.
29. Count architecture, context length, horizon, feature set, seed, checkpoint and foundation-model prompt/configuration as model-selection trials; keep them inside development data.
30. Deep learning wins are dataset- and task-dependent; retain simpler tabular/linear baselines unless repeated evidence shows the sequence architecture adds net-of-cost value.

## جمع‌بندی کاربردی برای TradingAI
- معماری پیچیده به‌صورت پیش‌فرض بهتر نیست؛ LTSF-Linear/Ridge baseline اجباری باقی می‌ماند.
- پیش از استفاده از sequence model باید روشن شود مسئله پیش‌بینی cross-sectional با ورودی دنباله‌ای است یا forecasting چندگامه.
- هدف‌های forward-return و مرزهای زمانی باید با purge/embargo درست رعایت شوند.
- هیچ معماری LSTM/TCN/TSMixer/PatchTST/Mamba یا foundation model به runtime اضافه یا فعال نشد.
- هیچ آموزش یا benchmark روی داده واقعی TradingAI انجام نشد؛ این مرحله استخراج اصول و ثبت در curriculum است.
- نتایج case studyهای بازارهای خارجی مستقیماً به بازار ایران تعمیم داده نمی‌شوند.
- هیچ سیگنال، امتیاز، ریسک یا سفارشی تغییر نکرد؛ PAPER/Shadow باقی ماند.

## نتیجه مهم فصل
خود راهنمای فصل تأکید می‌کند که deep learning در بخش محدودی از شواهد کتاب برتری روشن دارد؛ مدل‌های ساده توالی و baselineهای جدولی اغلب رقابتی می‌مانند. بنابراین پیچیدگی باید با آزمون همسان و تکرارشونده توجیه شود.

## مرحله بعد
فصل ۱۴: Latent Factor Models — PCA، eigenportfolios، IPCA، autoencoders و SDF؛ با کنترل point-in-time و جلوگیری از نشت اطلاعات.
