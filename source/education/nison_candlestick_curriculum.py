"""Steve Nison-inspired candlestick evidence curriculum.

Concise original learning rules derived from the supplied book's structure
and inspected examples. This is not a reproduction of the book. Advisory only.
"""
from __future__ import annotations
from typing import Any, Dict, List, Sequence

SOURCE = {"author": "Steve Nison", "title": "Japanese Candlestick Charting Techniques",
          "edition": "Second Edition", "curriculum_id": "NISON_CANDLE_EVIDENCE_V1",
          "mode": "SHADOW_ADVISORY_ONLY"}

LESSONS = [
 {"chapter":3,"topic":"Candle construction","printed_pages":"23-30","rules":["Read open, high, low and close together.","Separate real body from upper and lower shadows.","Use only completed candles; the close is a completed-bar observation."]},
 {"chapter":4,"topic":"Reversal patterns","printed_pages":"31-60","patterns":["umbrella_lines","hammer","hanging_man","engulfing","dark_cloud_cover","piercing"],"rules":["A reversal pattern warns of a possible trend change, not a guaranteed opposite trend.","Interpret the pattern after identifying the preceding trend.","Use pattern extremes as nearby invalidation or support/resistance references.","A hanging man requires bearish confirmation; hammer body colour is secondary."]},
 {"chapter":5,"topic":"Stars","printed_pages":"61-80","patterns":["morning_star","evening_star","morning_doji_star","evening_doji_star","shooting_star","inverted_hammer"],"rules":["Evaluate a star relative to the preceding move.","The third candle completes the three-candle star formation.","An inverted hammer requires bullish follow-through; a shooting star is a top warning."]},
 {"chapter":6,"topic":"Additional reversal patterns","printed_pages":"81-124","patterns":["harami","harami_cross","tweezers","belt_hold","upside_gap_two_crows","three_black_crows","three_advancing_white_soldiers","three_mountains","three_rivers","counterattack_lines","dumpling_top","frypan_bottom","tower_top","tower_bottom"],"rules":["Inspect multi-candle pattern location and preceding move.","Repeated highs/lows and failed follow-through are contextual evidence.","Use nearby structure to judge whether market control has changed."]},
 {"chapter":7,"topic":"Continuation patterns","printed_pages":"125-154","patterns":["windows","tasuki","high_low_price_gapping_plays","gapping_side_by_side_white_lines","rising_three_methods","falling_three_methods","separating_lines"],"rules":["Candles can describe continuation as well as reversal.","A gap/window can later act as support or resistance.","Judge continuation patterns against the existing trend."]},
 {"chapter":8,"topic":"Doji","printed_pages":"155-172","patterns":["northern_doji","long_legged_doji","rickshaw_man","gravestone_doji","dragonfly_doji","tri_star"],"rules":["A doji describes a close near the open and signals balance/indecision.","A doji alone does not establish a reversal; location and subsequent price action matter."]},
 {"chapter":9,"topic":"Putting it all together","printed_pages":"173-180","rules":["Combine candle evidence with the broader chart rather than using it in isolation."]},
 {"chapter":10,"topic":"Candle clusters","printed_pages":"187-192","rules":["Read groups of candles as a sequence; avoid over-weighting one isolated bar."]},
 {"chapter":11,"topic":"Candles with trend lines","printed_pages":"193-212","rules":["Check candle evidence against trend-line breaks, holds, springs and upthrusts.","A failed break and a successful retest are different observations."]},
 {"chapter":12,"topic":"Candles with retracement levels","printed_pages":"213-216","rules":["Use retracement zones as context for candle reactions, not automatic signals."]},
 {"chapter":13,"topic":"Candles with moving averages","printed_pages":"217-224","rules":["Use moving averages as contextual trend references alongside candle evidence."]},
 {"chapter":14,"topic":"Candles with oscillators","printed_pages":"225-240","rules":["Compare candle evidence with RSI, stochastic and MACD context.","Indicator agreement is context, not proof or a standalone instruction."]},
 {"chapter":15,"topic":"Candles with volume","printed_pages":"241-248","rules":["Read volume as participation context alongside the price formation."]},
 {"chapter":16,"topic":"Measured moves","printed_pages":"249-262","rules":["Use box breakouts, swing targets, flags and pennants for price objectives; candle patterns do not supply targets by themselves."]},
 {"chapter":17,"topic":"East-West convergence","printed_pages":"263-266","rules":["Combine candle interpretation with Western technical tools and explicit price structure."]},
]

def _candle(row: Dict[str, Any]) -> Dict[str, float]:
    o,h,l,c=(float(row[k]) for k in ("open","high","low","close"))
    if h < max(o,c,l) or l > min(o,c,h) or h < l:
        raise ValueError("Invalid OHLC candle")
    return {"open":o,"high":h,"low":l,"close":c,"body":abs(c-o),
            "range":h-l,"upper":h-max(o,c),"lower":min(o,c)-l}

def _bull(x): return x["close"] > x["open"]
def _bear(x): return x["close"] < x["open"]
def _mid(x): return (x["open"]+x["close"])/2.0

def _result(name: str, direction: str, start: int, end: int, bars: Sequence[Dict[str,float]], confirmation: str, invalidation: float, note: str) -> Dict[str,Any]:
    nxt=bars[end+1] if end+1 < len(bars) else None
    confirmed=False
    if nxt is not None:
        confirmed = (nxt["close"] > max(bars[end]["open"],bars[end]["close"]) if direction=="bullish"
                     else nxt["close"] < min(bars[end]["open"],bars[end]["close"]))
    return {"pattern":name,"direction":direction,"formation_index":[start,end],
            "status":"CONFIRMED" if confirmed else "WAITING_FOR_CONFIRMATION",
            "confirmation_rule":confirmation,"invalidation_reference":invalidation,
            "context_note":note,"score_contribution":0,"risk_contribution":0,
            "trade_instruction":None,"source":SOURCE["curriculum_id"]}

def analyze_candles(rows: Sequence[Dict[str,Any]], trend: str="unknown") -> Dict[str,Any]:
    """Return latest eligible candle evidence, never a trade signal.

    trend is supplied by the receiving brain: up/down/sideways/unknown.
    """
    trend=str(trend).lower()
    if trend not in {"up","down","sideways","unknown"}:
        raise ValueError("trend must be up, down, sideways or unknown")
    bars=[_candle(r) for r in rows]
    evidence=[]
    for i,x in enumerate(bars):
        rng=x["range"]
        if rng<=0 or x["body"]<=0: continue
        small=x["body"]<=rng*0.35
        tiny_up=x["upper"]<=max(x["body"]*0.25,rng*0.03)
        tiny_low=x["lower"]<=max(x["body"]*0.25,rng*0.03)
        if small and x["lower"]>=2*x["body"] and tiny_up:
            if trend=="down": evidence.append(_result("hammer","bullish",i,i,bars,"Look for bullish follow-through or a structural hold.",x["low"],"After a decline; body colour is secondary."))
            elif trend=="up": evidence.append(_result("hanging_man","bearish",i,i,bars,"Require a later close below the real body.",x["low"],"After a rally; warning, not an automatic short."))
        if small and x["upper"]>=2*x["body"] and tiny_low:
            if trend=="down": evidence.append(_result("inverted_hammer","bullish",i,i,bars,"Require a later close above the real body.",x["low"],"Bottom-reversal candidate after a decline."))
            elif trend=="up": evidence.append(_result("shooting_star","bearish",i,i,bars,"Look for bearish follow-through or structural rejection.",x["high"],"Top-reversal warning after a rally."))
        if i>=1:
            p=bars[i-1]
            if _bear(p) and _bull(x) and x["open"]<=p["close"] and x["close"]>=p["open"] and trend=="down":
                evidence.append(_result("bullish_engulfing","bullish",i-1,i,bars,"Check follow-through and whether the pattern low holds.",min(p["low"],x["low"]),"Bullish body engulfs the prior bearish body."))
            if _bull(p) and _bear(x) and x["open"]>=p["close"] and x["close"]<=p["open"] and trend=="up":
                evidence.append(_result("bearish_engulfing","bearish",i-1,i,bars,"Check follow-through and whether the pattern high holds.",max(p["high"],x["high"]),"Bearish body engulfs the prior bullish body."))
            if _bull(p) and _bear(x) and x["open"]>p["high"] and x["close"]<_mid(p) and x["close"]>p["open"] and trend=="up":
                evidence.append(_result("dark_cloud_cover","bearish",i-1,i,bars,"Look for bearish continuation.",max(p["high"],x["high"]),"Second candle penetrates the prior bullish body."))
            if _bear(p) and _bull(x) and x["open"]<p["low"] and x["close"]>_mid(p) and x["close"]<p["open"] and trend=="down":
                evidence.append(_result("piercing_pattern","bullish",i-1,i,bars,"Look for bullish continuation.",min(p["low"],x["low"]),"Second candle recovers above the midpoint of the prior bearish body."))
        if i>=2:
            a,b=bars[i-2],bars[i-1]
            star=b["body"]<=max(a["body"],x["body"])*0.5
            if trend=="down" and _bear(a) and star and _bull(x) and x["close"]>_mid(a):
                evidence.append(_result("morning_star","bullish",i-2,i,bars,"Third candle completes the formation; assess nearby support.",min(a["low"],b["low"],x["low"]),"Three-candle bottom-reversal formation."))
            if trend=="up" and _bull(a) and star and _bear(x) and x["close"]<_mid(a):
                evidence.append(_result("evening_star","bearish",i-2,i,bars,"Third candle completes the formation; assess nearby resistance.",max(a["high"],b["high"],x["high"]),"Three-candle top-reversal formation."))
    if not evidence:
        return {"curriculum":SOURCE,"trend_context":trend,"evidence":[],"interpretation":"NO_CANDLE_PATTERN_DETECTED","trade_instruction":None,"score_contribution":0,"risk_contribution":0}
    latest=max(evidence,key=lambda e:e["formation_index"][1])
    return {"curriculum":SOURCE,"trend_context":trend,"evidence":[latest],"interpretation":latest["status"],"trade_instruction":None,"score_contribution":0,"risk_contribution":0,"safety":"Advisory evidence only; receiving brain retains its own decision."}
