import unittest
from nison_candlestick_curriculum import analyze_candles

def c(o,h,l,close): return {"open":o,"high":h,"low":l,"close":close}

class NisonCurriculumTests(unittest.TestCase):
    def test_hammer_after_decline(self):
        out=analyze_candles([c(12,13,10,11),c(11,11,8,10.5)],"down")
        self.assertEqual(out["evidence"][0]["pattern"],"hammer")
        self.assertIsNone(out["trade_instruction"])
        self.assertEqual(out["score_contribution"],0)
    def test_same_shape_after_rally_is_hanging_man(self):
        out=analyze_candles([c(10,12,9,11),c(11,11,8,10.5)],"up")
        self.assertEqual(out["evidence"][0]["pattern"],"hanging_man")
    def test_engulfing_requires_trend_context(self):
        rows=[c(10,11,8,9),c(8.5,12,8,11)]
        self.assertEqual(analyze_candles(rows,"down")["evidence"][0]["pattern"],"bullish_engulfing")
        self.assertEqual(analyze_candles(rows,"unknown")["evidence"],[])
    def test_invalid_ohlc_rejected(self):
        with self.assertRaises(ValueError): analyze_candles([c(10,9,8,11)],"down")
    def test_doji_is_neutral_advisory_evidence(self):
        out=analyze_candles([c(10,12,8,10.02)],"down")
        self.assertEqual(out["evidence"][0]["pattern"],"doji")
        self.assertEqual(out["evidence"][0]["direction"],"neutral")
        self.assertIsNone(out["trade_instruction"])
        self.assertEqual(out["score_contribution"],0)
        self.assertEqual(out["risk_contribution"],0)

    def test_spinning_top_is_neutral(self):
        out=analyze_candles([c(10,12,9,11)],"sideways")
        self.assertEqual(out["evidence"][0]["pattern"],"spinning_top")
        self.assertEqual(out["evidence"][0]["direction"],"neutral")

    def test_no_signal_or_risk_authority(self):
        out=analyze_candles([c(10,11,9,10)],"sideways")
        self.assertIsNone(out["trade_instruction"])
        self.assertEqual(out["score_contribution"],0)
        self.assertEqual(out["risk_contribution"],0)

if __name__=="__main__": unittest.main()
