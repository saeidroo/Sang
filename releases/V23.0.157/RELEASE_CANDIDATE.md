# V23.0.157 — Multi-timeframe Market Structure (release candidate)

**Repository:** `saeidroo/Sang`  
**Reference source branch:** `v23.0.153-rebuild`  
**Candidate artifact:** `V23.0.157_MULTITIMEFRAME_STRUCTURE_PATCH.zip`  
**SHA-256:** `5cefb785aed9fe22161b8af24a49c19b575aa9bda6920916ff8a2af5d96342f6`

## Scope recorded from the supplied patch

The candidate adds a research-only multi-timeframe structure summary for closed 1d, 4h, 1h, 15m and 5m candles. It reuses confirmed swing pivots and existing BOS/CHOCH evidence and publishes structural context through the existing Knowledge Bus.

It is explicitly shadow-only: it must not change signal scores, model weights, ranking, risk controls, Paper execution or real-order settings.

## Patch inventory

The ZIP contains 10 entries:
- `backend/api.py`
- `backend/market_structure_advanced.py`
- `frontend/app.js`
- `frontend/index.html`
- `main.py`
- `README.md`
- `tests/test_v23_0_157_multi_timeframe_structure.py`
- `tests/test_compact_ui_contract.py`
- `tests/test_v23_0_119_autopilot_ui.py`
- `BUILD_REPORT_V23.0.157_MULTITIMEFRAME_STRUCTURE_FA.md`

## Validation reported with the candidate

- Python compilation: passed.
- `node --check frontend/app.js`: passed.
- Focused multi-timeframe, historical validation, candle, BOS/CHOCH, AutoPilot and UI checks: 40 passed.
- Full-suite collection was not clean in the build environment: 1,382 tests were collected, but 10 test modules failed during collection because Flask was unavailable. Full-suite success is therefore **not established**.
- The user's live archive and exchange feeds were not tested in the build environment.

## Repository synchronization status — important

This commit records the candidate metadata and checksum only. The ZIP itself and its source files have **not** been uploaded by this commit.

The repository currently has a V23.0.153 source-archive branch and a separate Stage 8 draft PR based on V23.0.152. The V23.0.154–V23.0.156 source snapshots are not present as verified repository refs in the current audit. Therefore the V23.0.157 patch has not been declared directly applicable to the V23.0.153 archive, and no files in `main` have been replaced.

Before importing the actual patch, restore/commit the exact V23.0.156 base (or prove compatibility by comparing the patch against that base), then apply only the listed changed files and run the focused regression suite.

**Safety:** PAPER ONLY. No real orders. No strategy scores, weights, thresholds, ranking or risk limits changed by this recorded candidate.
