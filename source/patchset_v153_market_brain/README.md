# V23.0.153 market feeds + historical brain hotfix

This branch contains a patch set for the V23.0.153 UI Stage 2 source archive. The archive's internal root folder is named `TradingSignalAIPro_V23.0.152_AUDIT`; keep that folder name when applying the patch.

## Apply on a clean source tree

1. Extract the original V23.0.153 ZIP into a clean folder.
2. Download all `.patch.gz` files in this folder, preserving their numeric prefixes.
3. Decompress them to `.patch` files, then run `git apply --check` and `git apply` in numeric order from the project root.

Python one-liner to decompress on Windows PowerShell (run from the project root after downloading the patch files into `hotfix`):

```powershell
python -c "import gzip,pathlib; p=pathlib.Path('hotfix'); [(p/(f.stem)).write_bytes(gzip.decompress(f.read_bytes())) for f in sorted(p.glob('*.patch.gz'))]"
```

Check and apply:

```powershell
Get-ChildItem .\hotfix\*.patch | Sort-Object Name | ForEach-Object { git apply --check $_.FullName; if ($LASTEXITCODE -ne 0) { throw ('Patch check failed: ' + $_.Name) } }
Get-ChildItem .\hotfix\*.patch | Sort-Object Name | ForEach-Object { git apply $_.FullName; if ($LASTEXITCODE -ne 0) { throw ('Patch apply failed: ' + $_.Name) } }
```

Do not apply to a tree that already contains these changes. The full fixed source ZIP is also supplied separately with this change.

## What changes

- Adds fallback sources for gold and WTI/Brent cards; shows provider, timestamp, delayed/proxy/stale state rather than presenting stale data as live.
- Adds gold, silver, WTI and Brent archive targets, expands historical fetch fallbacks, and retains strict OHLCV validation.
- Triggers/coalesces another historical-brain scan after usable 1h candles arrive.
- Changes archive candle loading to per-symbol quotas, preventing one early symbol from exhausting a shared global limit.
- Makes brain service state and archive/backfill progress explicit; 100% is only reported after a successful scan with valid historical symbols/candles.
- Adds/updates focused tests and a Persian fix report.

## Verification

- Python compileall: passed.
- JavaScript syntax checks for `frontend/app.js` and `frontend/market-glance.js`: passed.
- Focused test suite: 43 passed.
- Full repository suite: not confirmed in the offline environment because Flask was not installed and package installation could not reach the network; one broader run also hit the execution timeout.
- Live third-party feed connectivity and optional API-key providers were not verified from this environment.

Optional keys: `TWELVEDATA_API_KEY`, `ALPHAVANTAGE_API_KEY`, `CRYPTOCOMPARE_API_KEY`, `CMC_API_KEY`. Keyless fallbacks remain enabled where the provider permits them.

## Safety

No live orders are sent. No production database is migrated or modified. Strategy signals, weights, ranking, thresholds, position sizing and risk limits are unchanged. Paper-only behavior remains in force.
