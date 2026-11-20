"""Stage 8: historical learning must not bridge archive gaps or bad candles."""
import sqlite3

from backend import market_brain as brain


def _db(path, rows):
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE candles (
        symbol TEXT, timeframe TEXT, t INTEGER, open REAL, high REAL,
        low REAL, close REAL, volume REAL)""")
    con.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)",
                    [(r[0], "1h", *r[1:]) for r in rows])
    con.commit()
    con.close()


def _flat_rows(symbol, start, count, price=100.0):
    return [(symbol, start + i * 3_600_000, price, price * 1.002,
             price * .998, price, 1000.0) for i in range(count)]


def test_historical_extreme_learning_does_not_bridge_missing_hour(tmp_path, monkeypatch):
    db = tmp_path / "candles.sqlite3"
    start = 1_700_000_000_000
    rows = _flat_rows("GAPUSDT", start, 30)
    # A 24-hour pump-like run begins after a missing 7-hour interval.
    post_start = start + 37 * 3_600_000
    for i in range(30):
        price = 100.0 if i < 2 else 100.0 + (20.0 * (i - 2) / 24.0)
        rows.append(("GAPUSDT", post_start + i * 3_600_000,
                     price, price * 1.002, price * .998, price, 1000.0))
    _db(db, rows)
    monkeypatch.setattr(brain, "HISTORY_DB_PATH", db)
    monkeypatch.setattr(brain, "FEEDBACK_DB_PATH", tmp_path / "feedback.sqlite3")

    result = brain.learn_historical_extremes(now=1_800_000_000)

    assert result["status"] == "completed"
    assert result["pump_events"] == 0
    assert result["gap_breaks"] == 1
    assert result["segments"] == 2
    assert result["candles"] == 60


def test_invalid_ohlc_rows_are_excluded_and_reported(tmp_path, monkeypatch):
    db = tmp_path / "candles.sqlite3"
    start = 1_700_000_000_000
    rows = _flat_rows("BADUSDT", start, 55)
    # high is below close: impossible OHLC candle.
    rows[35] = ("BADUSDT", rows[35][1], 100.0, 99.0, 98.0, 101.0, 1000.0)
    _db(db, rows)
    monkeypatch.setattr(brain, "HISTORY_DB_PATH", db)
    monkeypatch.setattr(brain, "FEEDBACK_DB_PATH", tmp_path / "feedback.sqlite3")

    result = brain.learn_historical_extremes(now=1_800_000_000)

    assert result["status"] == "completed"
    assert result["invalid_rows"] == 1
    assert result["gap_breaks"] == 1
    assert result["segments"] == 2
    assert result["candles"] == 54


def test_conflicting_duplicate_timestamp_is_removed_as_a_group(tmp_path, monkeypatch):
    db = tmp_path / "candles.sqlite3"
    start = 1_700_000_000_000
    rows = _flat_rows("DUPUSDT", start, 55)
    duplicate = list(rows[20])
    duplicate[5] = duplicate[5] + 0.5
    duplicate[3] = max(duplicate[3], duplicate[5])
    rows.extend([rows[20], tuple(duplicate)])
    _db(db, rows)
    monkeypatch.setattr(brain, "HISTORY_DB_PATH", db)
    monkeypatch.setattr(brain, "FEEDBACK_DB_PATH", tmp_path / "feedback.sqlite3")

    result = brain.learn_historical_extremes(now=1_800_000_000)

    assert result["status"] == "completed"
    assert result["duplicate_timestamp_groups"] == 1
    assert result["invalid_rows"] == 3
    assert result["candles"] == 54
    assert result["gap_breaks"] == 1


def test_exact_duplicate_timestamp_is_collapsed_without_invalidating_candle():
    start = 1_700_000_000_000
    rows = _flat_rows("EXACTUSDT", start, 3)
    rows.append(rows[1])
    segments, audit = brain._prepare_hourly_segments(rows)
    assert sum(map(len, segments)) == 3
    assert audit["duplicate_timestamp_groups"] == 1
    assert audit["invalid_rows"] == 0
    assert audit["gap_breaks"] == 0


def test_history_archive_connection_is_read_only(tmp_path, monkeypatch):
    db = tmp_path / "candles.sqlite3"
    _db(db, _flat_rows("READONLYUSDT", 1_700_000_000_000, 55))
    before = db.read_bytes()
    monkeypatch.setattr(brain, "HISTORY_DB_PATH", db)
    monkeypatch.setattr(brain, "FEEDBACK_DB_PATH", tmp_path / "feedback.sqlite3")

    result = brain.learn_historical_extremes(now=1_800_000_000)

    assert result["status"] == "completed"
    assert db.read_bytes() == before


def test_predict_does_not_join_analogs_across_missing_hour(tmp_path, monkeypatch):
    db = tmp_path / "candles.sqlite3"
    start = 1_700_000_000_000
    rows = _flat_rows("CURRENTUSDT", start, 30)
    rows.extend(_flat_rows("CURRENTUSDT", start + 37 * 3_600_000, 30))
    _db(db, rows)
    monkeypatch.setattr(brain, "HISTORY_DB_PATH", db)
    monkeypatch.setattr(brain, "FEEDBACK_DB_PATH", tmp_path / "feedback.sqlite3")
    latest_t = rows[-1][1]

    items = [{"symbol": "CURRENTUSDT"}]
    result = brain.predict(items, now=latest_t / 1000.0 + 3600)

    assert result["archive_quality"]["gap_breaks"] == 1
    assert result["archive_quality"]["segments"] == 2
    assert items[0]["brain_prediction"]["status"] == "few_historical_analogs"
    assert items[0]["brain_prediction"]["analogs"] == 0


def test_cache_hit_preserves_archive_quality_audit(tmp_path, monkeypatch):
    db = tmp_path / "candles.sqlite3"
    start = 1_700_000_000_000
    rows = _flat_rows("CACHEUSDT", start, 30)
    rows.extend(_flat_rows("CACHEUSDT", start + 35 * 3_600_000, 30))
    _db(db, rows)
    monkeypatch.setattr(brain, "HISTORY_DB_PATH", db)
    monkeypatch.setattr(brain, "FEEDBACK_DB_PATH", tmp_path / "feedback.sqlite3")

    first = brain.learn_historical_extremes(now=1_800_000_000)
    second = brain.learn_historical_extremes(now=1_800_000_001)

    assert first["gap_breaks"] == 1
    assert second["cache_hit"] is True
    assert second["gap_breaks"] == 1
    assert second["segments"] == 2
