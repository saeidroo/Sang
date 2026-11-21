# V174 — Nison source extraction: candle construction

Source: Steve Nison, *Japanese Candlestick Charting Techniques*, Second Edition. Uploaded scan: `Steve_Nison_Japanese_Candlestick_Charting_Techniques_Prentice_Hall.pdf` (298 pages; image-based scan).

## Work completed
Rendered and OCR-checked PDF pages 36–39 (printed pages 25–28), within Chapter 3, “Constructing the Candlestick Lines”.

## Extracted lessons (original concise paraphrase)
- The real body spans open to close. Its direction tells whether the period closed above or below its open.
- The shadows extend from the body to the high and low.
- A long rising body depicts buyer control for that completed interval; a long falling body depicts seller control.
- Body size is a momentum clue. Expanding falling bodies during a decline indicate increasing bearish momentum.
- A spinning top is a small-body warning that directional control may be weakening; one candle alone is tentative.
- A doji has equal or nearly equal open and close and represents indecision; its meaning depends on context.
- Candle interpretation applies to intraday, daily and weekly intervals, but each candle belongs to its own interval.
- A candle warning near support or resistance gains structural context.

## Code changes
Existing `source/education/nison_candlestick_curriculum.py` now exposes `INSPECTED_LESSONS[3]` with the extracted details and evidence pages. The analyzer now reports doji and spinning-top observations as neutral advisory evidence. These observations carry no score, no risk authority and no trade instruction.

## Boundaries
This is a partial extraction of Chapter 3, not a claim that the full book has been OCR-processed. Other chapter mappings remain topic outlines until their actual pages are inspected. The analyzer remains shadow/advisory only; no live trading or autonomous order action is enabled.


## V175 continuation — printed page 29
The next scanned page (PDF page 40, printed page 29) was visually inspected. Additional original paraphrases were added to `INSPECTED_LESSONS[3]`:
- The open is an early and provisional view of the market battle.
- The close is a pivotal completed price and may be used to confirm a breakout beyond an important chart level.
- Some technical systems, including moving-average systems, calculate from closing prices.
- The author labels unusually large orders intended to affect the close a “night attack” and similar orders at the open a “morning attack”.
- Pattern names act as memory aids for market emotion; the page characterizes dark-cloud cover and evening star as bearish, and morning star as bullish.

The source uses the “attack” wording as terminology/metaphor; the code stores it as an educational note, not as a measurable detector. Two tests were added for neutral doji and spinning-top advisory output. Tests have been committed but not executed in this environment.
