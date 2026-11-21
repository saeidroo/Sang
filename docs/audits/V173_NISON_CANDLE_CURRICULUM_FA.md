# V173 — Nison Candlestick Curriculum (Shadow-only)

## Source basis
The supplied Steve Nison, *Japanese Candlestick Charting Techniques*, second edition PDF was inspected. Its contents pages enumerate candle construction, reversal patterns, stars, additional reversals, continuation patterns, doji, convergence with Western tools, and measured moves. Selected chapter pages were visually inspected, including the hammer/hanging-man criteria and context, hanging-man confirmation, and inverted-hammer confirmation.

This implementation is an original concise ruleset and detector, not a reproduction of the book. The PDF itself is not copied into the repository.

## Stored artifacts
- `source/education/nison_candlestick_curriculum.py`: source metadata, chapter/topic lesson map, concise rules, and OHLC evidence detector for hammer, hanging man, inverted hammer, shooting star, engulfing, dark-cloud cover, piercing, morning star and evening star.
- `source/education/test_nison_candlestick_curriculum.py`: deterministic unit tests.
- Every result has zero score/risk contribution and no trade instruction.
- The receiving brain supplies trend context; the detector does not appoint itself trend authority.

## Guardrails and limitations
- Only completed OHLC bars are analyzed.
- A reversal formation is a possible trend change, not proof of an opposite trend.
- Pattern location and preceding trend are required for directional classification.
- Confirmation status is separate from pattern recognition.
- No model weights, signal scores, ranking, risk, or paper/live execution are changed.
- This curriculum component is stored in GitHub but is not yet wired into every runtime brain. Runtime integration and cross-brain behavioral tests remain separate work.
- The detector currently implements a subset of the patterns in the book's contents; the remaining named formations are mapped as lessons but are not yet machine-detected.

## Verification
Run from this folder:
```bash
python -m unittest -v test_nison_candlestick_curriculum.py
python -m py_compile nison_candlestick_curriculum.py
```

## Source map (printed page numbers)
Ch. 3 candle construction 23–30; Ch. 4 reversals 31–60; Ch. 5 stars 61–80; Ch. 6 additional reversals 81–124; Ch. 7 continuation 125–154; Ch. 8 doji 155–172; Ch. 9 synthesis 173–180; Ch. 10–17 convergence and measured moves 187–266.

This is a first executable extraction, not a claim that every page or every named pattern has a detector.
