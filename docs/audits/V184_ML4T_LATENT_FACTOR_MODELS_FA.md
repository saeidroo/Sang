# V184 — Latent Factor Models (ML4T Chapter 14)

تاریخ: 2026-11-21

## منبع و سورس واقعی بررسی‌شده
منبع اصلی فصل ۱۴ از مخزن رسمی Stefan Jansen:
- `01_pca_equity_sectors.py`: correlation-PCA، bootstrap بلوکی، تطبیق sign/order و rolling PCA.
- `02_eigenportfolios.py`: eigenportfolio، تحلیل sector exposure، hierarchical PCA، residual diagnostics و covariance دو‌سرعته.
- `03_yield_curve_decomposition.py`: تجزیه منحنی بازده و تفسیر level/slope/curvature.
- `04_ipca.py`: بازیابی زیر‌فضای عامل با داده مصنوعی و alternating least squares.
- `05_rp_pca.py`: sweep وزن pricing-error و تفکیک fit از reconstruction.
- `06_conditional_autoencoder.py`: شبکه beta مشروط به characteristics، شبکه factor و ensemble.
- `07_stochastic_discount_factor.py`: آموزش adversarial بین portfolio-weight و moment network.
- `08_supervised_autoencoder.py`: bottleneck مشترک، reconstruction و سرهای پیش‌بینی، purge و embargo.
- `09_case_study_insights.py`: registry coverage، مقایسه IC و paired comparison روی کلیدهای timestamp-entity یکسان.

راهنمای فصل، تفاوت هدف covariance explanation و pricing را محور اصلی قرار می‌دهد. نوت‌بوک‌ها نیز تأکید می‌کنند که bootstrap برای وابستگی زمانی، تطبیق componentها، و مقایسه روی نمونه‌های یکسان ضروری است.

## ۴۲ قاعده عملی افزوده‌شده
1. تمایز عامل توضیح‌دهنده کوواریانس از عامل قیمت‌گذاری‌شده؛ واریانس توضیح‌داده‌شده بالا لزوماً پیش‌بینی بازده نیست.
2. انتخاب آگاهانه covariance-PCA یا correlation-PCA؛ استانداردسازی هدف اقتصادی را تغییر می‌دهد.
3. fit کردن scaler و PCA فقط در پنجره آموزش برای کاربرد پیش‌بینی.
4. تعیین تعداد عامل با چند معیار و نه آستانه ثابت واریانس.
5. عدم یکی‌گرفتن elbow نمودار با تعداد عوامل priced.
6. کنترل نویز کوواریانس وقتی بُعد دارایی نسبت به طول تاریخ بزرگ است.
7. مقایسه shrinkage/structured covariance با covariance خام در هدف ریسک یکسان.
8. bootstrap بلوکی برای حفظ وابستگی زمانی.
9. تطبیق sign و ترتیب مؤلفه‌ها قبل از مقایسه bootstrap.
10. تشخیص sign flip از چرخش واقعی زیرفضای عامل.
11. مقایسه projection/subspace وقتی eigenvalueها نزدیک‌اند.
12. پایش rolling loading similarity، eigenvalue gap و سهم واریانس.
13. بارگذاری با فاصله اطمینان شامل صفر، شناسایی ضعیف دارد.
14. تعیین gross normalization، leverage، short constraints و rebalance برای eigenportfolio.
15. گزارش gross/net exposure، concentration، turnover، liquidity و sector bets.
16. تفکیک factor risk decomposition از alpha generation.
17. بررسی residualها برای ساختار مقطعی و persistence باقیمانده.
18. استفاده از hierarchical PCA فقط با منطق گروه‌بندی مستند و مقایسه با global PCA.
19. تعریف دو پنجره سریع/کند covariance و ترکیب point-in-time.
20. ممنوعیت استفاده از آینده در covariance، loadings، factor count و normalization.
21. تفسیر yield-curve PCs پس از کنترل maturity، واحد، missing tenor و level/change.
22. تبدیل عامل منحنی بازده به DV01/key-rate hedge و سنجش residual hedge.
23. در IPCA، characteristics تعیین‌کننده exposureهای متغیر با زمان‌اند.
24. fit تمام preprocessing و ALS در هر training fold؛ synthetic recovery برای صحت‌سنجی.
25. factor count و انتخاب characteristic در IPCA جزو model selection است.
26. در RP-PCA، sweep وزن pricing error و گزارش جداگانه دو هدف.
27. سنجش ارزش افزوده latent factor نسبت به characteristics و baselineهای linear/GBM.
28. طراحی test assets تعیین می‌کند چه pricing errorهایی قابل مشاهده‌اند.
29. توجه به rotation/sign/scale ambiguity و مقایسه invariant subspace.
30. تفکیک reconstruction loss از forward ranking skill در CAE.
31. انتخاب checkpoint فقط با validation زمانی، purge و embargo.
32. میانگین‌گیری ensemble در سطح asset prediction، نه raw loadingهای دارای rotation متفاوت.
33. سنجش حساسیت به seed و local minima با ensemble.
34. در adversarial SDF، تفکیک pricing error و factor Sharpe از rank IC.
35. کنترل پایداری adversarial optimization، ظرفیت moment network و seed.
36. تفکیک reconstruction و prediction head در supervised autoencoder.
37. block-bootstrap برای labelهای هم‌پوشان و paired comparison روی timestamp-asset یکسان.
38. خواندن confidence interval پیش از رتبه‌بندی مدل‌ها.
39. پوشش ثبت‌شده هر estimator را گزارش کن؛ نبود run امتیاز صفر یا شکست نیست.
40. عامل latent فقط با ارزش افزوده تکرارشونده، پایدار و net-of-cost مجاز به اثرگذاری می‌شود.
41. جداسازی Stage 1 factor estimation، Stage 2 premium forecasting و Stage 3 exposure combination.
42. نتایج بازارهای خارجی فقط شواهد روش‌شناختی‌اند و loadings/premiums آن‌ها به بازار ایران منتقل فرض نمی‌شوند.

## جمع‌بندی تصمیمی
- PCA برای ساختار ریسک و covariance مفید است؛ به‌تنهایی سیگنال خرید/فروش تولید نمی‌کند.
- IPCA و CAE می‌توانند exposure را به characteristics مشروط کنند؛ RP-PCA هدف pricing را وارد می‌کند؛ SDF مستقیماً pricing moments را هدف می‌گیرد.
- معیار اصلی پذیرش، reconstruction یا explained variance نیست؛ ارزش افزوده پیش‌بینی خارج از نمونه و پس از هزینه است.
- در مقایسه مدل‌ها، sample coverage و تاریخ‌های مشترک باید دقیقاً همسان باشند.

## وضعیت TradingAI
- فقط ۴۲ اصل آموزشی به curriculum مشترک اضافه شد.
- هیچ PCA/IPCA/CAE/SDF runtime model ساخته یا فعال نشد.
- هیچ آموزش یا benchmark روی داده TradingAI انجام نشد.
- هیچ سیگنال، امتیاز، ریسک یا سفارشی تغییر نکرد؛ PAPER/Shadow پابرجاست.
- این ثبت آموزشی به‌تنهایی اثبات نمی‌کند که runtime مغزها این دانش را در تصمیم واقعی مصرف می‌کنند.

## مرحله بعد
فصل ۱۵ — Causal Machine Learning: Double Machine Learning، اثر رویداد و causal discovery؛ با تمرکز بر confounding، leakage و محدودیت ادعای علیت.
