# V23.0.165 — Cross-brain recorded failure diagnosis

- Branch: `fix/v156-cross-timeframe-brain-bus`
- Artifact: `TradingSignalAIPro_V23.0.165_CROSS_BRAIN_FAILURE_DIAGNOSIS.zip`
- SHA256: `91b14184825012cb59be1647d9b466aef7b8a27a6103453a932205743d969f61`
- `backend/market_brain.py`: matured PAPER outcome packets now include already-recorded failure/neutral labels grouped by symbol, signal type and horizon.
- `backend/brain.py`: peer historical review preserves those diagnosis fields.
- No cause is inferred from raw outcomes; each label is marked `observed_label_not_inferred`. Current labels are limited to recorded categories such as `opposite_move` and `no_follow_through`.
- No score, confidence, risk, signal, or order-execution behavior is changed. No new brain, module, database or table. PAPER ONLY retained.
- py_compile: PASS.
- Related targeted tests: 45 passed.
- Full project suite was not run.
- This commit is the audit report only; it does not synchronize the complete ZIP into repository source paths. `main` remains untouched.
