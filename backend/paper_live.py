"""V23.0.13 live-market-data paper trading with ATR-aware risk and Funding accounting.

Uses public exchange ticker endpoints only. It NEVER submits exchange orders,
reads private balances, or needs API keys. Fills and PnL are simulated locally.
"""
from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import time
import contextvars
from functools import wraps
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.data import SESSION
from backend.portfolio_risk import (aggregate_open_risk, size_for_risk,
                                    validate_structure_room)
from backend.trade_contract import (atr_bracket as shared_atr_bracket,
                                    TRADE_HORIZON_BARS, timeframe_seconds)
from backend.funding import (VERSION as FUNDING_VERSION, fetch_funding_history, funding_cashflow,
                             funding_history_complete, quantity_at_settlement)
from backend.execution_model import execution_costs, fill_price
from backend.bracket_execution import evaluate_bracket_candle

VERSION = "paper-live-risk-v13-funding-pro-rata-partial-exits"

# A process lease protects the PAPER ledger across processes. Mutating entry
# points also enforce it themselves so non-Flask callers cannot bypass the API
# boundary. AutoPilot explicitly enters this context only around its own work.
_PAPER_WRITER_AUTHORIZED = contextvars.ContextVar("paper_writer_authorized", default=False)


@contextmanager
def authorized_paper_writer():
    token = _PAPER_WRITER_AUTHORIZED.set(True)
    try:
        yield
    finally:
        _PAPER_WRITER_AUTHORIZED.reset(token)


def _paper_ledger_writer_guard(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if not _PAPER_WRITER_AUTHORIZED.get():
            from backend import paper_process_lease
            lease = paper_process_lease.lease_status(_db_path())
            if lease.get("held"):
                raise RuntimeError("paper_ledger_owned_by_autopilot")
        return func(*args, **kwargs)
    return wrapped

LEARNING_VERSION = "paper-trade-outcome-v2-context"
VALID_TIMEFRAMES = ("5m", "15m", "30m", "1h", "4h", "1d")

# Fixed, conservative preset requested by the operator. Read-only from the UI.
SETTINGS = {
    "mode": "PAPER_ONLY_LIVE_MARKET_DATA",
    "initial_balance": 1_000.0,
    "currency": "USDT",
    "default_exchange": "auto",
    "fallback_order": ["binance", "bybit", "okx", "gateio", "mexc", "bitget"],
    "default_market": "spot",
    "default_symbol": "BTCUSDT",
    "quote_refresh_seconds": 10,
    "cross_exchange_validation_enabled": True,
    "cross_exchange_min_sources": 2,
    "cross_exchange_max_deviation_pct": 1.0,
    "risk_per_trade_pct": 0.5,
    "max_position_notional_pct": 20.0,
    "max_open_positions": 3,
    "stop_loss_pct": 1.5,
    "take_profit_pct": 3.0,
    "max_daily_loss_pct": 3.0,
    "max_drawdown_pct": 10.0,
    # Aggregate stop-risk limits across all open paper positions.
    "max_portfolio_risk_pct": 2.0,
    "max_spot_risk_pct": 1.5,
    "max_perp_risk_pct": 1.0,
    "max_directional_risk_pct": 1.5,
    "fee_bps_per_side": 10.0,
    "slippage_bps_per_side": 5.0,
    "spread_bps_full": 2.0,
    "impact_bps_per_1000_usdt": 0.5,
    "max_impact_bps_per_side": 20.0,
    "leverage": 1,
    "private_api_keys_required": False,
    "real_orders_enabled": False,
}

EXCHANGE_NAMES = {
    "binance": "Binance", "bybit": "Bybit", "okx": "OKX",
    "gateio": "Gate.io", "mexc": "MEXC", "bitget": "Bitget",
}
SYMBOL_RE = re.compile(r"^[A-Z0-9]{3,24}$")
_CACHE: dict[tuple[str, str, str], tuple[float, dict]] = {}
_CACHE_TTL = 3.0
QUOTE_MAX_AGE_SECONDS = 60.0
QUOTE_MAX_FUTURE_SKEW_SECONDS = 5.0


def _db_path() -> Path:
    p = Path(os.getenv("TRADING_AI_PAPER_LIVE_DB", str(Path.home() / ".trading_ai_models" / "paper_live.sqlite3"))).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@contextmanager
def _connect():
    """Open a short-lived SQLite connection with consistent durability settings.

    sqlite3.Connection's context manager commits/rolls back but does not close
    the connection. Wrapping it here guarantees closure on every code path.
    """
    conn = sqlite3.connect(str(_db_path()), timeout=30.0)
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA foreign_keys=ON")
        # In WAL mode FULL asks SQLite to sync the WAL at each commit. This
        # favors crash durability for the paper ledger over write throughput.
        conn.execute("PRAGMA synchronous=FULL")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(*, backfill_learning: bool = True) -> None:
    with _connect() as c:
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("""CREATE TABLE IF NOT EXISTS paper_live_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opened_at REAL NOT NULL,
            symbol TEXT NOT NULL,
            market TEXT NOT NULL,
            exchange TEXT NOT NULL,
            requested_exchange TEXT NOT NULL DEFAULT 'auto',
            side TEXT NOT NULL,
            quantity REAL NOT NULL,
            notional REAL NOT NULL,
            reference_entry REAL NOT NULL,
            entry_fill REAL NOT NULL,
            entry_fee REAL NOT NULL,
            execution_costs_json TEXT NOT NULL DEFAULT '{}',
            stop_price REAL NOT NULL,
            target_price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPEN',
            closed_at REAL,
            reference_exit REAL,
            exit_fill REAL,
            exit_fee REAL,
            gross_pnl REAL,
            net_pnl REAL,
            exit_reason TEXT,
            last_price REAL,
            last_price_at REAL,
            settings_json TEXT NOT NULL
        )""")
        # Migrate databases created by an earlier V22.7.9 preview.
        cols = {row[1] for row in c.execute("PRAGMA table_info(paper_live_trades)").fetchall()}
        if "execution_costs_json" not in cols:
            c.execute("ALTER TABLE paper_live_trades ADD COLUMN execution_costs_json TEXT NOT NULL DEFAULT '{}'")
        if "requested_exchange" not in cols:
            c.execute("ALTER TABLE paper_live_trades ADD COLUMN requested_exchange TEXT NOT NULL DEFAULT 'auto'")
            c.execute("UPDATE paper_live_trades SET requested_exchange=exchange WHERE requested_exchange='auto'")
        # Learning-ready context: each simulated trade keeps its timeframe and
        # entry provenance so a future exchange adapter can consume the same contract.
        cols = {row[1] for row in c.execute("PRAGMA table_info(paper_live_trades)").fetchall()}
        timeframe_was_missing = "timeframe" not in cols
        if timeframe_was_missing:
            c.execute("ALTER TABLE paper_live_trades ADD COLUMN timeframe TEXT NOT NULL DEFAULT 'unknown'")
        if "entry_context_json" not in cols:
            c.execute("ALTER TABLE paper_live_trades ADD COLUMN entry_context_json TEXT NOT NULL DEFAULT '{}'")
        if "entry_idempotency_key" not in cols:
            c.execute("ALTER TABLE paper_live_trades ADD COLUMN entry_idempotency_key TEXT")
        if "funding_total" not in cols:
            c.execute("ALTER TABLE paper_live_trades ADD COLUMN funding_total REAL NOT NULL DEFAULT 0")
        if "funding_event_count" not in cols:
            c.execute("ALTER TABLE paper_live_trades ADD COLUMN funding_event_count INTEGER NOT NULL DEFAULT 0")
        if "funding_status" not in cols:
            c.execute("ALTER TABLE paper_live_trades ADD COLUMN funding_status TEXT NOT NULL DEFAULT 'NOT_APPLICABLE'")
        if "funding_error" not in cols:
            c.execute("ALTER TABLE paper_live_trades ADD COLUMN funding_error TEXT")
        if "funding_checked_at" not in cols:
            c.execute("ALTER TABLE paper_live_trades ADD COLUMN funding_checked_at REAL")
        # Persist trailing state so an AutoPilot restart cannot forget the
        # favourable price extreme already observed for an open PAPER trade.
        if "trailing_peak_price" not in cols:
            c.execute("ALTER TABLE paper_live_trades ADD COLUMN trailing_peak_price REAL")
        if "trailing_active" not in cols:
            c.execute("ALTER TABLE paper_live_trades ADD COLUMN trailing_active INTEGER NOT NULL DEFAULT 0")
        # Durable OHLC replay cursor. NULL means no closed candle has yet been
        # committed for this trade; updates are committed with any resulting exit.
        if "replay_last_candle_open_ms" not in cols:
            c.execute("ALTER TABLE paper_live_trades ADD COLUMN replay_last_candle_open_ms INTEGER")
        if "replay_status" not in cols:
            c.execute("ALTER TABLE paper_live_trades ADD COLUMN replay_status TEXT NOT NULL DEFAULT 'PENDING'")
        if "replay_error" not in cols:
            c.execute("ALTER TABLE paper_live_trades ADD COLUMN replay_error TEXT")
        c.execute("UPDATE paper_live_trades SET funding_status='PENDING' WHERE market='perp' AND funding_status='NOT_APPLICABLE'")
        c.execute("""CREATE TABLE IF NOT EXISTS paper_funding_events (
            trade_id INTEGER NOT NULL,
            settlement_ts_ms INTEGER NOT NULL,
            exchange TEXT NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            funding_rate REAL NOT NULL,
            mark_price REAL,
            event_notional REAL NOT NULL,
            notional_basis TEXT NOT NULL,
            position_quantity REAL NOT NULL DEFAULT 0,
            partial_exited_quantity REAL NOT NULL DEFAULT 0,
            cashflow REAL NOT NULL,
            source TEXT NOT NULL DEFAULT 'public_funding_history',
            created_at REAL NOT NULL,
            PRIMARY KEY(trade_id, settlement_ts_ms),
            FOREIGN KEY(trade_id) REFERENCES paper_live_trades(id)
        )""")
        funding_cols = {row[1] for row in c.execute("PRAGMA table_info(paper_funding_events)").fetchall()}
        if "position_quantity" not in funding_cols:
            c.execute("ALTER TABLE paper_funding_events ADD COLUMN position_quantity REAL NOT NULL DEFAULT 0")
        if "partial_exited_quantity" not in funding_cols:
            c.execute("ALTER TABLE paper_funding_events ADD COLUMN partial_exited_quantity REAL NOT NULL DEFAULT 0")
        c.execute("CREATE INDEX IF NOT EXISTS idx_paper_funding_trade ON paper_funding_events(trade_id, settlement_ts_ms)")
        c.execute("""CREATE TABLE IF NOT EXISTS paper_partial_exits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id INTEGER NOT NULL,
            idempotency_key TEXT NOT NULL,
            created_at REAL NOT NULL,
            quantity REAL NOT NULL,
            reference_exit REAL NOT NULL,
            exit_fill REAL NOT NULL,
            entry_fee_allocated REAL NOT NULL,
            exit_fee REAL NOT NULL,
            gross_pnl REAL NOT NULL,
            net_pnl REAL NOT NULL,
            reason TEXT NOT NULL DEFAULT 'PARTIAL_MANUAL',
            UNIQUE(trade_id, idempotency_key),
            FOREIGN KEY(trade_id) REFERENCES paper_live_trades(id)
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_partial_exit_trade ON paper_partial_exits(trade_id, id)")
        # One durable idempotency key can create at most one simulated trade,
        # including after the original trade is closed or the process restarts.
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_paper_live_entry_idempotency "
                  "ON paper_live_trades(entry_idempotency_key) WHERE entry_idempotency_key IS NOT NULL")
        c.execute("CREATE INDEX IF NOT EXISTS idx_paper_live_status ON paper_live_trades(status, id)")
        # Cover frequent open-position scans, daily PnL/report windows, and
        # funding reconciliation without changing trade semantics.
        c.execute("CREATE INDEX IF NOT EXISTS idx_paper_live_open_symbol_market "
                  "ON paper_live_trades(status, symbol, market, id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_paper_live_closed_at "
                  "ON paper_live_trades(status, closed_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_paper_live_funding_status "
                  "ON paper_live_trades(status, market, funding_status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_paper_funding_settlement "
                  "ON paper_funding_events(settlement_ts_ms)")
        c.execute("""CREATE TABLE IF NOT EXISTS paper_learning_events (
            trade_id INTEGER PRIMARY KEY,
            closed_at REAL NOT NULL,
            symbol TEXT NOT NULL,
            market TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            exchange TEXT NOT NULL,
            side TEXT NOT NULL,
            exit_reason TEXT,
            outcome INTEGER NOT NULL,
            net_pnl REAL NOT NULL,
            return_pct REAL NOT NULL,
            duration_seconds REAL NOT NULL,
            notional REAL NOT NULL,
            gross_pnl REAL NOT NULL,
            total_fees REAL NOT NULL,
            entry_fill REAL NOT NULL,
            exit_fill REAL NOT NULL,
            context_json TEXT NOT NULL DEFAULT '{}'
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_paper_learning_scope ON paper_learning_events(symbol,market,timeframe,side,closed_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_paper_learning_closed_at "
                  "ON paper_learning_events(closed_at DESC, trade_id DESC)")
        c.execute("""CREATE TABLE IF NOT EXISTS paper_learning_profiles (
            scope_key TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            market TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            side TEXT NOT NULL,
            sample_count INTEGER NOT NULL,
            win_count INTEGER NOT NULL,
            loss_count INTEGER NOT NULL,
            win_rate_pct REAL NOT NULL,
            avg_net_return_pct REAL NOT NULL,
            expectancy_usdt REAL NOT NULL,
            profit_factor REAL,
            total_net_pnl REAL NOT NULL,
            avg_duration_seconds REAL NOT NULL,
            learning_state TEXT NOT NULL,
            updated_at REAL NOT NULL
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS paper_live_meta (
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS paper_equity_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at REAL NOT NULL,
            equity REAL NOT NULL,
            peak_equity REAL NOT NULL,
            drawdown_pct REAL NOT NULL,
            realized_pnl REAL NOT NULL,
            unrealized_pnl REAL NOT NULL,
            open_positions INTEGER NOT NULL,
            quote_health TEXT NOT NULL,
            funding_health TEXT NOT NULL
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_paper_equity_history_time ON paper_equity_history(recorded_at DESC)")
        # Persist the paper account's starting balance. Older V22.7.9 databases
        # only stored peak_equity; migrate their peak baseline from 10,000 USDT
        # to the newly requested 1,000 USDT while preserving all trade history.
        peak_before = c.execute("SELECT value FROM paper_live_meta WHERE key='peak_equity'").fetchone()
        saved_initial = c.execute("SELECT value FROM paper_live_meta WHERE key='initial_balance'").fetchone()
        if saved_initial is None:
            legacy_initial = 10_000.0 if peak_before is not None else float(SETTINGS["initial_balance"])
            c.execute("INSERT INTO paper_live_meta(key,value) VALUES('initial_balance',?)", (str(SETTINGS["initial_balance"]),))
            if legacy_initial != float(SETTINGS["initial_balance"]):
                realized_row = c.execute("SELECT COALESCE(SUM(net_pnl),0) FROM paper_live_trades WHERE status='CLOSED'").fetchone()
                migrated_equity = float(SETTINGS["initial_balance"]) + float(realized_row[0] or 0.0)
                migrated_peak = max(float(SETTINGS["initial_balance"]), migrated_equity)
                c.execute("INSERT INTO paper_live_meta(key,value) VALUES('peak_equity',?) "
                          "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(migrated_peak),))
            else:
                c.execute("INSERT OR IGNORE INTO paper_live_meta(key,value) VALUES('peak_equity',?)", (str(SETTINGS["initial_balance"]),))
        elif float(saved_initial[0]) != float(SETTINGS["initial_balance"]):
            realized_row = c.execute("SELECT COALESCE(SUM(net_pnl),0) FROM paper_live_trades WHERE status='CLOSED'").fetchone()
            migrated_equity = float(SETTINGS["initial_balance"]) + float(realized_row[0] or 0.0)
            migrated_peak = max(float(SETTINGS["initial_balance"]), migrated_equity)
            c.execute("UPDATE paper_live_meta SET value=? WHERE key='peak_equity'", (str(migrated_peak),))
            c.execute("UPDATE paper_live_meta SET value=? WHERE key='initial_balance'", (str(SETTINGS["initial_balance"]),))
        else:
            c.execute("INSERT OR IGNORE INTO paper_live_meta(key,value) VALUES('peak_equity',?)", (str(SETTINGS["initial_balance"]),))
        if backfill_learning:
            # Backfill closed historical paper trades once. Legacy rows have no
            # timeframe, so they are explicitly marked as "unknown", never guessed.
            missing = c.execute("""SELECT t.* FROM paper_live_trades t
                LEFT JOIN paper_learning_events e ON e.trade_id=t.id
                WHERE t.status='CLOSED' AND e.trade_id IS NULL""").fetchall()
            for trade in missing:
                _record_learning_event(c, trade, legacy=True)
            repaired_legacy = _repair_legacy_funding_learning_events(c)
            if missing or repaired_legacy:
                _rebuild_learning_profiles_conn(c)
            else:
                event_count = int(c.execute("SELECT COUNT(*) FROM paper_learning_events").fetchone()[0] or 0)
                profile_count = int(c.execute("SELECT COUNT(*) FROM paper_learning_profiles").fetchone()[0] or 0)
                if event_count > 0 and profile_count == 0:
                    _rebuild_learning_profiles_conn(c)


def _safe_json_object(value: Any) -> dict:
    try:
        data = json.loads(value or "{}")
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError):
        return {}



def _repair_legacy_funding_learning_events(c: sqlite3.Connection, trade_id: int | None = None) -> int:
    """Repair only provably stale v1 learning outcomes after funding reconciliation.

    The migration is intentionally narrow and idempotent. It never changes the
    trade ledger or funding evidence; it only corrects the derived learning row.
    """
    sql = """
        SELECT
            t.id, t.market, t.status, t.funding_status, t.funding_total,
            t.funding_event_count, t.opened_at, t.closed_at, t.net_pnl,
            t.gross_pnl, t.entry_fee, t.exit_fee, t.notional,
            t.entry_fill, t.exit_fill,
            e.closed_at AS event_closed_at, e.net_pnl AS event_net_pnl,
            e.gross_pnl AS event_gross_pnl, e.total_fees AS event_total_fees,
            e.notional AS event_notional, e.return_pct AS event_return_pct,
            e.entry_fill AS event_entry_fill, e.exit_fill AS event_exit_fill,
            e.context_json AS event_context_json,
            COALESCE(f.cashflow_total, 0.0) AS evidence_funding_total,
            COALESCE(f.event_count, 0) AS evidence_event_count
        FROM paper_live_trades t
        JOIN paper_learning_events e ON e.trade_id=t.id
        LEFT JOIN (
            SELECT trade_id, SUM(cashflow) AS cashflow_total, COUNT(*) AS event_count
            FROM paper_funding_events GROUP BY trade_id
        ) f ON f.trade_id=t.id
        WHERE t.status='CLOSED' AND t.market='perp'
          AND t.funding_status='SYNCED'
    """
    args: tuple = ()
    if trade_id is not None:
        sql += " AND t.id=?"
        args = (int(trade_id),)

    rows = c.execute(sql, args).fetchall()
    repaired = 0

    def close(a: Any, b: Any) -> bool:
        try:
            return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-8)
        except (TypeError, ValueError):
            return False

    for row in rows:
        context = _safe_json_object(row["event_context_json"])
        migration = context.get("funding_learning_migration")
        if isinstance(migration, dict) and migration.get("migration") == "signed-funding-v1-to-v2":
            continue
        if context.get("learning_version") != "paper-trade-outcome-v1":
            continue

        funding = float(row["funding_total"] or 0.0)
        trade_net = float(row["net_pnl"] or 0.0)
        event_net = float(row["event_net_pnl"] or 0.0)
        notional = float(row["notional"] or 0.0)
        gross = float(row["gross_pnl"] or 0.0)
        entry_fee = float(row["entry_fee"] or 0.0)
        exit_fee = float(row["exit_fee"] or 0.0)
        if notional <= 0 or row["closed_at"] is None:
            continue

        # Require complete and independently persisted funding evidence.
        if not close(row["evidence_funding_total"], funding):
            continue
        if int(row["evidence_event_count"] or 0) != int(row["funding_event_count"] or 0):
            continue
        if int(row["evidence_event_count"] or 0) <= 0:
            continue

        # The trade ledger itself must satisfy the canonical signed-cashflow identity.
        canonical_net = gross - entry_fee - exit_fee + funding
        if not close(trade_net, canonical_net):
            continue

        # Prove this is the specific legacy defect: event PnL omitted signed funding.
        if not close(trade_net - event_net, funding):
            continue
        if not close(row["event_gross_pnl"], gross):
            continue
        if not close(row["event_notional"], notional):
            continue
        if not close(row["event_entry_fill"], row["entry_fill"]):
            continue
        if not close(row["event_exit_fill"], row["exit_fill"]):
            continue
        if not close(row["event_closed_at"], row["closed_at"]):
            continue

        corrected_fees = entry_fee + exit_fee - funding
        corrected_return = canonical_net / notional * 100.0
        context["funding_learning_migration"] = {
            "migration": "signed-funding-v1-to-v2",
            "reason": "Legacy learning outcome omitted signed funding cashflow",
            "old_net_pnl": event_net,
            "corrected_net_pnl": canonical_net,
            "funding_total": funding,
            "old_total_fees": float(row["event_total_fees"] or 0.0),
            "corrected_total_fees": corrected_fees,
            "evidence_event_count": int(row["evidence_event_count"]),
        }
        c.execute(
            """UPDATE paper_learning_events
               SET outcome=?, net_pnl=?, return_pct=?, total_fees=?, context_json=?
               WHERE trade_id=?""",
            (
                1 if canonical_net > 0 else 0,
                canonical_net,
                corrected_return,
                corrected_fees,
                json.dumps(context, ensure_ascii=False, sort_keys=True),
                int(row["id"]),
            ),
        )
        repaired += 1

    return repaired

def _sanitize_decision_context(value: Any, *, depth: int = 0) -> Any:
    """Bound and normalize model/indicator context before storing it in SQLite."""
    if depth > 4:
        return None
    if value is None or isinstance(value, (bool, str, int)):
        return value[:500] if isinstance(value, str) else value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "item"):
        try:
            return _sanitize_decision_context(value.item(), depth=depth + 1)
        except Exception:
            return None
    if isinstance(value, dict):
        clean = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 256:
                break
            clean[str(key)[:80]] = _sanitize_decision_context(item, depth=depth + 1)
        return clean
    if isinstance(value, (list, tuple)):
        return [_sanitize_decision_context(item, depth=depth + 1) for item in value[:64]]
    return str(value)[:200]


def _record_learning_event(c: sqlite3.Connection, trade: Any, *, legacy: bool = False) -> None:
    """Persist one immutable outcome observation for each fully reconciled trade."""
    if str(trade["market"] or "") == "perp" and str(trade["funding_status"] or "") != "SYNCED":
        return  # Do not train from a futures outcome whose funding cashflows are incomplete.
    notional = max(float(trade["notional"] or 0.0), 1e-12)
    net_pnl = float(trade["net_pnl"] or 0.0)
    opened_at = float(trade["opened_at"] or 0.0)
    closed_at = float(trade["closed_at"] or time.time())
    funding_total = float(trade["funding_total"] or 0.0) if "funding_total" in trade.keys() else 0.0
    # Signed funding income reduces net transaction costs; negative funding
    # cashflow increases costs. Net PnL already includes this same cashflow.
    total_fees = float(trade["entry_fee"] or 0.0) + float(trade["exit_fee"] or 0.0) - funding_total
    context = _safe_json_object(trade["entry_context_json"] if "entry_context_json" in trade.keys() else "{}")
    context["funding_total"] = round(funding_total, 10)
    context["funding_event_count"] = int(trade["funding_event_count"] or 0) if "funding_event_count" in trade.keys() else 0
    if legacy:
        context["migration_note"] = "Legacy closed trade; timeframe unavailable in original record."
    timeframe = str(trade["timeframe"] if "timeframe" in trade.keys() else "unknown")
    if legacy and not timeframe:
        timeframe = "unknown"
    c.execute("""INSERT OR IGNORE INTO paper_learning_events(
        trade_id,closed_at,symbol,market,timeframe,exchange,side,exit_reason,outcome,
        net_pnl,return_pct,duration_seconds,notional,gross_pnl,total_fees,entry_fill,exit_fill,context_json
    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        int(trade["id"]), closed_at, str(trade["symbol"]), str(trade["market"]), timeframe,
        str(trade["exchange"]), str(trade["side"]), str(trade["exit_reason"] or "UNKNOWN"),
        1 if net_pnl > 0 else 0, net_pnl, net_pnl / notional * 100.0,
        max(0.0, closed_at - opened_at), notional, float(trade["gross_pnl"] or 0.0),
        total_fees, float(trade["entry_fill"] or 0.0), float(trade["exit_fill"] or 0.0),
        json.dumps(context, ensure_ascii=False, sort_keys=True),
    ))


def _rebuild_learning_profiles_conn(c: sqlite3.Connection) -> dict:
    rows = _rows(c, "SELECT * FROM paper_learning_events ORDER BY closed_at ASC, trade_id ASC")
    grouped: dict[tuple[str, str, str, str], list[dict]] = {}
    for row in rows:
        key = (row["symbol"], row["market"], row["timeframe"], row["side"])
        grouped.setdefault(key, []).append(row)
    c.execute("DELETE FROM paper_learning_profiles")
    now = time.time()
    profiles = []
    for (symbol, market, timeframe, side), items in grouped.items():
        n = len(items)
        wins = sum(1 for x in items if float(x["net_pnl"]) > 0)
        losses = n - wins
        total_positive = sum(float(x["net_pnl"]) for x in items if float(x["net_pnl"]) > 0)
        total_negative = abs(sum(float(x["net_pnl"]) for x in items if float(x["net_pnl"]) < 0))
        total_pnl = sum(float(x["net_pnl"]) for x in items)
        avg_return = sum(float(x["return_pct"]) for x in items) / n if n else 0.0
        expectancy = total_pnl / n if n else 0.0
        profit_factor = (total_positive / total_negative) if total_negative > 0 else (None if total_positive <= 0 else 99.0)
        avg_duration = sum(float(x["duration_seconds"]) for x in items) / n if n else 0.0
        if n < 30:
            learning_state = "COLLECTING"
        elif avg_return <= 0 or (profit_factor is not None and profit_factor <= 1.0):
            learning_state = "NO_EDGE"
        elif n >= 50 and profit_factor is not None and profit_factor >= 1.15:
            learning_state = "PAPER_EVIDENCE_ONLY"
        else:
            learning_state = "SHADOW_VALIDATION"
        scope_key = "|".join((symbol, market, timeframe, side))
        c.execute("""INSERT INTO paper_learning_profiles(
            scope_key,symbol,market,timeframe,side,sample_count,win_count,loss_count,win_rate_pct,
            avg_net_return_pct,expectancy_usdt,profit_factor,total_net_pnl,avg_duration_seconds,
            learning_state,updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            scope_key, symbol, market, timeframe, side, n, wins, losses, wins / n * 100.0,
            avg_return, expectancy, profit_factor, total_pnl, avg_duration, learning_state, now,
        ))
        profiles.append({
            "scope_key": scope_key, "symbol": symbol, "market": market, "timeframe": timeframe,
            "side": side, "sample_count": n, "win_count": wins, "loss_count": losses,
            "win_rate_pct": wins / n * 100.0, "avg_net_return_pct": avg_return,
            "expectancy_usdt": expectancy, "profit_factor": profit_factor,
            "total_net_pnl": total_pnl, "avg_duration_seconds": avg_duration,
            "learning_state": learning_state, "updated_at": now,
        })
    profiles.sort(key=lambda x: (x["sample_count"], x["symbol"]), reverse=True)
    return {"profiles": profiles, "event_count": len(rows), "last_learned_at": max((x["closed_at"] for x in rows), default=None)}


def get_learning_state() -> dict:
    """Expose durable paper-trade learning memory and future-readiness evidence."""
    init_db()
    with _connect() as c:
        event_summary = c.execute("SELECT COUNT(*), MAX(closed_at) FROM paper_learning_events").fetchone()
        profiles = _rows(c, "SELECT * FROM paper_learning_profiles ORDER BY sample_count DESC, symbol ASC LIMIT 50")
        summary = {"event_count": int(event_summary[0] or 0), "last_learned_at": event_summary[1],
                   "profiles": profiles}
        rows = _rows(c, "SELECT trade_id,closed_at,symbol,market,timeframe,exchange,side,exit_reason,outcome,net_pnl,return_pct,duration_seconds,notional,total_fees FROM paper_learning_events ORDER BY closed_at DESC LIMIT 20")
        total = summary["event_count"]
        aggregate = c.execute("""SELECT COUNT(*), SUM(CASE WHEN net_pnl>0 THEN 1 ELSE 0 END),
            COALESCE(SUM(net_pnl),0), COALESCE(AVG(return_pct),0),
            COALESCE(SUM(CASE WHEN net_pnl>0 THEN net_pnl ELSE 0 END),0),
            COALESCE(ABS(SUM(CASE WHEN net_pnl<0 THEN net_pnl ELSE 0 END)),0)
            FROM paper_learning_events""").fetchone()
        n = int(aggregate[0] or 0); win_count = int(aggregate[1] or 0)
        gross_wins = float(aggregate[4] or 0.0); gross_losses = float(aggregate[5] or 0.0)
        pf = gross_wins / gross_losses if gross_losses > 0 else (99.0 if gross_wins > 0 else None)
        return {
            "version": LEARNING_VERSION,
            "summary": {"closed_trades": n, "wins": win_count, "losses": n - win_count,
                "win_rate_pct": win_count / n * 100.0 if n else 0.0,
                "total_net_pnl": float(aggregate[2] or 0.0),
                "avg_net_return_pct": float(aggregate[3] or 0.0),
                "profit_factor": pf, "last_learned_at": summary["last_learned_at"]},
            "profiles": summary["profiles"][:50], "recent_events": rows,
            "policy": {"source": "closed_simulated_trades_only", "min_samples_for_shadow_review": 30,
                "min_samples_for_paper_evidence": 50, "real_orders_enabled": False,
                "future_exchange_use": "REQUIRES_SEPARATE_VALIDATION_AND_EXPLICIT_ENABLE"},
        }



def get_strategy_validation_events() -> list[dict]:
    """Chronologically ordered reconciled closed-paper outcomes for validation only."""
    init_db()
    with _connect() as c:
        return _rows(c, "SELECT symbol,market,timeframe,side,net_pnl,return_pct,context_json,closed_at,trade_id FROM paper_learning_events ORDER BY closed_at ASC,trade_id ASC")

def get_strategy_learning_ranking(min_samples: int = 10) -> dict:
    """Read-only strategy cohorts built exclusively from reconciled closed paper trades."""
    from backend.strategy_learning import rank_strategy_performance
    init_db()
    with _connect() as c:
        rows = _rows(c, "SELECT symbol,market,timeframe,side,net_pnl,return_pct,context_json FROM paper_learning_events ORDER BY closed_at ASC,trade_id ASC")
    return rank_strategy_performance(rows, min_samples=min_samples)

def get_learning_gate(symbol: str, market: str, timeframe: str, side: str) -> dict:
    """Stable contract for a future exchange executor; never authorizes live orders."""
    symbol = str(symbol or "").upper().replace("/", "").strip()
    market = str(market or "spot").lower().strip()
    timeframe = str(timeframe or "1h").lower().strip()
    side = str(side or "LONG").upper().strip()
    if not SYMBOL_RE.fullmatch(symbol) or not symbol.endswith("USDT"):
        raise ValueError("نماد نامعتبر است")
    if market not in ("spot", "perp") or timeframe not in VALID_TIMEFRAMES or side not in ("LONG", "SHORT"):
        raise ValueError("بازار، تایم‌فریم یا جهت نامعتبر است")
    init_db()
    scope_key = "|".join((symbol, market, timeframe, side))
    with _connect() as c:
        c.row_factory = sqlite3.Row
        row = c.execute("SELECT * FROM paper_learning_profiles WHERE scope_key=?", (scope_key,)).fetchone()
    profile = dict(row) if row else None
    profile_state = profile["learning_state"] if profile else "NO_DATA"
    return {
        "symbol": symbol, "market": market, "timeframe": timeframe, "side": side,
        "learning_state": profile_state,
        "sample_count": int(profile["sample_count"]) if profile else 0,
        "win_rate_pct": profile["win_rate_pct"] if profile else None,
        "avg_net_return_pct": profile["avg_net_return_pct"] if profile else None,
        "profit_factor": profile["profit_factor"] if profile else None,
        "paper_evidence_available": profile_state == "PAPER_EVIDENCE_ONLY",
        "entry_blocked": profile_state == "NO_EDGE",
        "risk_scale": ({"NO_DATA": 0.50, "COLLECTING": 0.50,
                        "SHADOW_VALIDATION": 0.65, "PAPER_EVIDENCE_ONLY": 1.0,
                        "NO_EDGE": 0.0}.get(profile_state, 0.0)),
        "live_execution_allowed": False,
        "reason": ("این خروجی فقط فیلتر شواهد معاملات آزمایشی است؛ اجرای واقعی نیازمند اعتبارسنجی مستقل و فعال‌سازی جداگانه است. "
                   "NO_EDGE فقط ورود آزمایشی همان نماد/بازار/تایم‌فریم/جهت را متوقف می‌کند."),
    }


def rebuild_learning() -> dict:
    """Recompute persistent symbol/market/timeframe/side profiles from outcomes."""
    init_db()
    with _connect() as c:
        summary = _rebuild_learning_profiles_conn(c)
        c.execute("INSERT INTO paper_live_meta(key,value) VALUES('learning_last_rebuild',?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(time.time()),))
    return get_learning_state()


def get_learning_export_rows() -> list[dict]:
    init_db()
    with _connect() as c:
        return _rows(c, """SELECT trade_id,closed_at,symbol,market,timeframe,exchange,side,exit_reason,
            outcome,net_pnl,return_pct,duration_seconds,notional,gross_pnl,total_fees,entry_fill,exit_fill,context_json
            FROM paper_learning_events ORDER BY closed_at ASC,trade_id ASC""")


def _number(v: Any, label: str = "price") -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise RuntimeError(f"{label} در پاسخ صرافی نامعتبر است")
    if not math.isfinite(x) or x <= 0:
        raise RuntimeError(f"{label} در پاسخ صرافی نامعتبر است")
    return x


def _http_json(url: str, params: dict | None = None) -> Any:
    r = SESSION.get(url, params=params, timeout=(3, 6), headers={"Accept": "application/json"})
    r.raise_for_status()
    try:
        return r.json()
    except ValueError as exc:
        raise RuntimeError("پاسخ صرافی JSON معتبر نیست") from exc


def _market_symbol(symbol: str, market: str, exchange: str) -> str:
    if market == "spot":
        return symbol
    if exchange == "okx":
        return symbol[:-4] + "-USDT-SWAP" if symbol.endswith("USDT") else symbol
    if exchange == "gateio":
        return symbol[:-4] + "_USDT" if symbol.endswith("USDT") else symbol
    if exchange == "mexc":
        return symbol[:-4] + "_USDT" if symbol.endswith("USDT") else symbol
    return symbol


def _parse_ticker(exchange: str, payload: Any) -> float:
    if exchange in ("binance", "mexc"):
        return _number(payload.get("price") if isinstance(payload, dict) else None)
    if exchange == "bybit":
        result = (payload.get("result") or {}) if isinstance(payload, dict) else {}
        rows = result.get("list") or []
        if not rows:
            raise RuntimeError("Bybit بازار را برنگرداند")
        return _number(rows[0].get("lastPrice"))
    if exchange == "okx":
        rows = payload.get("data") or [] if isinstance(payload, dict) else []
        if not rows:
            raise RuntimeError("OKX بازار را برنگرداند")
        return _number(rows[0].get("last"))
    if exchange == "gateio":
        rows = payload if isinstance(payload, list) else []
        if not rows:
            raise RuntimeError("Gate.io بازار را برنگرداند")
        return _number(rows[0].get("last"))
    if exchange == "bitget":
        rows = payload.get("data") or [] if isinstance(payload, dict) else []
        if not rows:
            raise RuntimeError("Bitget بازار را برنگرداند")
        return _number(rows[0].get("lastPr") or rows[0].get("last"))
    raise RuntimeError("صرافی پشتیبانی نمی‌شود")


def _fetch_one(exchange: str, symbol: str, market: str) -> dict:
    ex_symbol = _market_symbol(symbol, market, exchange)
    if exchange == "binance":
        if market == "spot":
            url = "https://data-api.binance.vision/api/v3/ticker/price"
            params = {"symbol": ex_symbol}
        else:
            url = "https://fapi.binance.com/fapi/v1/ticker/price"
            params = {"symbol": ex_symbol}
    elif exchange == "bybit":
        url = "https://api.bybit.com/v5/market/tickers"
        params = {"category": "spot" if market == "spot" else "linear", "symbol": ex_symbol}
    elif exchange == "mexc":
        if market == "spot":
            url = "https://api.mexc.com/api/v3/ticker/price"
            params = {"symbol": ex_symbol}
        else:
            url = "https://contract.mexc.com/api/v1/contract/ticker"
            params = {"symbol": ex_symbol}
    elif exchange == "okx":
        inst = ex_symbol if market == "perp" else (symbol[:-4] + "-USDT" if symbol.endswith("USDT") else symbol)
        url = "https://www.okx.com/api/v5/market/ticker"
        params = {"instId": inst}
    elif exchange == "gateio":
        if market == "spot":
            gate_symbol = symbol[:-4] + "_USDT" if symbol.endswith("USDT") else symbol
            url = "https://api.gateio.ws/api/v4/spot/tickers"
            params = {"currency_pair": gate_symbol}
        else:
            url = "https://api.gateio.ws/api/v4/futures/usdt/tickers"
            params = {"contract": ex_symbol}
    elif exchange == "bitget":
        if market == "spot":
            url = "https://api.bitget.com/api/v2/spot/market/tickers"
            params = {"symbol": ex_symbol}
        else:
            url = "https://api.bitget.com/api/v2/mix/market/ticker"
            params = {"productType": "USDT-FUTURES", "symbol": ex_symbol}
    else:
        raise ValueError("exchange نامعتبر است")

    payload = _http_json(url, params)
    if exchange == "mexc" and market == "perp":
        if payload.get("success") is False:
            raise RuntimeError(payload.get("message") or "MEXC Futures خطا داد")
        data = payload.get("data") or {}
        price = data.get("lastPrice") or data.get("fairPrice")
        price = _number(price)
    else:
        if exchange in ("bybit", "okx", "bitget") and isinstance(payload, dict):
            code = str(payload.get("retCode", payload.get("code", "0")))
            if exchange == "bybit" and code != "0":
                raise RuntimeError("Bybit: " + str(payload.get("retMsg", "API error")))
            if exchange == "okx" and code != "0":
                raise RuntimeError("OKX: " + str(payload.get("msg", "API error")))
            if exchange == "bitget" and code not in ("00000", "0", "None"):
                raise RuntimeError("Bitget: " + str(payload.get("msg", "API error")))
        price = _parse_ticker(exchange, payload)
    received_at = time.time()
    # Some providers publish a server-side timestamp with the ticker. Preserve it
    # separately from our receipt timestamp so stale responses cannot masquerade
    # as fresh merely because the HTTP request just completed.
    source_ts = None
    try:
        if exchange == "bybit" and payload.get("time") is not None:
            source_ts = float(payload["time"]) / 1000.0
        elif exchange == "okx" and payload.get("data") and payload["data"][0].get("ts"):
            source_ts = float(payload["data"][0]["ts"]) / 1000.0
    except (TypeError, ValueError, IndexError, KeyError):
        source_ts = None
    if source_ts is not None:
        age = received_at - source_ts
        if age > QUOTE_MAX_AGE_SECONDS:
            raise RuntimeError(f"داده قیمت کهنه است ({age:.1f} ثانیه)")
        if age < -QUOTE_MAX_FUTURE_SKEW_SECONDS:
            raise RuntimeError("زمان پاسخ صرافی جلوتر از ساعت سیستم است")
    return {
        "symbol": symbol, "market": market, "exchange": exchange,
        "exchange_name": EXCHANGE_NAMES[exchange], "price": price,
        "timestamp": datetime.fromtimestamp(received_at, timezone.utc).isoformat(),
        "received_at_epoch": received_at,
        "source_timestamp_epoch": source_ts,
        "source_age_seconds": (max(0.0, received_at - source_ts) if source_ts is not None else None),
        "source_timestamp_verified": source_ts is not None,
        "source": "public_rest_ticker", "authenticated": False,
    }


def get_quote(symbol: str, market: str = "spot", exchange: str = "auto", *, use_cache: bool = True) -> dict:
    symbol = str(symbol or "").upper().replace("/", "").strip()
    market = str(market or "spot").lower().strip()
    exchange = str(exchange or "auto").lower().strip()
    if not SYMBOL_RE.fullmatch(symbol) or not symbol.endswith("USDT"):
        raise ValueError("نماد باید مانند BTCUSDT و با پسوند USDT باشد")
    if market not in ("spot", "perp"):
        raise ValueError("بازار باید spot یا perp باشد")
    if exchange != "auto" and exchange not in EXCHANGE_NAMES:
        raise ValueError("صرافی انتخاب‌شده پشتیبانی نمی‌شود")
    key = (symbol, market, exchange)
    now = time.time()
    cached = _CACHE.get(key)
    if use_cache and cached:
        cache_age = max(0.0, now - cached[0])
        if cache_age < _CACHE_TTL:
            return dict(cached[1], cached=True, cache_age_seconds=round(cache_age, 3),
                        data_status="fresh_cache")
        # Expired cache entries are never returned as a fallback when providers fail.
        _CACHE.pop(key, None)

    order = SETTINGS["fallback_order"] if exchange == "auto" else [exchange]
    errors = []
    for ex in order:
        try:
            quote = _fetch_one(ex, symbol, market)
            quote["fallback"] = (exchange == "auto" and ex != order[0])
            quote["requested_exchange"] = exchange
            checked_at = time.time()
            quote["checked_at_epoch"] = checked_at
            quote["cache_age_seconds"] = 0.0
            quote["cached"] = False
            quote["data_status"] = "fresh_live"
            quote["provider_failures_before_success"] = list(errors)
            _CACHE[key] = (checked_at, quote)
            return quote
        except Exception as exc:
            errors.append({"exchange": ex, "name": EXCHANGE_NAMES[ex], "error": str(exc)[:160]})
    detail = " | ".join(f"{x['name']}: {x['error']}" for x in errors)
    raise RuntimeError("اتصال قیمت زنده از هیچ صرافی برقرار نشد؛ داده قدیمی جایگزین نشد: " + detail)


def get_consensus_quote(symbol: str, market: str = "spot", *, min_sources: int | None = None,
                        max_deviation_pct: float | None = None) -> dict:
    """Return a quote only when independent venues agree within a strict band.

    This is used for new AUTO paper entries. It never averages venue prices:
    the median is the reference and the actual median venue quote is returned.
    """
    minimum = int(min_sources if min_sources is not None else SETTINGS.get("cross_exchange_min_sources", 2))
    band = float(max_deviation_pct if max_deviation_pct is not None else SETTINGS.get("cross_exchange_max_deviation_pct", 1.0))
    if minimum < 2 or minimum > len(EXCHANGE_NAMES):
        raise ValueError("حداقل تعداد منابع مستقل باید بین ۲ و تعداد صرافی‌ها باشد")
    if not math.isfinite(band) or band <= 0 or band > 10:
        raise ValueError("حد اختلاف قیمت بین صرافی‌ها نامعتبر است")
    successes, errors = [], []
    for venue in SETTINGS["fallback_order"]:
        try:
            q = _fetch_one(venue, symbol, market)
            price = _number(q.get("price"), "قیمت")
            if q.get("symbol", symbol).upper() != symbol.upper() or q.get("market", market).lower() != market.lower():
                raise RuntimeError("نماد یا نوع بازار پاسخ صرافی با درخواست یکسان نیست")
            successes.append(dict(q, price=price))
        except Exception as exc:
            errors.append({"exchange": venue, "error": str(exc)[:160]})
        if len(successes) >= max(minimum, 3):
            break
    if len(successes) < minimum:
        raise RuntimeError(f"اجماع قیمت برقرار نشد؛ فقط {len(successes)} منبع معتبر از حداقل {minimum} منبع. " + str(errors[:3]))
    prices = sorted(q["price"] for q in successes)
    median = prices[len(prices) // 2] if len(prices) % 2 else (prices[len(prices)//2 - 1] + prices[len(prices)//2]) / 2.0
    deviations = [abs(q["price"] - median) / median * 100.0 for q in successes]
    worst = max(deviations)
    if worst > band:
        details = ", ".join(f"{q['exchange']}={q['price']:.10g}" for q in successes)
        raise RuntimeError(f"اختلاف قیمت صرافی‌ها بیش از حد مجاز است ({worst:.3f}% > {band:.3f}%): {details}")
    # Select the real venue quote closest to the median; never synthesize a fill price.
    selected_index = min(range(len(successes)), key=lambda i: abs(successes[i]["price"] - median))
    selected = successes[selected_index]
    checked = time.time()
    return dict(selected, requested_exchange="auto", cross_exchange_validated=True,
                consensus_price=median, consensus_sources=[{"exchange": q["exchange"], "price": q["price"],
                "deviation_pct": round(deviations[i], 5)} for i, q in enumerate(successes)],
                consensus_source_count=len(successes), consensus_max_deviation_pct=round(worst, 5),
                consensus_checked_at_epoch=checked, provider_failures=errors)


def check_connections(symbol: str = "BTCUSDT", market: str = "spot") -> dict:
    rows = []
    with ThreadPoolExecutor(max_workers=len(EXCHANGE_NAMES)) as pool:
        futures = {pool.submit(get_quote, symbol, market, ex, use_cache=False): ex for ex in EXCHANGE_NAMES}
        for f in as_completed(futures):
            ex = futures[f]
            try:
                q = f.result()
                rows.append({"id": ex, "name": EXCHANGE_NAMES[ex], "ok": True, "price": q["price"], "timestamp": q["timestamp"]})
            except Exception as exc:
                rows.append({"id": ex, "name": EXCHANGE_NAMES[ex], "ok": False, "error": str(exc)[:160]})
    rows.sort(key=lambda x: SETTINGS["fallback_order"].index(x["id"]))
    ok_count = sum(1 for x in rows if x["ok"])
    return {"symbol": symbol, "market": market, "providers": rows, "ok_count": ok_count,
            "total": len(rows), "checked_at": datetime.now(timezone.utc).isoformat(),
            "note": "فقط دسترسی عمومی قیمت آزمایش شد؛ API Key خصوصی یا سفارش واقعی استفاده نشده است."}


def _rows(c: sqlite3.Connection, sql: str, args=()) -> list[dict]:
    c.row_factory = sqlite3.Row
    return [dict(r) for r in c.execute(sql, args).fetchall()]


@_paper_ledger_writer_guard
def sync_open_funding_positions(trade_id: int | None = None, *, force: bool = False) -> dict:
    """Reconcile settled funding events for open or not-yet-reconciled closed positions.

    Public REST calls are made outside SQLite write transactions. A composite
    primary key prevents duplicate cashflows after retries/restarts.
    """
    init_db()
    where = "market='perp' AND (status='OPEN' OR (status='CLOSED' AND funding_status IN ('PENDING','ERROR','PARTIAL')))"
    args: tuple = ()
    if trade_id is not None:
        where += " AND id=?"
        args = (int(trade_id),)
    with _connect() as c:
        c.row_factory = sqlite3.Row
        positions = [dict(r) for r in c.execute(f"SELECT * FROM paper_live_trades WHERE {where} ORDER BY id", args).fetchall()]

    synced = failed = inserted_total = skipped = 0
    now = time.time()
    for trade in positions:
        checked_at = float(trade.get("funding_checked_at") or 0.0)
        if not force and checked_at > 0 and now - checked_at < 45.0:
            skipped += 1
            continue
        tid = int(trade["id"])
        exchange = str(trade["exchange"] or "").lower()
        try:
            sync_end = float(trade["closed_at"] or now)
            events = fetch_funding_history(exchange, str(trade["symbol"]), float(trade["opened_at"]), sync_end)
            status = "SYNCED"
            status_note = None
            # These venues document finite public historical lookback windows.
            if exchange in ("okx", "bitget") and float(trade["opened_at"]) < sync_end - 90 * 86400:
                status = "PARTIAL"
                status_note = "تاریخچهٔ عمومی صرافی برای کل عمر موقعیت کافی نیست؛ فقط بازهٔ در دسترس ثبت شد."
            elif not funding_history_complete(exchange, events, float(trade["opened_at"])):
                status = "PARTIAL"
                status_note = "به سقف تعداد رکوردهای API رسیدیم؛ احتمال دارد بخشی از تسویه‌های قدیمی‌تر در دسترس نباشد."
            with _connect() as c:
                c.row_factory = sqlite3.Row
                c.execute("BEGIN IMMEDIATE")
                current = c.execute("SELECT * FROM paper_live_trades WHERE id=?", (tid,)).fetchone()
                if current is None:
                    continue
                added = 0
                for event in events:
                    settle_ms = int(round(float(event["settlement_ts"]) * 1000))
                    if settle_ms <= int(float(current["opened_at"]) * 1000):
                        continue
                    partial_rows = [dict(r) for r in c.execute(
                        "SELECT created_at,quantity FROM paper_partial_exits WHERE trade_id=? AND created_at<=? ORDER BY created_at,id",
                        (tid, settle_ms / 1000.0)).fetchall()]
                    quantity_at_event, exited_at_event = quantity_at_settlement(
                        float(current["quantity"]), partial_rows, settle_ms / 1000.0)
                    if quantity_at_event <= max(1e-12, float(current["quantity"]) * 1e-10):
                        continue
                    cashflow, event_notional, basis = funding_cashflow(
                        current["side"], quantity_at_event, float(event["funding_rate"]),
                        mark_price=event.get("mark_price"), entry_price=float(current["entry_fill"]),
                    )
                    cur = c.execute("""INSERT OR IGNORE INTO paper_funding_events(
                        trade_id,settlement_ts_ms,exchange,symbol,side,funding_rate,mark_price,
                        event_notional,notional_basis,position_quantity,partial_exited_quantity,
                        cashflow,source,created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (tid, settle_ms, exchange, str(current["symbol"]), str(current["side"]),
                     float(event["funding_rate"]), event.get("mark_price"), event_notional,
                     basis, quantity_at_event, exited_at_event, cashflow, "public_funding_history", now))
                    added += max(0, cur.rowcount)
                total_row = c.execute("SELECT COALESCE(SUM(cashflow),0),COUNT(*) FROM paper_funding_events WHERE trade_id=?", (tid,)).fetchone()
                funding_total = float(total_row[0] or 0.0)
                event_count = int(total_row[1] or 0)
                c.execute("""UPDATE paper_live_trades SET funding_total=?,funding_event_count=?,funding_status=?,funding_error=?,
                    funding_checked_at=? WHERE id=?""",
                    (funding_total, event_count, status, status_note, now, tid))
                latest_trade = c.execute("SELECT * FROM paper_live_trades WHERE id=?", (tid,)).fetchone()
                if latest_trade is not None and str(latest_trade["status"]) == "CLOSED":
                    corrected_net = (float(latest_trade["gross_pnl"] or 0.0)
                                     - float(latest_trade["entry_fee"] or 0.0)
                                     - float(latest_trade["exit_fee"] or 0.0) + funding_total)
                    c.execute("UPDATE paper_live_trades SET net_pnl=? WHERE id=?", (corrected_net, tid))
                    latest_trade = c.execute("SELECT * FROM paper_live_trades WHERE id=?", (tid,)).fetchone()
                    if status == "SYNCED":
                        _record_learning_event(c, latest_trade)
                        _repair_legacy_funding_learning_events(c, trade_id=tid)
                        _rebuild_learning_profiles_conn(c)
                inserted_total += added
                synced += 1
        except Exception as exc:
            failed += 1
            with _connect() as c:
                c.execute("UPDATE paper_live_trades SET funding_status='ERROR',funding_error=?,funding_checked_at=? WHERE id=?",
                          (str(exc)[:240], now, tid))
    return {"version": FUNDING_VERSION, "positions_checked": len(positions) - skipped,
            "positions_synced": synced, "positions_failed": failed,
            "positions_skipped_cooldown": skipped, "events_inserted": inserted_total}


def get_funding_audit(trade_id: int) -> dict:
    """Read-only, chronological audit of settled Funding and partial exits."""
    init_db()
    with _connect() as c:
        c.row_factory = sqlite3.Row
        trade = c.execute("""SELECT id,symbol,market,exchange,side,status,quantity,opened_at,closed_at,
            funding_total,funding_event_count,funding_status,funding_error,entry_fill,net_pnl
            FROM paper_live_trades WHERE id=?""", (int(trade_id),)).fetchone()
        if trade is None:
            raise ValueError("موقعیت آزمایشی پیدا نشد")
        events = _rows(c, """SELECT settlement_ts_ms,exchange,symbol,side,funding_rate,mark_price,
            event_notional,notional_basis,position_quantity,partial_exited_quantity,cashflow,source,created_at
            FROM paper_funding_events WHERE trade_id=? ORDER BY settlement_ts_ms""", (int(trade_id),))
        exits = _rows(c, """SELECT id,created_at,quantity,reference_exit,exit_fill,entry_fee_allocated,
            exit_fee,gross_pnl,net_pnl,reason FROM paper_partial_exits WHERE trade_id=? ORDER BY created_at,id""", (int(trade_id),))
    return {"trade": dict(trade), "funding_events": events, "partial_exits": exits,
            "funding_event_sum": round(sum(float(x["cashflow"] or 0) for x in events), 10),
            "audit_complete": str(trade["funding_status"] or "") == "SYNCED" or str(trade["market"]) != "perp"}


def _funding_event_count(c: sqlite3.Connection, trade_id: int) -> int:
    row = c.execute("SELECT COUNT(*) FROM paper_funding_events WHERE trade_id=?", (int(trade_id),)).fetchone()
    return int(row[0] or 0)


def _closed_totals(c: sqlite3.Connection) -> tuple[float, float]:
    # Partial exits on still-open positions are realized cashflows too. Once a
    # position is fully closed, its final net_pnl already includes those exits;
    # therefore only add partial rows belonging to OPEN trades.
    closed = c.execute("SELECT COALESCE(SUM(net_pnl),0) FROM paper_live_trades WHERE status='CLOSED'").fetchone()
    partial = c.execute("""SELECT COALESCE(SUM(p.net_pnl),0) FROM paper_partial_exits p
        JOIN paper_live_trades t ON t.id=p.trade_id WHERE t.status='OPEN'""").fetchone()
    realized = float(closed[0] or 0) + float(partial[0] or 0)
    day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    closed_day = c.execute("SELECT COALESCE(SUM(net_pnl),0) FROM paper_live_trades WHERE status='CLOSED' AND closed_at>=?", (day_start,)).fetchone()
    partial_day = c.execute("""SELECT COALESCE(SUM(p.net_pnl),0) FROM paper_partial_exits p
        JOIN paper_live_trades t ON t.id=p.trade_id WHERE t.status='OPEN' AND p.created_at>=?""", (day_start,)).fetchone()
    daily = float(closed_day[0] or 0) + float(partial_day[0] or 0)
    return realized, daily


def _closed_trade(c: sqlite3.Connection, trade_id: int, exit_reference: float, reason: str = "MANUAL") -> dict:
    c.row_factory = sqlite3.Row
    row = c.execute("SELECT * FROM paper_live_trades WHERE id=? AND status='OPEN'", (int(trade_id),)).fetchone()
    if not row:
        raise ValueError("موقعیت باز پیدا نشد یا قبلاً بسته شده است")
    side = row["side"]
    try:
        saved_costs = json.loads(row["execution_costs_json"] or "{}")
        if not isinstance(saved_costs, dict) or not saved_costs.get("total_adverse_price_bps_per_side"):
            legacy_cfg = dict(SETTINGS, spread_bps_full=0.0,
                              impact_bps_per_1000_usdt=0.0, max_impact_bps_per_side=0.0)
            saved_costs = execution_costs(float(row["notional"]), legacy_cfg)
    except (TypeError, ValueError):
        legacy_cfg = dict(SETTINGS, spread_bps_full=0.0,
                          impact_bps_per_1000_usdt=0.0, max_impact_bps_per_side=0.0)
        saved_costs = execution_costs(float(row["notional"]), legacy_cfg)
    partials = c.execute("SELECT * FROM paper_partial_exits WHERE trade_id=? ORDER BY id", (int(trade_id),)).fetchall()
    exited_qty = sum(float(x["quantity"]) for x in partials)
    remaining_qty = max(0.0, float(row["quantity"]) - exited_qty)
    if remaining_qty <= max(1e-12, float(row["quantity"]) * 1e-10):
        raise ValueError("مقدار باقی‌مانده برای بستن کامل معتبر نیست")
    allocated_entry_fee = sum(float(x["entry_fee_allocated"]) for x in partials)
    remaining_entry_fee = max(0.0, float(row["entry_fee"]) - allocated_entry_fee)
    fee_rate = float(saved_costs["fee_bps_per_side"]) / 10000.0
    direction = 1 if side == "LONG" else -1
    exit_fill = fill_price(float(exit_reference), side, "exit", saved_costs)
    exit_fee_remaining = remaining_qty * exit_fill * fee_rate
    gross_remaining = direction * remaining_qty * (exit_fill - float(row["entry_fill"]))
    partial_gross = sum(float(x["gross_pnl"]) for x in partials)
    partial_exit_fees = sum(float(x["exit_fee"]) for x in partials)
    partial_net = sum(float(x["net_pnl"]) for x in partials)
    gross = partial_gross + gross_remaining
    exit_fee = partial_exit_fees + exit_fee_remaining
    funding_row = c.execute("SELECT COALESCE(SUM(cashflow),0) FROM paper_funding_events WHERE trade_id=?", (int(trade_id),)).fetchone()
    funding_total = float(funding_row[0] or 0.0)
    funding_count = _funding_event_count(c, int(trade_id))
    # Funding events already store the exact open quantity at each settlement.
    # Partial realized PnL and remaining-position PnL are therefore additive.
    net = partial_net + gross_remaining - remaining_entry_fee - exit_fee_remaining + funding_total
    now = time.time()
    next_funding_status = ("PENDING" if str(row["market"]) == "perp" and str(row["funding_status"] or "") == "SYNCED"
                           else str(row["funding_status"] or "NOT_APPLICABLE"))
    c.execute("""UPDATE paper_live_trades SET status='CLOSED',closed_at=?,reference_exit=?,exit_fill=?,
        exit_fee=?,gross_pnl=?,net_pnl=?,funding_total=?,funding_event_count=?,exit_reason=?,last_price=?,last_price_at=?,
        funding_status=?,funding_checked_at=CASE WHEN ?='PENDING' THEN 0 ELSE funding_checked_at END
        WHERE id=? AND status='OPEN'""",
        (now, float(exit_reference), exit_fill, exit_fee, gross, net, funding_total, funding_count,
         reason, float(exit_reference), now, next_funding_status, next_funding_status, int(trade_id)))
    closed_row = c.execute("SELECT * FROM paper_live_trades WHERE id=?", (int(trade_id),)).fetchone()
    _record_learning_event(c, closed_row)
    _rebuild_learning_profiles_conn(c)
    return {"id": int(trade_id), "status": "CLOSED", "reference_exit": float(exit_reference),
            "exit_fill": exit_fill, "gross_pnl": gross, "net_pnl": net,
            "entry_fee": float(row["entry_fee"]), "exit_fee": exit_fee,
            "partial_exit_count": len(partials), "partial_quantity": exited_qty,
            "remaining_quantity": remaining_qty, "funding_total": funding_total,
            "funding_event_count": funding_count, "funding_status": str(row["funding_status"] or "UNKNOWN"),
            "funding_error": row["funding_error"], "reason": reason}


# Risk rails an engine (e.g. autopilot) may override per trade. Everything else
# (fees, slippage, mode, leverage) stays global and read-only.
OVERRIDABLE_SETTINGS = ("max_open_positions", "max_position_notional_pct", "risk_per_trade_pct",
                        "stop_loss_pct", "take_profit_pct", "max_daily_loss_pct", "max_drawdown_pct",
                        "max_portfolio_risk_pct", "max_spot_risk_pct", "max_perp_risk_pct",
                        "max_directional_risk_pct")


def _idempotent_replay_result(row: sqlite3.Row) -> dict:
    """Return the original simulated execution when a request is replayed."""
    quote = {
        "symbol": str(row["symbol"]), "market": str(row["market"]),
        "exchange": str(row["exchange"]), "price": float(row["reference_entry"]),
        "timestamp": float(row["opened_at"]), "source": "persisted_idempotent_replay",
        "authenticated": False, "cached": False, "fallback": False,
    }
    try:
        settings = json.loads(row["settings_json"] or "{}")
        if not isinstance(settings, dict):
            settings = {}
    except (TypeError, ValueError):
        settings = {}
    return {
        "id": int(row["id"]), "symbol": str(row["symbol"]), "market": str(row["market"]),
        "exchange": str(row["exchange"]), "side": str(row["side"]),
        "quantity": float(row["quantity"]), "notional": float(row["notional"]),
        "reference_entry": float(row["reference_entry"]), "entry_fill": float(row["entry_fill"]),
        "entry_fee": float(row["entry_fee"]), "stop_price": float(row["stop_price"]),
        "target_price": float(row["target_price"]), "timeframe": str(row["timeframe"] or "unknown"),
        "settings": settings, "quote": quote, "status": str(row["status"]),
        "entry_idempotency_key": row["entry_idempotency_key"], "idempotent_replay": True,
    }


@_paper_ledger_writer_guard
def open_position(symbol: str, side: str, market: str = "spot", exchange: str = "auto", timeframe: str = "1h",
                  overrides: dict | None = None, entry_source: str | None = None,
                  decision_context: dict | None = None,
                  idempotency_key: str | None = None,
                  atr_value: float | None = None) -> dict:
    symbol = str(symbol or "").upper().replace("/", "").strip()
    side = str(side or "").upper().strip()
    market = str(market or "spot").lower().strip()
    timeframe = str(timeframe or "1h").lower().strip()
    if idempotency_key is not None:
        idempotency_key = str(idempotency_key).strip()
        if (not idempotency_key or len(idempotency_key) > 180
                or not re.fullmatch(r"[A-Za-z0-9:_|.\-]+", idempotency_key)):
            raise ValueError("شناسهٔ یکتای ورود نامعتبر است")
    if timeframe not in VALID_TIMEFRAMES:
        raise ValueError("تایم‌فریم باید یکی از 5m، 15m، 30m، 1h، 4h یا 1d باشد")
    if side not in ("LONG", "SHORT"):
        raise ValueError("جهت باید LONG یا SHORT باشد")
    if market == "spot" and side != "LONG":
        raise ValueError("در بازار اسپات موقعیت SHORT مجاز نیست؛ برای شورت بازار فیوچرز را انتخاب کن")
    # Fast replay check avoids exchange calls when the same signal was already
    # committed before a crash/retry. A second check under BEGIN IMMEDIATE below
    # closes the race between concurrent workers.
    if idempotency_key:
        init_db()
        with _connect() as existing_conn:
            existing_conn.row_factory = sqlite3.Row
            existing = existing_conn.execute(
                "SELECT * FROM paper_live_trades WHERE entry_idempotency_key=?",
                (idempotency_key,)).fetchone()
        if existing:
            return _idempotent_replay_result(existing)
    if market not in ("spot", "perp"):
        raise ValueError("نوع بازار باید spot یا perp باشد")
    eff = dict(SETTINGS)
    override_ranges = {
        "max_open_positions": (1, 10), "max_position_notional_pct": (1.0, 100.0),
        "risk_per_trade_pct": (0.05, 5.0), "stop_loss_pct": (0.1, 20.0),
        "take_profit_pct": (0.1, 50.0), "max_daily_loss_pct": (0.1, 20.0),
        "max_drawdown_pct": (0.1, 50.0), "max_portfolio_risk_pct": (0.25, 10.0),
        "max_spot_risk_pct": (0.25, 10.0), "max_perp_risk_pct": (0.25, 10.0),
        "max_directional_risk_pct": (0.25, 10.0),
    }
    for key, value in (overrides or {}).items():
        if key not in OVERRIDABLE_SETTINGS:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"مقدار تنظیم ریسک {key} نامعتبر است")
        low, high = override_ranges[key]
        if not low <= float(value) <= high:
            raise ValueError(f"مقدار تنظیم ریسک {key} خارج از محدوده مجاز است")
        eff[key] = float(value)
    if exchange == "auto" and SETTINGS.get("cross_exchange_validation_enabled", True):
        quote = get_consensus_quote(symbol, market)
    else:
        quote = get_quote(symbol, market, exchange)
    ref = float(quote["price"])
    # Refresh the current book before admitting more risk. If any existing
    # position cannot be marked on its original exchange, fail closed.
    current_state = get_state(refresh_quotes=True)
    current_account = current_state.get("account") or {}
    if int(current_account.get("disconnected_positions") or 0) > 0:
        raise ValueError("قیمت یک موقعیت باز از صرافی ورود دریافت نشد؛ تا بازیابی قیمت، ورود جدید متوقف است")
    if int(current_account.get("funding_incomplete_positions") or 0) > 0:
        raise ValueError("هزینهٔ Funding یک یا چند معامله هنوز کامل تطبیق نشده؛ تا تکمیل تاریخچه، ورود جدید متوقف است")
    direction = 1 if side == "LONG" else -1
    fee_rate = SETTINGS["fee_bps_per_side"] / 10000.0
    # Seed sizing with the canonical label/backtest barrier geometry. The
    # size-dependent execution cost is recalculated in the convergence loop below.
    provisional_costs = execution_costs(1000.0, SETTINGS)
    entry_fill = fill_price(ref, side, "entry", provisional_costs)

    # AutoPilot supplies ATR from the same CLOSED candle used for the signal.
    # Keep the exact +/-1.5 ATR geometry used by labels and backtests; report
    # actual net R/R after fees, spread, slippage and size impact separately.
    atr_bracket = None
    if atr_value is not None:
        atr_bracket = shared_atr_bracket(
            entry_price=entry_fill, atr_value=atr_value, side=side,
            fee_bps_per_side=provisional_costs["fee_bps_per_side"],
            slippage_bps_per_side=provisional_costs["total_adverse_price_bps_per_side"],
            entry_price_is_fill=True,
        )
        eff["stop_loss_pct"] = float(atr_bracket["stop_loss_pct"])
        eff["take_profit_pct"] = float(atr_bracket["take_profit_pct"])

    init_db()
    with _connect() as c:
        c.row_factory = sqlite3.Row
        c.execute("BEGIN IMMEDIATE")
        if idempotency_key:
            existing = c.execute(
                "SELECT * FROM paper_live_trades WHERE entry_idempotency_key=?",
                (idempotency_key,)).fetchone()
            if existing:
                return _idempotent_replay_result(existing)
        open_detail_rows = c.execute("SELECT * FROM paper_live_trades WHERE status='OPEN' ORDER BY id").fetchall()
        open_risk = aggregate_open_risk(
            open_detail_rows,
            fee_bps_per_side=SETTINGS["fee_bps_per_side"],
            slippage_bps_per_side=SETTINGS["slippage_bps_per_side"],
        )
        if not open_risk["complete"]:
            raise ValueError("ریسک حدضرر یکی از موقعیت‌های باز قابل محاسبه نیست؛ ورود جدید برای ایمنی متوقف شد")
        open_count = len(open_detail_rows)
        open_notional = sum(float(row["notional"] or 0.0) for row in open_detail_rows)
        if open_count >= int(eff["max_open_positions"]):
            raise ValueError("حداکثر تعداد موقعیت باز آزمایشی پر شده است")
        exists = c.execute("SELECT 1 FROM paper_live_trades WHERE status='OPEN' AND symbol=? AND market=?", (symbol, market)).fetchone()
        if exists:
            raise ValueError("برای این نماد و بازار، یک موقعیت باز وجود دارد")
        stale_cutoff = time.time() - max(30.0, float(SETTINGS.get("quote_refresh_seconds", 10)) * 3.0)
        stale_open = c.execute("SELECT id FROM paper_live_trades WHERE status='OPEN' AND (last_price_at IS NULL OR CAST(last_price_at AS REAL)<?)",
                               (stale_cutoff,)).fetchone()
        if stale_open:
            raise ValueError("قیمت موقعیت باز قدیمی است؛ تا دریافت قیمت تازه از صرافی ورود جدید متوقف است")
        realized, daily = _closed_totals(c)
        realized_equity = SETTINGS["initial_balance"] + realized
        # Never increase risk from unrealized profits, but do account for
        # marked-to-market losses when computing the remaining cash/risk budget.
        marked_equity = (current_state.get("account") or {}).get("equity")
        try:
            marked_equity = float(marked_equity)
            if not math.isfinite(marked_equity) or marked_equity <= 0:
                marked_equity = None
        except (TypeError, ValueError):
            marked_equity = None
        equity = min(realized_equity, marked_equity) if marked_equity is not None else realized_equity
        if daily <= -(equity * eff["max_daily_loss_pct"] / 100):
            raise ValueError("حد ضرر روزانهٔ حساب آزمایشی فعال شده است؛ ورود جدید متوقف شد")
        peak_row = c.execute("SELECT value FROM paper_live_meta WHERE key='peak_equity'").fetchone()
        peak = max(SETTINGS["initial_balance"], float(peak_row[0]) if peak_row else SETTINGS["initial_balance"], equity)
        dd = equity / peak - 1.0 if peak else 0.0
        if dd <= -(eff["max_drawdown_pct"] / 100):
            raise ValueError("حداکثر افت سرمایه فعال شده است؛ ورود جدید متوقف شد")
        available = equity - open_notional
        if available <= 0:
            raise ValueError("موجودی آزاد حساب آزمایشی کافی نیست")

        # Portfolio-, market-, and direction-level stop-risk budgets are all
        # checked atomically under BEGIN IMMEDIATE, so concurrent entries cannot
        # spend the same remaining risk budget twice.
        portfolio_cap = equity * float(eff["max_portfolio_risk_pct"]) / 100.0
        market_cap_pct = float(eff["max_spot_risk_pct"] if market == "spot" else eff["max_perp_risk_pct"])
        market_cap = equity * market_cap_pct / 100.0
        directional_cap = equity * float(eff["max_directional_risk_pct"]) / 100.0
        current_total_risk = float(open_risk["total"])
        current_market_risk = float(open_risk["by_market"].get(market, 0.0))
        current_directional_risk = float(open_risk["by_side"].get(side, 0.0))
        remaining_portfolio = portfolio_cap - current_total_risk
        remaining_market = market_cap - current_market_risk
        remaining_directional = directional_cap - current_directional_risk
        risk_budget_cash = min(
            equity * float(eff["risk_per_trade_pct"]) / 100.0,
            remaining_portfolio, remaining_market, remaining_directional,
        )
        if risk_budget_cash <= 1e-8:
            raise ValueError("ظرفیت ریسک پرتفوی، بازار یا جهت معامله تکمیل شده است؛ ورود جدید مسدود شد")
        sizing = size_for_risk(
            equity=equity, risk_budget_cash=risk_budget_cash,
            stop_loss_pct=eff["stop_loss_pct"],
            max_position_notional_pct=eff["max_position_notional_pct"],
            available_balance=available,
            fee_bps_per_side=SETTINGS["fee_bps_per_side"],
            slippage_bps_per_side=provisional_costs["total_adverse_price_bps_per_side"],
        )
        notional = float(sizing["notional"])
        if notional < 10:
            raise ValueError("ظرفیت ریسک باقی‌مانده برای یک موقعیت حداقل ۱۰ تتری کافی نیست")
        # Iterate to a stable notional while recomputing the canonical ATR stop
        # from the same size-dependent fill/cost assumptions used for sizing.
        # This closes the small but real risk-budget drift caused by using a
        # provisional fill for the stop percentage and a final fill for execution.
        for _ in range(32):
            trade_costs = execution_costs(notional, SETTINGS)
            candidate_entry_fill = fill_price(ref, side, "entry", trade_costs)
            candidate_stop_pct = float(eff["stop_loss_pct"])
            if atr_value is not None:
                candidate_bracket = shared_atr_bracket(
                    entry_price=candidate_entry_fill, atr_value=atr_value, side=side,
                    fee_bps_per_side=trade_costs["fee_bps_per_side"],
                    slippage_bps_per_side=trade_costs["total_adverse_price_bps_per_side"],
                    entry_price_is_fill=True,
                )
                candidate_stop_pct = float(candidate_bracket["stop_loss_pct"])
            candidate_sizing = size_for_risk(
                equity=equity, risk_budget_cash=risk_budget_cash,
                stop_loss_pct=candidate_stop_pct,
                max_position_notional_pct=eff["max_position_notional_pct"],
                available_balance=available,
                fee_bps_per_side=trade_costs["fee_bps_per_side"],
                slippage_bps_per_side=trade_costs["total_adverse_price_bps_per_side"],
            )
            next_notional = float(candidate_sizing["notional"])
            if next_notional < 10:
                raise ValueError("ظرفیت ریسک باقی‌مانده برای یک موقعیت حداقل ۱۰ تتری کافی نیست")
            if abs(next_notional - notional) <= max(1e-8, notional * 1e-8):
                notional = min(notional, next_notional)
                sizing = candidate_sizing
                break
            notional = next_notional
        else:
            raise ValueError("اندازه‌گذاری با هزینه اجرای وابسته به حجم همگرا نشد؛ ورود برای ایمنی متوقف شد")

        trade_costs = execution_costs(notional, SETTINGS)
        fee_rate = float(trade_costs["fee_bps_per_side"]) / 10000.0
        if notional < 10:
            raise ValueError("ظرفیت ریسک باقی‌مانده برای یک موقعیت حداقل ۱۰ تتری کافی نیست")
        entry_fill = fill_price(ref, side, "entry", trade_costs)
        if atr_value is not None:
            atr_bracket = shared_atr_bracket(
                entry_price=entry_fill, atr_value=atr_value, side=side,
                fee_bps_per_side=trade_costs["fee_bps_per_side"],
                slippage_bps_per_side=trade_costs["total_adverse_price_bps_per_side"],
                entry_price_is_fill=True,
            )
            eff["stop_loss_pct"] = float(atr_bracket["stop_loss_pct"])
            eff["take_profit_pct"] = float(atr_bracket["take_profit_pct"])
            atr_bracket["final_execution_validation"] = {
                "valid": True,
                "net_reward_risk": atr_bracket["net_reward_risk"],
                "stop_loss_pct": atr_bracket["stop_loss_pct"],
                "take_profit_pct": atr_bracket["take_profit_pct"],
                "round_trip_cost_pct": atr_bracket["round_trip_cost_pct"],
                "funding_included": False,
                "method": "final_notional_execution_cost_validation",
                "note": "Barrier levels match training/backtest ATR geometry; net R/R uses final size-dependent fees, spread, slippage and impact. Funding is excluded until settled.",
            }
            structure = (decision_context or {}).get("atr_risk_input", {}).get("market_structure") if isinstance(decision_context, dict) else None
            if structure:
                atr_bracket["market_structure_validation"] = validate_structure_room(
                    structure, side=side, entry_price=entry_fill,
                    target_price=atr_bracket["target_price"], min_clearance_pct=0.10)

        # Independently verify the final stop-risk amount after the last fill and
        # execution-cost recalculation. Fail closed rather than exceed a budget.
        final_stop_pct = float(eff["stop_loss_pct"])
        final_risk_fraction = (final_stop_pct / 100.0
            + 2.0 * (float(trade_costs["fee_bps_per_side"])
                     + float(trade_costs["total_adverse_price_bps_per_side"])) / 10000.0)
        final_stop_risk = notional * final_risk_fraction
        if (not math.isfinite(final_stop_risk)
                or final_stop_risk > risk_budget_cash + max(1e-7, risk_budget_cash * 1e-7)):
            raise ValueError("ریسک نهایی پس از هزینه اجرای واقعی از بودجه مجاز بیشتر شد؛ ورود متوقف شد")
        sizing = dict(sizing)
        sizing.update({"notional": notional, "risk_fraction": final_risk_fraction,
                       "estimated_stop_risk": round(final_stop_risk, 8)})
        quantity = notional / entry_fill
        stop_price = entry_fill * (1 - direction * eff["stop_loss_pct"] / 100)
        target_price = entry_fill * (1 + direction * eff["take_profit_pct"] / 100)
        entry_fee = notional * fee_rate
        settings_json = json.dumps(eff, ensure_ascii=False, sort_keys=True)
        saved_decision_context = _sanitize_decision_context(decision_context or {})
        if not isinstance(saved_decision_context, dict):
            saved_decision_context = {}
        if atr_bracket is not None:
            atr_bracket = dict(atr_bracket)
            atr_bracket.update({"entry_price": round(entry_fill, 12),
                                "entry_time": time.time(),
                                "funding_included": False})
            saved_decision_context["atr_risk_bracket"] = atr_bracket
        entry_context = {
            "learning_version": LEARNING_VERSION,
            "entry_source": str(entry_source) if entry_source else "manual_paper_ui",
            "quote_source": quote.get("source", "public_rest_ticker"),
            "quote_timestamp": quote.get("timestamp"), "timeframe": timeframe,
            "requested_exchange": exchange, "settings_version": VERSION,
            "execution_cost_model": trade_costs,
            "entry_idempotency_key": idempotency_key,
            "portfolio_risk": {
                "risk_budget_cash": round(risk_budget_cash, 8),
                "estimated_stop_risk": sizing["estimated_stop_risk"],
                "risk_fraction": sizing["risk_fraction"],
                "portfolio_cap_cash": round(portfolio_cap, 8),
                "market_cap_cash": round(market_cap, 8),
                "directional_cap_cash": round(directional_cap, 8),
                "open_risk_before_entry": round(current_total_risk, 8),
            },
            "real_order_sent": False,
            "funding_engine_version": FUNDING_VERSION,
            "funding_accounting": "settled_public_rates_only" if market == "perp" else "not_applicable",
            "decision_context": saved_decision_context,
        }
        cur = c.execute("""INSERT INTO paper_live_trades(opened_at,symbol,market,exchange,requested_exchange,side,quantity,notional,
            reference_entry,entry_fill,entry_fee,execution_costs_json,stop_price,target_price,last_price,last_price_at,settings_json,timeframe,entry_context_json,
            entry_idempotency_key,funding_status)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (time.time(), symbol, market, quote["exchange"], exchange, side, quantity, notional, ref,
             entry_fill, entry_fee, json.dumps(trade_costs, sort_keys=True), stop_price, target_price, ref, time.time(), settings_json, timeframe,
             json.dumps(entry_context, ensure_ascii=False, sort_keys=True), idempotency_key,
             "PENDING" if market == "perp" else "NOT_APPLICABLE"))
        return {"id": cur.lastrowid, "symbol": symbol, "market": market, "exchange": quote["exchange"],
                "side": side, "quantity": quantity, "notional": notional, "reference_entry": ref,
                "entry_fill": entry_fill, "entry_fee": entry_fee, "execution_costs": trade_costs, "stop_price": stop_price,
                "target_price": target_price, "timeframe": timeframe, "settings": eff, "quote": quote,
                "estimated_stop_risk": sizing["estimated_stop_risk"],
                "portfolio_risk_budget": risk_budget_cash,
                "atr_risk_bracket": atr_bracket,
                "entry_idempotency_key": idempotency_key, "idempotent_replay": False, "status": "OPEN",
                "funding_status": "PENDING" if market == "perp" else "NOT_APPLICABLE"}


@_paper_ledger_writer_guard
def partial_close_position(trade_id: int, quantity: float, *, idempotency_key: str,
                           reason: str = "PARTIAL_MANUAL") -> dict:
    """Close part of an open spot paper position using its pinned exchange quote.

    Funding is allocated using the position quantity actually open at each
    settlement timestamp; delayed reconciliation remains idempotent.
    """
    init_db()
    key = str(idempotency_key or "").strip()[:120]
    if not key:
        raise ValueError("کلید یکتای درخواست خروج جزئی الزامی است")
    requested = _number(quantity, "مقدار خروج")
    with _connect() as c:
        c.row_factory = sqlite3.Row
        prior = c.execute("SELECT * FROM paper_partial_exits WHERE trade_id=? AND idempotency_key=?",
                          (int(trade_id), key)).fetchone()
        if prior:
            return {**dict(prior), "status": "PARTIAL", "idempotent_replay": True}
        row = c.execute("SELECT * FROM paper_live_trades WHERE id=? AND status='OPEN'", (int(trade_id),)).fetchone()
        if row is None:
            raise ValueError("موقعیت باز پیدا نشد یا قبلاً بسته شده است")
        prior_qty = c.execute("SELECT COALESCE(SUM(quantity),0) FROM paper_partial_exits WHERE trade_id=?",
                              (int(trade_id),)).fetchone()[0]
        from backend.partial_exit import validate_partial_quantity, calculate_partial_exit
        remaining = validate_partial_quantity(original_quantity=float(row["quantity"]),
            already_exited=float(prior_qty or 0), requested_quantity=requested)
        exchange = str(row["exchange"] or "").lower()
        symbol, market = row["symbol"], row["market"]
    quote = get_quote(symbol, market, exchange, use_cache=False)
    if str(quote.get("exchange") or "").lower() != exchange:
        raise RuntimeError("منبع قیمت خروج با صرافی ورود یکسان نیست؛ خروج جزئی انجام نشد")
    costs = _safe_json_object(row["execution_costs_json"])
    if not costs:
        legacy_cfg = dict(SETTINGS, spread_bps_full=0.0, impact_bps_per_1000_usdt=0.0,
                          max_impact_bps_per_side=0.0)
        costs = execution_costs(float(row["notional"]), legacy_cfg)
    allocated_entry_fee = float(row["entry_fee"]) * requested / float(row["quantity"])
    calc = calculate_partial_exit(side=row["side"], quantity=requested,
        entry_fill=float(row["entry_fill"]), entry_fee_allocated=allocated_entry_fee,
        exit_reference=float(quote["price"]), execution_costs=costs)
    with _connect() as c:
        c.row_factory = sqlite3.Row
        c.execute("BEGIN IMMEDIATE")
        current = c.execute("SELECT * FROM paper_live_trades WHERE id=? AND status='OPEN'", (int(trade_id),)).fetchone()
        if current is None:
            raise ValueError("موقعیت در زمان ثبت خروج جزئی دیگر باز نیست")
        duplicate = c.execute("SELECT * FROM paper_partial_exits WHERE trade_id=? AND idempotency_key=?",
                              (int(trade_id), key)).fetchone()
        if duplicate:
            return {**dict(duplicate), "status": "PARTIAL", "idempotent_replay": True}
        current_exited = float(c.execute("SELECT COALESCE(SUM(quantity),0) FROM paper_partial_exits WHERE trade_id=?",
                                          (int(trade_id),)).fetchone()[0] or 0)
        validate_partial_quantity(original_quantity=float(current["quantity"]),
            already_exited=current_exited, requested_quantity=requested)
        cur = c.execute("""INSERT INTO paper_partial_exits(trade_id,idempotency_key,created_at,quantity,
            reference_exit,exit_fill,entry_fee_allocated,exit_fee,gross_pnl,net_pnl,reason)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (int(trade_id), key, time.time(), requested, calc["reference_exit"], calc["exit_fill"],
             calc["entry_fee_allocated"], calc["exit_fee"], calc["gross_pnl"], calc["net_pnl"], str(reason)[:80]))
    return {"id": int(trade_id), "partial_exit_id": cur.lastrowid, **calc,
            "remaining_quantity": remaining, "status": "PARTIAL", "idempotent_replay": False,
            "quote": quote, "real_order_sent": False}


@_paper_ledger_writer_guard
def close_position(trade_id: int) -> dict:
    init_db()
    with _connect() as c:
        row = c.execute("SELECT symbol,market,exchange,requested_exchange FROM paper_live_trades WHERE id=? AND status='OPEN'", (int(trade_id),)).fetchone()
    if not row:
        raise ValueError("موقعیت باز پیدا نشد یا قبلاً بسته شده است")
    symbol, market, exchange, requested_exchange = row
    # Pin an open position to the exact venue that supplied its entry quote.
    # `requested_exchange` may be "auto"; using it here could silently switch
    # venues at exit and mix two different market prices in one simulated trade.
    quote = get_quote(symbol, market, exchange, use_cache=False)
    if str(quote.get("exchange") or "").lower() != str(exchange or "").lower():
        raise RuntimeError("منبع قیمت خروج با صرافی ورود یکسان نیست؛ موقعیت باز باقی ماند")
    with _connect() as c:
        c.execute("BEGIN IMMEDIATE")
        result = _closed_trade(c, int(trade_id), float(quote["price"]), "MANUAL")
    if str(market).lower() == "perp":
        # Sync after commit so the history window includes the final close time.
        # API failure never blocks the simulated close; the closed trade remains flagged.
        sync_open_funding_positions(trade_id=int(trade_id), force=True)
        with _connect() as c:
            c.row_factory = sqlite3.Row
            final_row = c.execute("SELECT net_pnl,funding_total,funding_event_count,funding_status,funding_error FROM paper_live_trades WHERE id=?",
                                  (int(trade_id),)).fetchone()
        if final_row is not None:
            result.update(dict(final_row))
    result["quote"] = quote
    return result


def _estimate_open_net_pnl(row: dict, price: float) -> float:
    """Estimate unrealized PnL after exit slippage and both-side fees."""
    side = str(row.get("side") or "LONG").upper()
    direction = 1 if side == "LONG" else -1
    costs = _safe_json_object(row.get("execution_costs_json"))
    if not costs.get("total_adverse_price_bps_per_side"):
        legacy_cfg = dict(SETTINGS, spread_bps_full=0.0,
                          impact_bps_per_1000_usdt=0.0, max_impact_bps_per_side=0.0)
        costs = execution_costs(float(row.get("notional") or 1000.0), legacy_cfg)
    fee_rate = float(costs["fee_bps_per_side"]) / 10000.0
    estimated_exit_fill = fill_price(float(price), side, "exit", costs)
    estimated_exit_fee = float(row["quantity"]) * estimated_exit_fill * fee_rate
    gross_est = direction * float(row["quantity"]) * (estimated_exit_fill - float(row["entry_fill"]))
    funding_total = float(row.get("funding_total") or 0.0)
    return gross_est - float(row["entry_fee"]) - estimated_exit_fee + funding_total


def _apply_remaining_position(c: sqlite3.Connection, row: dict) -> dict:
    """Project immutable original trade fields into its currently open remainder."""
    original = float(row.get("quantity") or 0.0)
    partials = c.execute("SELECT COALESCE(SUM(quantity),0) AS quantity, "
                         "COALESCE(SUM(net_pnl),0) AS net_pnl, COUNT(*) AS count "
                         "FROM paper_partial_exits WHERE trade_id=?", (int(row["id"]),)).fetchone()
    exited = float(partials[0] or 0.0)
    row["original_quantity"] = original
    row["partial_exited_quantity"] = exited
    row["partial_realized_net_pnl"] = float(partials[1] or 0.0)
    row["partial_exit_count"] = int(partials[2] or 0)
    if exited > 0 and original > 0:
        ratio = max(0.0, (original - exited) / original)
        row["quantity"] = original - exited
        row["notional"] = float(row.get("notional") or 0.0) * ratio
        row["entry_fee"] = float(row.get("entry_fee") or 0.0) * ratio
    return row


@_paper_ledger_writer_guard
def replay_position_candles(trade_id: int, candles: list[dict], *, now_ms: int | None = None) -> dict:
    """Persistently replay caller-supplied CLOSED OHLC candles for one PAPER trade.

    Candle retrieval is deliberately outside this function: callers must fetch
    from the trade's pinned exchange/symbol/timeframe and pass a complete batch.
    Cursor advancement and a triggered close share one SQLite transaction.
    """
    from backend.paper_candle_replay import replay_closed_candles

    init_db()
    with _connect() as c:
        c.row_factory = sqlite3.Row
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT * FROM paper_live_trades WHERE id=?", (int(trade_id),)).fetchone()
        if row is None:
            raise ValueError("موقعیت آزمایشی پیدا نشد")
        if str(row["status"]) != "OPEN":
            return {"trade_id": int(trade_id), "status": "ALREADY_CLOSED",
                    "last_processed_open_ms": row["replay_last_candle_open_ms"]}
        if str(row["exchange"]).lower() not in EXCHANGE_NAMES:
            raise ValueError("صرافی ثبت‌شده برای بازپخش معتبر نیست")
        try:
            seconds = timeframe_seconds(str(row["timeframe"]))
        except Exception as exc:
            raise ValueError("تایم‌فریم معامله برای بازپخش معتبر نیست") from exc
        from backend.trade_contract import TRAIL_TRIGGER_PCT, TRAIL_DISTANCE_PCT
        result = replay_closed_candles(
            side=str(row["side"]), stop_price=float(row["stop_price"]),
            target_price=float(row["target_price"]), candles=candles,
            timeframe_seconds=seconds,
            last_processed_open_ms=(int(row["replay_last_candle_open_ms"])
                if row["replay_last_candle_open_ms"] is not None else None),
            opened_at_ms=int(float(row["opened_at"]) * 1000), now_ms=now_ms,
            horizon_bars=TRADE_HORIZON_BARS,
            trailing_trigger_pct=TRAIL_TRIGGER_PCT,
            trailing_distance_pct=TRAIL_DISTANCE_PCT,
            trailing_peak_price=row["trailing_peak_price"],
            trailing_active=bool(row["trailing_active"]),
            entry_price=float(row["entry_fill"]))
        cursor = result.get("last_processed_open_ms")
        # Commit the evolving protective state with the replay cursor so a
        # restart cannot lose trailing progress or reprocess the same candle.
        c.execute("UPDATE paper_live_trades SET stop_price=?,trailing_peak_price=?,trailing_active=? WHERE id=? AND status='OPEN'",
                  (float(result.get("stop_price") or row["stop_price"]),
                   result.get("trailing_peak_price"), int(bool(result.get("trailing_active"))), int(trade_id)))
        if result["exit"]:
            exit_event = result["exit"]
            closed = _closed_trade(c, int(trade_id), float(exit_event["fill_reference"]),
                                   str(exit_event["reason"]))
            c.execute("UPDATE paper_live_trades SET replay_last_candle_open_ms=?, replay_status='EXITED', replay_error=NULL WHERE id=?",
                      (cursor, int(trade_id)))
            result["closed_trade"] = closed
        else:
            c.execute("UPDATE paper_live_trades SET replay_last_candle_open_ms=?, replay_status='CURRENT', replay_error=NULL WHERE id=? AND status='OPEN'",
                      (cursor, int(trade_id)))
        result["trade_id"] = int(trade_id)
        return result


def fetch_pinned_closed_candles(row: dict, *, limit: int = 1000) -> list[dict]:
    """Fetch closed OHLC candles from the trade's pinned public venue.

    Binance, Bybit and OKX are supported. Other venues fail closed; no venue
    substitution is allowed. Returned candles are normalized for replay.
    """
    exchange = str(row.get("exchange") or "").lower()
    market = str(row.get("market") or "spot").lower()
    symbol = str(row.get("symbol") or "").upper()
    timeframe = str(row.get("timeframe") or "")
    if exchange not in EXCHANGE_NAMES:
        raise RuntimeError("OHLCV replay unsupported for pinned exchange")
    if market not in ("spot", "perp") or not SYMBOL_RE.fullmatch(symbol):
        raise RuntimeError("invalid pinned market or symbol")
    seconds = timeframe_seconds(timeframe)
    now_ms = int(time.time() * 1000)
    cursor = row.get("replay_last_candle_open_ms")
    start_ms = int(cursor) + seconds * 1000 if cursor is not None else int(float(row["opened_at"]) * 1000)
    start_ms = max(0, start_ms - start_ms % (seconds * 1000))
    limit = max(2, min(int(limit), 1000))
    if exchange == "binance":
        url = "https://api.binance.com/api/v3/klines" if market == "spot" else "https://fapi.binance.com/fapi/v1/klines"
        raw = _http_json(url, {"symbol": symbol, "interval": timeframe, "startTime": start_ms, "limit": limit})
        rows = [{"t": int(x[0]), "open": float(x[1]), "high": float(x[2]), "low": float(x[3]), "close": float(x[4])} for x in raw]
    elif exchange == "bybit":
        interval = {"5m":"5", "15m":"15", "30m":"30", "1h":"60", "4h":"240", "1d":"D"}[timeframe]
        payload = _http_json("https://api.bybit.com/v5/market/kline", {"category":"spot" if market == "spot" else "linear", "symbol":symbol, "interval":interval, "start":start_ms, "limit":limit})
        if str(payload.get("retCode", "0")) != "0": raise RuntimeError("Bybit OHLCV API error")
        raw = (payload.get("result") or {}).get("list") or []
        rows = [{"t":int(x[0]), "open":float(x[1]), "high":float(x[2]), "low":float(x[3]), "close":float(x[4])} for x in raw]
    elif exchange == "okx":
        inst = _market_symbol(symbol, market, exchange)
        bar = {"1d":"1D"}.get(timeframe, timeframe)
        payload = _http_json("https://www.okx.com/api/v5/market/history-candles", {"instId":inst, "bar":bar, "after":str(now_ms), "before":str(start_ms), "limit":str(limit)})
        if str(payload.get("code", "0")) != "0":
            raise RuntimeError("OKX OHLCV API error")
        raw = payload.get("data") or []
        rows = [{"t":int(x[0]), "open":float(x[1]), "high":float(x[2]), "low":float(x[3]), "close":float(x[4])} for x in raw if len(x) >= 9 and str(x[8]) == "1"]
    elif exchange == "gateio":
        interval = timeframe
        if market == "spot":
            pair = symbol.replace("USDT", "_USDT").replace("USDC", "_USDC")
            raw = _http_json("https://api.gateio.ws/api/v4/spot/candlesticks", {
                "currency_pair": pair, "interval": interval, "from": start_ms // 1000,
                "to": now_ms // 1000, "limit": min(limit, 1000)})
            if not isinstance(raw, list):
                raise RuntimeError("Gate.io spot OHLCV response invalid")
            rows = [{"t":int(x[0]) * 1000, "open":float(x[5]), "high":float(x[3]),
                     "low":float(x[4]), "close":float(x[2])} for x in raw if len(x) >= 6]
        else:
            contract = symbol.replace("USDT", "_USDT").replace("USDC", "_USDC")
            raw = _http_json("https://api.gateio.ws/api/v4/futures/usdt/candlesticks", {
                "contract": contract, "interval": interval, "from": start_ms // 1000,
                "to": now_ms // 1000, "limit": min(limit, 1000)})
            if not isinstance(raw, list):
                raise RuntimeError("Gate.io futures OHLCV response invalid")
            # Gate.io futures candlesticks are normally arrays in the order
            # [timestamp, volume, close, high, low, open]. Accept the documented
            # array shape and the keyed shape used by some compatible gateways.
            rows = []
            for item in raw:
                if isinstance(item, dict) and "t" in item:
                    rows.append({"t": int(item["t"]) * 1000,
                                 "open": float(item["o"]), "high": float(item["h"]),
                                 "low": float(item["l"]), "close": float(item["c"])})
                elif isinstance(item, (list, tuple)) and len(item) >= 6:
                    rows.append({"t": int(item[0]) * 1000,
                                 "open": float(item[5]), "high": float(item[3]),
                                 "low": float(item[4]), "close": float(item[2])})
                else:
                    raise RuntimeError("Gate.io futures OHLCV row shape invalid")
    elif exchange == "mexc":
        if market == "spot":
            interval = {"1h":"60m"}.get(timeframe, timeframe)
            raw = _http_json("https://api.mexc.com/api/v3/klines", {
                "symbol": symbol, "interval": interval, "startTime": start_ms,
                "endTime": now_ms, "limit": min(limit, 1000)})
            if not isinstance(raw, list):
                raise RuntimeError("MEXC spot OHLCV response invalid")
            rows = [{"t":int(x[0]), "open":float(x[1]), "high":float(x[2]),
                     "low":float(x[3]), "close":float(x[4])} for x in raw if len(x) >= 5]
        else:
            contract = symbol.replace("USDT", "_USDT").replace("USDC", "_USDC")
            interval = {"5m":"Min5", "15m":"Min15", "30m":"Min30", "1h":"Min60",
                        "4h":"Hour4", "1d":"Day1"}[timeframe]
            payload = _http_json(f"https://contract.mexc.com/api/v1/contract/kline/{contract}", {
                "interval": interval, "start": start_ms // 1000, "end": now_ms // 1000})
            if payload.get("success") is not True:
                raise RuntimeError("MEXC futures OHLCV API error")
            data = payload.get("data") or {}
            keys = ("time", "open", "high", "low", "close")
            if any(not isinstance(data.get(k), list) for k in keys):
                raise RuntimeError("MEXC futures OHLCV shape invalid")
            rows = [{"t":int(data["time"][i]) * 1000, "open":float(data["open"][i]),
                     "high":float(data["high"][i]), "low":float(data["low"][i]),
                     "close":float(data["close"][i])} for i in range(min(len(data[k]) for k in keys))]
    else:  # Bitget
        if market == "spot":
            granularity = {"5m":"5min", "15m":"15min", "30m":"30min", "1h":"1h", "4h":"4h", "1d":"1day"}[timeframe]
            url = "https://api.bitget.com/api/v2/spot/market/candles"
            params = {"symbol":symbol, "granularity":granularity, "startTime":start_ms,
                      "endTime":now_ms, "limit":str(min(limit, 1000))}
        else:
            granularity = {"5m":"5m", "15m":"15m", "30m":"30m", "1h":"1H", "4h":"4H", "1d":"1D"}[timeframe]
            url = "https://api.bitget.com/api/v2/mix/market/candles"
            params = {"symbol":symbol, "productType":"USDT-FUTURES", "granularity":granularity,
                      "startTime":start_ms, "endTime":now_ms, "limit":str(min(limit, 1000))}
        payload = _http_json(url, params)
        if str(payload.get("code", "00000")) != "00000":
            raise RuntimeError("Bitget OHLCV API error")
        raw = payload.get("data") or []
        rows = [{"t":int(x[0]), "open":float(x[1]), "high":float(x[2]),
                 "low":float(x[3]), "close":float(x[4])} for x in raw if len(x) >= 5]
    rows.sort(key=lambda x: x["t"])
    # Reject malformed prices rather than silently replaying corrupted bars.
    for candle in rows:
        values = (candle["open"], candle["high"], candle["low"], candle["close"])
        if (not all(math.isfinite(v) and v > 0 for v in values)
                or candle["low"] > min(candle["open"], candle["close"])
                or candle["high"] < max(candle["open"], candle["close"])
                or candle["low"] > candle["high"]):
            raise RuntimeError("OHLCV candle values invalid")
    if len(rows) > 1 and any(rows[i]["t"] == rows[i-1]["t"] for i in range(1, len(rows))):
        raise RuntimeError("OHLCV duplicate timestamps")
    return [x for x in rows if x["t"] + seconds * 1000 <= now_ms]


def fetch_pinned_closed_candles_complete(row: dict, *, page_limit: int = 1000,
                                         max_pages: int = 10) -> list[dict]:
    """Fetch a bounded sequence of pages from the trade's pinned venue.

    Each subsequent request starts strictly after the last returned candle.
    The helper deliberately caps one refresh to 10,000 bars; if a longer
    outage exists, the next refresh resumes from the durable replay cursor.
    It never changes venue and never treats an empty/short page as permission
    to skip a detected timestamp gap (the replay engine validates continuity).
    """
    page_limit = max(2, min(int(page_limit), 1000))
    max_pages = max(1, min(int(max_pages), 10))
    page_row = dict(row)
    collected: list[dict] = []
    last_timestamp = None
    for _ in range(max_pages):
        page = fetch_pinned_closed_candles(page_row, limit=page_limit)
        if not page:
            break
        page = sorted(page, key=lambda item: int(item["t"]))
        if last_timestamp is not None and int(page[0]["t"]) <= last_timestamp:
            raise RuntimeError("OHLCV pagination did not advance monotonically")
        if any(int(page[i]["t"]) <= int(page[i-1]["t"])
               for i in range(1, len(page))):
            raise RuntimeError("OHLCV page contains duplicate or reordered candles")
        collected.extend(page)
        last_timestamp = int(page[-1]["t"])
        if len(page) < page_limit:
            break
        page_row["replay_last_candle_open_ms"] = last_timestamp
    return collected


def _refresh_open_positions(open_rows: list[dict]) -> list[dict]:
    """Refresh pinned venue quotes outside SQLite transactions, then persist each mark.

    Network calls must never run while holding a SQLite write transaction. Each
    position is also re-read under BEGIN IMMEDIATE before a stop/target decision
    so a concurrent manual close or trailing-stop update cannot be overwritten.
    """
    if not open_rows:
        return []
    # Keep the historical trade quantity immutable; expose only the unclosed
    # remainder to risk and mark-to-market calculations.
    with _connect() as c:
        open_rows = [_apply_remaining_position(c, item) for item in open_rows]

    def fetch_pinned(row: dict) -> dict:
        pinned_exchange = str(row.get("exchange") or "").lower().strip()
        if pinned_exchange not in EXCHANGE_NAMES:
            raise RuntimeError("صرافی ثبت‌شده برای این موقعیت معتبر نیست؛ قیمت جایگزین استفاده نشد")
        candles = fetch_pinned_closed_candles_complete(row)
        replay = replay_position_candles(int(row["id"]), candles) if candles else None
        if replay and replay.get("exit"):
            return {"replay": replay, "closed": True}
        quote = get_quote(row["symbol"], row["market"], pinned_exchange, use_cache=False)
        if str(quote.get("exchange") or "").lower() != pinned_exchange:
            raise RuntimeError("منبع قیمت با صرافی ورود یکسان نیست؛ پایش متوقف شد")
        if str(quote.get("symbol") or row["symbol"]).upper() != str(row["symbol"]).upper():
            raise RuntimeError("نماد قیمت دریافتی با موقعیت مطابقت ندارد")
        if str(quote.get("market") or row["market"]).lower() != str(row["market"]).lower():
            raise RuntimeError("نوع بازار قیمت دریافتی با موقعیت مطابقت ندارد")
        price = _number(quote.get("price"), "قیمت")
        checked_at = float(quote.get("checked_at_epoch") or time.time())
        max_age = max(15.0, float(SETTINGS.get("quote_refresh_seconds", 10)) * 3.0)
        age = time.time() - checked_at
        if age < -2.0 or age > max_age:
            raise RuntimeError(f"قیمت صرافی قدیمی است؛ سن قیمت {max(0.0, age):.1f} ثانیه")
        return {"quote": quote, "price": price, "checked_at": checked_at, "replay": replay, "closed": False}

    # Fetch in parallel to avoid making the manager's latency proportional to
    # the sum of all exchange REST timeouts. The pool is deliberately bounded.
    fetched: dict[int, dict] = {}
    errors: dict[int, str] = {}
    fetch_started: dict[int, float] = {}
    with ThreadPoolExecutor(max_workers=min(8, len(open_rows))) as pool:
        futures = {}
        for row in open_rows:
            trade_id = int(row["id"])
            fetch_started[trade_id] = time.time()
            futures[pool.submit(fetch_pinned, row)] = trade_id
        for future in as_completed(futures):
            trade_id = futures[future]
            try:
                fetched[trade_id] = future.result()
            except Exception as exc:
                errors[trade_id] = str(exc)[:160]

    refreshed: list[dict] = []
    for snapshot in open_rows:
        trade_id = int(snapshot["id"])
        if trade_id in errors:
            # Re-read status in case another worker closed the trade while the
            # REST request was in flight. Do not expose stale unrealized PnL.
            with _connect() as c:
                c.row_factory = sqlite3.Row
                current = c.execute("SELECT * FROM paper_live_trades WHERE id=?", (trade_id,)).fetchone()
            row = dict(current) if current else dict(snapshot)
            if row.get("status") == "OPEN":
                with _connect() as c:
                    row = _apply_remaining_position(c, row)
                latest_mark_at = float(row.get("last_price_at") or 0.0)
                # A different, newer refresh worker may have committed a mark
                # after this failed request started. Retain that valid pinned
                # mark instead of incorrectly downgrading the position.
                if latest_mark_at > fetch_started.get(trade_id, 0.0) and row.get("last_price") is not None:
                    row.update({"quote_status": "LIVE", "quote_error": None,
                                "unrealized_net_pnl": _estimate_open_net_pnl(row, float(row["last_price"])),
                                "live_exchange": row.get("exchange"),
                                "quote_timestamp": None, "quote_mark_source": "newer_persisted_mark"})
                else:
                    row.update({"quote_status": "DISCONNECTED", "quote_error": errors[trade_id],
                                "unrealized_net_pnl": None, "live_exchange": None})
            else:
                row.update({"quote_status": "NOT_REQUIRED", "unrealized_net_pnl": None})
            refreshed.append(row)
            continue

        result = fetched[trade_id]
        if result.get("closed"):
            with _connect() as c:
                c.row_factory = sqlite3.Row
                latest = c.execute("SELECT * FROM paper_live_trades WHERE id=?", (trade_id,)).fetchone()
            row = dict(latest) if latest else dict(snapshot)
            row.update({"quote_status": "NOT_REQUIRED", "unrealized_net_pnl": None,
                        "replay_status": "EXITED"})
            refreshed.append(row)
            continue
        quote = result["quote"]
        price = result["price"]
        checked_at = result["checked_at"]
        with _connect() as c:
            c.row_factory = sqlite3.Row
            c.execute("BEGIN IMMEDIATE")
            current = c.execute("SELECT * FROM paper_live_trades WHERE id=? AND status='OPEN'", (trade_id,)).fetchone()
            if current is None:
                latest = c.execute("SELECT * FROM paper_live_trades WHERE id=?", (trade_id,)).fetchone()
                row = dict(latest) if latest else dict(snapshot)
                row.update({"quote_status": "NOT_REQUIRED", "unrealized_net_pnl": None})
                refreshed.append(row)
                continue

            row = _apply_remaining_position(c, dict(current))
            row["funding_event_count"] = _funding_event_count(c, trade_id)
            # Concurrent manager/preflight refreshes can complete out of order.
            # Never let an older quote response overwrite a newer mark already
            # committed for this same pinned exchange.
            stored_mark_at = float(row.get("last_price_at") or 0.0)
            used_newer_stored_mark = stored_mark_at > checked_at
            if used_newer_stored_mark:
                price = _number(row.get("last_price"), "آخرین قیمت ذخیره‌شده")
                checked_at = stored_mark_at
            side = str(row["side"]).upper()
            stop = float(row["stop_price"])
            target = float(row["target_price"])
            # Time exit mirrors the 12-bar training/backtest horizon. It uses
            # elapsed timeframe duration as a conservative live approximation;
            # exact missed-candle replay is handled in the later simulator stage.
            try:
                bar_seconds = timeframe_seconds(str(row.get("timeframe") or ""))
                horizon_seconds = TRADE_HORIZON_BARS * bar_seconds
            except ValueError:
                horizon_seconds = None
            opened_at = float(row.get("opened_at") or checked_at)
            if horizon_seconds and checked_at - opened_at >= horizon_seconds:
                _closed_trade(c, trade_id, price, "TIME_EXIT")
                latest = c.execute("SELECT * FROM paper_live_trades WHERE id=?", (trade_id,)).fetchone()
                row = dict(latest) if latest else row
                row.update({"quote_status": "LIVE", "live_exchange": quote["exchange"],
                            "quote_timestamp": None if used_newer_stored_mark else quote.get("timestamp"),
                            "quote_mark_source": "time_horizon_exit", "unrealized_net_pnl": None})
                refreshed.append(row)
                continue
            # Prefer a complete, validated OHLC candle when the quote provider
            # supplies one. Plain ticker quotes cannot reveal intrabar touches.
            candle = quote.get("candle") if isinstance(quote, dict) else None
            if isinstance(candle, dict):
                bracket = evaluate_bracket_candle(side=side, stop_price=stop,
                                                  target_price=target, candle=candle)
                hit_stop = bracket["stop_hit"]
                hit_target = bracket["target_hit"]
                reason = bracket["reason"]
                fill_reference = bracket["fill_reference"]
            else:
                # Ticker-only fallback: evaluate the observed mark only. This
                # cannot detect a stop/target touched between quote refreshes.
                hit_stop = price <= stop if side == "LONG" else price >= stop
                hit_target = price >= target if side == "LONG" else price <= target
                reason = "STOP_LOSS" if hit_stop else ("TAKE_PROFIT" if hit_target else None)
                fill_reference = price if hit_stop else (target if hit_target else None)
            if hit_stop or hit_target:
                _closed_trade(c, trade_id, fill_reference, reason)
                latest = c.execute("SELECT * FROM paper_live_trades WHERE id=?", (trade_id,)).fetchone()
                row = dict(latest) if latest else row
                row.update({"quote_status": "LIVE", "live_exchange": quote["exchange"],
                            "quote_timestamp": None if used_newer_stored_mark else quote.get("timestamp"),
                            "quote_mark_source": "newer_persisted_mark" if used_newer_stored_mark else "fresh_exchange_quote",
                            "unrealized_net_pnl": None})
                refreshed.append(row)
                continue

            c.execute("UPDATE paper_live_trades SET last_price=?,last_price_at=? WHERE id=? AND status='OPEN'",
                      (price, checked_at, trade_id))
            upnl = _estimate_open_net_pnl(row, price)
            row.update({"last_price": price, "last_price_at": checked_at,
                        "unrealized_net_pnl": upnl, "live_exchange": quote["exchange"],
                        "quote_timestamp": None if used_newer_stored_mark else quote.get("timestamp"),
                        "quote_mark_source": "newer_persisted_mark" if used_newer_stored_mark else "fresh_exchange_quote",
                        "quote_status": "LIVE"})
            refreshed.append(row)
    return refreshed


def validate_paper_ledger() -> dict:
    """Read-only startup integrity check; never repairs or rewrites trade history."""
    # Schema creation/migrations are allowed, but legacy learning backfill is
    # intentionally disabled here: a validator must not repair the evidence it audits.
    init_db(backfill_learning=False)
    errors: list[str] = []
    with _connect() as c:
        total = int(c.execute("SELECT COUNT(*) FROM paper_live_trades").fetchone()[0] or 0)
        open_bad = int(c.execute("""SELECT COUNT(*) FROM paper_live_trades
            WHERE status='OPEN' AND closed_at IS NOT NULL""").fetchone()[0] or 0)
        closed_bad = int(c.execute("""SELECT COUNT(*) FROM paper_live_trades
            WHERE status='CLOSED' AND (closed_at IS NULL OR exit_fill IS NULL OR net_pnl IS NULL)""").fetchone()[0] or 0)
        status_bad = int(c.execute("SELECT COUNT(*) FROM paper_live_trades WHERE status NOT IN ('OPEN','CLOSED')").fetchone()[0] or 0)
        numeric_bad = int(c.execute("""SELECT COUNT(*) FROM paper_live_trades WHERE
            quantity<=0 OR notional<=0 OR reference_entry<=0 OR entry_fill<=0 OR
            stop_price<=0 OR target_price<=0 OR
            quantity>1.0e100 OR notional>1.0e100 OR entry_fill>1.0e100""").fetchone()[0] or 0)
        orphan_funding = int(c.execute("""SELECT COUNT(*) FROM paper_funding_events f
            LEFT JOIN paper_live_trades t ON t.id=f.trade_id WHERE t.id IS NULL""").fetchone()[0] or 0)
        invalid_funding_events = int(c.execute("""SELECT COUNT(*) FROM paper_funding_events
            WHERE settlement_ts_ms<0 OR NOT (funding_rate=funding_rate)
               OR ABS(funding_rate)>1 OR event_notional<0 OR position_quantity<0
               OR partial_exited_quantity<0 OR ABS(cashflow)>1.0e100""").fetchone()[0] or 0)
        partial_quantity_overruns = int(c.execute("""SELECT COUNT(*) FROM (
            SELECT t.id FROM paper_live_trades t JOIN paper_partial_exits p ON p.trade_id=t.id
            GROUP BY t.id,t.quantity HAVING SUM(p.quantity)>t.quantity+0.0000001)""").fetchone()[0] or 0)
        invalid_partial_exits = int(c.execute("""SELECT COUNT(*) FROM paper_partial_exits
            WHERE quantity<=0 OR reference_exit<=0 OR exit_fill<=0 OR entry_fee_allocated<0
               OR exit_fee<0 OR ABS(net_pnl)>1.0e100 OR ABS(gross_pnl)>1.0e100""").fetchone()[0] or 0)
        invalid_replay_state = int(c.execute("""SELECT COUNT(*) FROM paper_live_trades
            WHERE replay_status NOT IN ('PENDING','CURRENT','EXITED','ERROR')
               OR replay_last_candle_open_ms<0
               OR (replay_status='EXITED' AND status!='CLOSED')""").fetchone()[0] or 0)
        duplicate_keys = int(c.execute("""SELECT COUNT(*) FROM (
            SELECT entry_idempotency_key FROM paper_live_trades
            WHERE entry_idempotency_key IS NOT NULL GROUP BY entry_idempotency_key HAVING COUNT(*)>1)""").fetchone()[0] or 0)
        # Learning outcomes are committed in the same SQLite transaction as a
        # close. Detect broken links or values that diverge from the trade ledger.
        learning_orphans = int(c.execute("""SELECT COUNT(*) FROM paper_learning_events l
            LEFT JOIN paper_live_trades t ON t.id=l.trade_id WHERE t.id IS NULL OR t.status!='CLOSED'""").fetchone()[0] or 0)
        learning_duplicates = int(c.execute("""SELECT COUNT(*) FROM (
            SELECT trade_id FROM paper_learning_events GROUP BY trade_id HAVING COUNT(*)>1)""").fetchone()[0] or 0)
        learning_mismatches = int(c.execute("""SELECT COUNT(*) FROM paper_learning_events l
            JOIN paper_live_trades t ON t.id=l.trade_id
            WHERE ABS(COALESCE(l.net_pnl,0)-COALESCE(t.net_pnl,0))>0.0000001
               OR ABS(COALESCE(l.closed_at,0)-COALESCE(t.closed_at,0))>0.001""").fetchone()[0] or 0)
        learning_missing = int(c.execute("""SELECT COUNT(*) FROM paper_live_trades t
            LEFT JOIN paper_learning_events l ON l.trade_id=t.id
            WHERE t.status='CLOSED' AND (t.market!='perp' OR t.funding_status='SYNCED') AND l.trade_id IS NULL""").fetchone()[0] or 0)
    checks = {"open_rows_with_close_time": open_bad, "incomplete_closed_rows": closed_bad,
              "unknown_status_rows": status_bad, "invalid_trade_numeric_rows": numeric_bad,
              "orphan_funding_events": orphan_funding, "invalid_funding_events": invalid_funding_events,
              "partial_quantity_overruns": partial_quantity_overruns,
              "invalid_partial_exits": invalid_partial_exits,
              "invalid_replay_state": invalid_replay_state, "duplicate_entry_keys": duplicate_keys,
              "orphan_learning_events": learning_orphans, "duplicate_learning_events": learning_duplicates,
              "learning_trade_mismatches": learning_mismatches,
              "missing_reconciled_learning_events": learning_missing}
    errors.extend(f"{name}:{count}" for name, count in checks.items() if count)
    return {"valid": not errors, "errors": errors, "checks": checks, "trade_rows": total,
            "read_only": True, "blocks_new_entries": bool(errors)}


def reconcile_trade_pnl(trade_id: int | None = None, *, tolerance: float = 1e-7) -> dict:
    """Read-only reconciliation of partial exits, fees, funding and closed PnL."""
    init_db(backfill_learning=False)
    if not math.isfinite(float(tolerance)) or float(tolerance) < 0:
        raise ValueError("تلورانس تطبیق نامعتبر است")
    issues: list[dict] = []
    rows_out: list[dict] = []
    with _connect() as c:
        c.row_factory = sqlite3.Row
        sql = "SELECT * FROM paper_live_trades"
        args: tuple = ()
        if trade_id is not None:
            sql += " WHERE id=?"
            args = (int(trade_id),)
        trades = c.execute(sql + " ORDER BY id", args).fetchall()
        if trade_id is not None and not trades:
            raise ValueError("معامله موردنظر پیدا نشد")
        for trade in trades:
            tid = int(trade["id"])
            partials = c.execute("SELECT quantity,entry_fee_allocated,exit_fee,gross_pnl,net_pnl FROM paper_partial_exits WHERE trade_id=?", (tid,)).fetchall()
            funding = c.execute("SELECT COALESCE(SUM(cashflow),0),COUNT(*) FROM paper_funding_events WHERE trade_id=?", (tid,)).fetchone()
            partial_qty = sum(float(x["quantity"] or 0) for x in partials)
            partial_entry_fee = sum(float(x["entry_fee_allocated"] or 0) for x in partials)
            partial_exit_fee = sum(float(x["exit_fee"] or 0) for x in partials)
            partial_gross = sum(float(x["gross_pnl"] or 0) for x in partials)
            partial_net = sum(float(x["net_pnl"] or 0) for x in partials)
            funding_sum, funding_count = float(funding[0] or 0), int(funding[1] or 0)
            checks = {
                "partial_quantity_exceeds_original": partial_qty - float(trade["quantity"] or 0),
                "partial_entry_fee_exceeds_total": partial_entry_fee - float(trade["entry_fee"] or 0),
            }
            if trade["status"] == "CLOSED":
                expected_net = (float(trade["gross_pnl"] or 0) - float(trade["entry_fee"] or 0)
                                - float(trade["exit_fee"] or 0) + funding_sum)
                checks["closed_net_pnl_mismatch"] = float(trade["net_pnl"] or 0) - expected_net
                checks["funding_total_mismatch"] = float(trade["funding_total"] or 0) - funding_sum
                checks["funding_event_count_mismatch"] = float(trade["funding_event_count"] or 0) - funding_count
                checks["partial_exit_fee_exceeds_total"] = partial_exit_fee - float(trade["exit_fee"] or 0)
            failed = [name for name, delta in checks.items() if (delta > float(tolerance) if "exceeds" in name else abs(delta) > float(tolerance))]
            for name in failed:
                issues.append({"trade_id": tid, "check": name, "delta": checks[name]})
            rows_out.append({"trade_id": tid, "status": trade["status"], "partial_exit_count": len(partials),
                             "partial_quantity": partial_qty, "remaining_quantity": max(0.0, float(trade["quantity"] or 0)-partial_qty),
                             "partial_realized_net_pnl": partial_net, "funding_event_sum": funding_sum,
                             "recorded_funding_total": float(trade["funding_total"] or 0),
                             "recorded_net_pnl": trade["net_pnl"], "checks_passed": not failed})
    return {"valid": not issues, "read_only": True, "trade_count": len(rows_out),
            "issue_count": len(issues), "issues": issues, "trades": rows_out}


def reconcile_account_equity(*, tolerance: float = 1e-7) -> dict:
    """Read-only ledger reconciliation; floating equity is marked unavailable when positions remain open."""
    init_db(backfill_learning=False)
    if not math.isfinite(float(tolerance)) or float(tolerance) < 0:
        raise ValueError("تلورانس تطبیق نامعتبر است")
    with _connect() as c:
        c.row_factory = sqlite3.Row
        meta = {str(r["key"]): str(r["value"]) for r in c.execute(
            "SELECT key,value FROM paper_live_meta WHERE key IN ('initial_balance','peak_equity')").fetchall()}
        closed = float(c.execute("SELECT COALESCE(SUM(net_pnl),0) FROM paper_live_trades WHERE status='CLOSED'").fetchone()[0] or 0)
        partial_open = float(c.execute("""SELECT COALESCE(SUM(p.net_pnl),0) FROM paper_partial_exits p
            JOIN paper_live_trades t ON t.id=p.trade_id WHERE t.status='OPEN'""").fetchone()[0] or 0)
        open_count = int(c.execute("SELECT COUNT(*) FROM paper_live_trades WHERE status='OPEN'").fetchone()[0] or 0)
        partial_closed_count = int(c.execute("""SELECT COUNT(*) FROM paper_partial_exits p
            JOIN paper_live_trades t ON t.id=p.trade_id WHERE t.status='CLOSED'""").fetchone()[0] or 0)
    initial = float(meta.get("initial_balance", SETTINGS["initial_balance"]))
    peak = float(meta.get("peak_equity", initial))
    realized = closed + partial_open
    known_equity = initial + realized
    issues = []
    if abs(initial - float(SETTINGS["initial_balance"])) > float(tolerance):
        issues.append({"check": "initial_balance_mismatch", "expected": float(SETTINGS["initial_balance"]), "actual": initial})
    if peak + float(tolerance) < max(initial, known_equity):
        issues.append({"check": "peak_equity_below_known_equity", "expected_at_least": max(initial, known_equity), "actual": peak})
    if partial_closed_count:
        issues.append({"check": "closed_trade_partial_rows_present", "count": partial_closed_count,
                       "severity": "warning", "detail": "بخشی از خروج‌ها در سود نهایی معامله بسته‌شده ادغام شده‌اند و دوباره شمرده نمی‌شوند."})
    return {"valid": not any(x.get("severity") != "warning" for x in issues), "read_only": True,
            "initial_balance": initial, "closed_trade_net_pnl": closed,
            "open_position_partial_realized_pnl": partial_open, "realized_pnl_total": realized,
            "known_realized_equity": known_equity, "open_positions": open_count,
            "equity_complete": open_count == 0,
            "equity": known_equity if open_count == 0 else None,
            "peak_equity": peak, "issues": issues}


def get_equity_history(*, limit: int = 200) -> dict:
    """Return persisted, complete paper-equity snapshots and peak-to-trough drawdown."""
    init_db(backfill_learning=False)
    limit = max(1, min(int(limit), 1000))
    with _connect() as c:
        rows = _rows(c, """SELECT recorded_at,equity,peak_equity,drawdown_pct,realized_pnl,
            unrealized_pnl,open_positions,quote_health,funding_health
            FROM paper_equity_history ORDER BY recorded_at DESC,id DESC LIMIT ?""", (limit,))
    rows.reverse()
    if not rows:
        return {"count": 0, "history": [], "max_drawdown_pct": None,
                "peak_equity": None, "latest_equity": None, "read_only": True}
    max_dd = min(float(row["drawdown_pct"]) for row in rows)
    return {"count": len(rows), "history": rows, "max_drawdown_pct": round(max_dd, 8),
            "peak_equity": max(float(row["peak_equity"]) for row in rows),
            "latest_equity": float(rows[-1]["equity"]), "read_only": True}


@_paper_ledger_writer_guard
def get_state(refresh_quotes: bool = True, sync_funding: bool = False) -> dict:
    init_db()
    funding_sync = sync_open_funding_positions() if sync_funding else {"positions_checked": 0, "positions_failed": 0, "events_inserted": 0}
    # Take a short read snapshot, close the connection, then perform network
    # requests. The position manager must not hold SQLite open across REST I/O.
    with _connect() as c:
        open_snapshot = _rows(c, "SELECT * FROM paper_live_trades WHERE status='OPEN' ORDER BY id DESC")
    open_rows = _refresh_open_positions(open_snapshot) if refresh_quotes else open_snapshot
    if not refresh_quotes:
        with _connect() as c:
            open_rows = [_apply_remaining_position(c, row) for row in open_rows]
            for row in open_rows:
                if row.get("market") == "perp":
                    row["funding_event_count"] = _funding_event_count(c, int(row["id"]))

    with _connect() as c:
        realized, daily = _closed_totals(c)
        open_count = sum(1 for x in open_rows if x.get("status") == "OPEN")
        funding_incomplete_open = sum(1 for x in open_rows if x.get("status") == "OPEN" and x.get("market") == "perp"
                                      and x.get("funding_status") not in ("SYNCED",))
        funding_incomplete_closed_row = c.execute("""SELECT COUNT(*) FROM paper_live_trades
            WHERE status='CLOSED' AND market='perp' AND funding_status!='SYNCED'""").fetchone()
        funding_incomplete_closed = int(funding_incomplete_closed_row[0] or 0)
        funding_incomplete = funding_incomplete_open + funding_incomplete_closed
        realized_complete = funding_incomplete_closed == 0
        disconnected = sum(1 for x in open_rows
                           if x.get("status") == "OPEN" and x.get("quote_status") == "DISCONNECTED")
        unrealized_complete = ((disconnected == 0) if refresh_quotes else (open_count == 0)) and funding_incomplete == 0
        known_upnl = sum(float(x.get("unrealized_net_pnl") or 0) for x in open_rows
                         if x.get("status") == "OPEN" and x.get("quote_status") != "DISCONNECTED")
        upnl = known_upnl if unrealized_complete else None
        equity = SETTINGS["initial_balance"] + realized + known_upnl if unrealized_complete else None
        peak_row = c.execute("SELECT value FROM paper_live_meta WHERE key='peak_equity'").fetchone()
        peak = max(SETTINGS["initial_balance"], float(peak_row[0]) if peak_row else SETTINGS["initial_balance"],
                   equity if equity is not None else SETTINGS["initial_balance"])
        if equity is not None:
            c.execute("UPDATE paper_live_meta SET value=? WHERE key='peak_equity'", (str(peak),))
            now_ts = time.time()
            last_snapshot = c.execute("SELECT recorded_at FROM paper_equity_history ORDER BY recorded_at DESC,id DESC LIMIT 1").fetchone()
            # Persist at most once per minute; the latest row remains restart-safe.
            if last_snapshot is None or now_ts - float(last_snapshot[0]) >= 60:
                c.execute("""INSERT INTO paper_equity_history
                    (recorded_at,equity,peak_equity,drawdown_pct,realized_pnl,unrealized_pnl,
                     open_positions,quote_health,funding_health)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                    (now_ts, float(equity), float(peak), ((float(equity) / float(peak) - 1.0) * 100.0) if peak else 0.0,
                     float(realized), float(known_upnl), int(open_count),
                     "DEGRADED" if disconnected else ("LIVE" if refresh_quotes else "NOT_REFRESHED"),
                     "DEGRADED" if funding_incomplete else "COMPLETE"))
        used = sum(float(x.get("notional") or 0) for x in open_rows if x.get("status") == "OPEN")
        recent = _rows(c, """SELECT t.id,t.opened_at,t.closed_at,t.symbol,t.market,t.timeframe,t.exchange,
            t.requested_exchange,t.side,t.quantity,t.notional,t.reference_entry,t.entry_fill,t.stop_price,
            t.target_price,t.status,t.reference_exit,t.exit_fill,t.net_pnl,t.exit_reason,t.entry_context_json,
            t.funding_total,t.funding_event_count,t.funding_status,t.funding_error,
            (SELECT COUNT(*) FROM paper_partial_exits p WHERE p.trade_id=t.id) AS partial_exit_count,
            (SELECT COALESCE(SUM(quantity),0) FROM paper_partial_exits p WHERE p.trade_id=t.id) AS partial_exited_quantity
            FROM paper_live_trades t ORDER BY t.id DESC LIMIT 40""")
        learning_row = c.execute("SELECT COUNT(*),MAX(closed_at) FROM paper_learning_events").fetchone()
        quote_health = ("NOT_REFRESHED" if not refresh_quotes else ("DEGRADED" if disconnected else "LIVE"))
        funding_health = "DEGRADED" if funding_incomplete else ("LIVE" if any(x.get("market") == "perp" for x in open_rows) else "NOT_APPLICABLE")
        # Do not present a partial mark-to-market as total equity or free cash.
        available = (max(0.0, equity - used) if equity is not None else None)
        risk_snapshot = aggregate_open_risk(
            open_rows,
            fee_bps_per_side=SETTINGS["fee_bps_per_side"],
            slippage_bps_per_side=SETTINGS["slippage_bps_per_side"],
        )
        risk_base = (equity if equity is not None else
                     (SETTINGS["initial_balance"] + realized if realized_complete else SETTINGS["initial_balance"]))
        risk_snapshot.update({
            "equity_basis": round(risk_base, 8),
            "portfolio_cap_pct": SETTINGS["max_portfolio_risk_pct"],
            "portfolio_cap_usdt": round(risk_base * SETTINGS["max_portfolio_risk_pct"] / 100.0, 8),
            "spot_cap_pct": SETTINGS["max_spot_risk_pct"],
            "spot_cap_usdt": round(risk_base * SETTINGS["max_spot_risk_pct"] / 100.0, 8),
            "perp_cap_pct": SETTINGS["max_perp_risk_pct"],
            "perp_cap_usdt": round(risk_base * SETTINGS["max_perp_risk_pct"] / 100.0, 8),
            "directional_cap_pct": SETTINGS["max_directional_risk_pct"],
            "directional_cap_usdt": round(risk_base * SETTINGS["max_directional_risk_pct"] / 100.0, 8),
            "remaining_portfolio_usdt": round(max(0.0, risk_base * SETTINGS["max_portfolio_risk_pct"] / 100.0 - risk_snapshot["total"]), 8),
            "remaining_spot_usdt": round(max(0.0, risk_base * SETTINGS["max_spot_risk_pct"] / 100.0 - risk_snapshot["by_market"].get("spot", 0.0)), 8),
            "remaining_perp_usdt": round(max(0.0, risk_base * SETTINGS["max_perp_risk_pct"] / 100.0 - risk_snapshot["by_market"].get("perp", 0.0)), 8),
            "remaining_long_usdt": round(max(0.0, risk_base * SETTINGS["max_directional_risk_pct"] / 100.0 - risk_snapshot["by_side"].get("LONG", 0.0)), 8),
            "remaining_short_usdt": round(max(0.0, risk_base * SETTINGS["max_directional_risk_pct"] / 100.0 - risk_snapshot["by_side"].get("SHORT", 0.0)), 8),
        })
        return {
            "version": VERSION, "mode": SETTINGS["mode"], "settings": dict(SETTINGS),
            "account": {"initial_balance": SETTINGS["initial_balance"], "realized_pnl": (realized if realized_complete else None),
                        "daily_realized_pnl": (daily if realized_complete else None), "unrealized_pnl": upnl,
                        "equity": equity, "available_balance": available,
                        "known_realized_equity": (SETTINGS["initial_balance"] + realized if realized_complete else None),
                        "realized_pnl_complete": realized_complete,
                        "used_notional": used, "peak_equity": peak,
                        "drawdown_pct": ((equity / peak - 1) * 100) if equity is not None and peak else None,
                        "open_positions": open_count,
                        "quote_health": quote_health, "disconnected_positions": disconnected,
                        "funding_health": funding_health, "funding_incomplete_positions": funding_incomplete,
                        "funding_incomplete_open_positions": funding_incomplete_open,
                        "funding_incomplete_closed_trades": funding_incomplete_closed,
                        "unrealized_pnl_complete": unrealized_complete,
                        "portfolio_risk": risk_snapshot},
            "open_positions": open_rows, "recent_trades": recent,
            "funding_sync": funding_sync,
            "learning_event_count": int(learning_row[0] or 0),
            "learning_last_closed_at": learning_row[1],
            "safety": {"paper_only": True, "real_orders_enabled": False,
                       "private_api_keys_used": False, "public_market_data_only": True},
        }


@_paper_ledger_writer_guard
def update_trailing_state(trade_id: int, observed_price: float, *,
                          trigger_pct: float, distance_pct: float) -> dict:
    """Persist the best observed price and tighten a PAPER stop atomically.

    The stored extreme survives process restarts. This still uses observed
    quote prices (not guaranteed intrabar OHLC), so it is not an exact replay
    substitute for the candle-based backtest.
    """
    from backend.trade_contract import trailing_stop_price
    init_db()
    price = _number(observed_price, "قیمت مشاهده‌شده")
    trigger = float(trigger_pct)
    distance = float(distance_pct)
    if not math.isfinite(trigger) or trigger <= 0 or not math.isfinite(distance) or not 0 < distance < 100:
        raise ValueError("trailing trigger/distance are invalid")
    with _connect() as c:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT side,entry_fill,stop_price,trailing_peak_price,trailing_active "
                        "FROM paper_live_trades WHERE id=? AND status='OPEN'",
                        (int(trade_id),)).fetchone()
        if not row:
            raise ValueError("موقعیت باز پیدا نشد یا قبلاً بسته شده است")
        side = str(row[0]).upper()
        entry = float(row[1])
        old_stop = float(row[2])
        old_peak = row[3]
        if side == "LONG":
            peak = max(price, float(old_peak) if old_peak is not None else price)
            progress = (peak / entry - 1.0) * 100.0
        elif side == "SHORT":
            peak = min(price, float(old_peak) if old_peak is not None else price)
            progress = (entry / peak - 1.0) * 100.0
        else:
            raise ValueError("invalid stored position side")
        active = bool(row[4]) or progress >= trigger
        new_stop = old_stop
        changed = False
        if active:
            candidate = trailing_stop_price(side=side, peak_price=peak, distance_pct=distance)
            tighter = candidate > old_stop if side == "LONG" else candidate < old_stop
            safely_behind_market = candidate < price if side == "LONG" else candidate > price
            if tighter and safely_behind_market:
                new_stop = candidate
                changed = True
        c.execute("UPDATE paper_live_trades SET trailing_peak_price=?,trailing_active=?,stop_price=? "
                  "WHERE id=? AND status='OPEN'",
                  (peak, int(active), new_stop, int(trade_id)))
        return {"id": int(trade_id), "side": side, "peak_price": peak,
                "trailing_active": active, "old_stop": old_stop,
                "new_stop": new_stop, "stop_updated": changed}


@_paper_ledger_writer_guard
def update_stop_price(trade_id: int, new_stop: float) -> dict:
    """Tighten-only protective stop update (used by autopilot trailing).

    A stop can only move in the direction that REDUCES risk: up for LONG,
    down for SHORT. It never loosens a position's protection.
    """
    init_db()
    new_stop = float(new_stop)
    with _connect() as c:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT side,stop_price FROM paper_live_trades WHERE id=? AND status='OPEN'",
                        (int(trade_id),)).fetchone()
        if not row:
            raise ValueError("موقعیت باز پیدا نشد یا قبلاً بسته شده است")
        side, old_stop = row[0], float(row[1])
        if side == "LONG" and new_stop <= old_stop:
            raise ValueError("حدضرر LONG فقط باید به سمت بالا منتقل شود")
        if side == "SHORT" and new_stop >= old_stop:
            raise ValueError("حدضرر SHORT فقط باید به سمت پایین منتقل شود")
        c.execute("UPDATE paper_live_trades SET stop_price=? WHERE id=? AND status='OPEN'",
                  (new_stop, int(trade_id)))
        return {"id": int(trade_id), "side": side, "old_stop": old_stop, "new_stop": new_stop}


def list_trades(status: str | None = None, since: float | None = None,
                until: float | None = None, limit: int | None = 200) -> list[dict]:
    """Filtered trade rows for engines/reports (entry_context_json included)."""
    init_db()
    sql = "SELECT * FROM paper_live_trades"
    conds, args = [], []
    if status in ("OPEN", "CLOSED"):
        conds.append("status=?")
        args.append(status)
    if since is not None:
        conds.append("COALESCE(closed_at,opened_at)>=?")
        args.append(float(since))
    if until is not None:
        conds.append("COALESCE(closed_at,opened_at)<=?")
        args.append(float(until))
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY id DESC"
    if limit:
        sql += f" LIMIT {max(1, int(limit))}"
    with _connect() as c:
        return _rows(c, sql, args)


def get_strategy_rankings(*, period: str = "all", min_trades: int = 5) -> dict:
    """Rank paper-traded strategy scopes with small-sample shrinkage.

    Strategy identity is the observable scope (symbol/market/timeframe/side),
    not an inferred strategy label. Score is risk-aware and read-only.
    """
    periods = {"day": 1, "week": 7, "month": 30, "all": None}
    period = str(period).lower().strip()
    if period not in periods:
        raise ValueError("period باید یکی از day, week, month, all باشد")
    min_trades = int(min_trades)
    if min_trades < 2 or min_trades > 500:
        raise ValueError("min_trades باید بین ۲ تا ۵۰۰ باشد")
    cutoff = time.time() - periods[period] * 86400 if periods[period] else None
    init_db(backfill_learning=False)
    with _connect() as c:
        if cutoff is None:
            rows = _rows(c, "SELECT * FROM paper_learning_events ORDER BY closed_at,trade_id")
        else:
            rows = _rows(c, "SELECT * FROM paper_learning_events WHERE closed_at>=? ORDER BY closed_at,trade_id", (cutoff,))
    pnl_all = [float(r["net_pnl"] or 0.0) for r in rows]
    prior = sum(pnl_all) / len(pnl_all) if pnl_all else 0.0
    grouped = {}
    for row in rows:
        key = (row["symbol"], row["market"], row["timeframe"], row["side"])
        grouped.setdefault(key, []).append(row)
    ranked = []
    for key, items in grouped.items():
        pnls = [float(r["net_pnl"] or 0.0) for r in items]
        wins = [v for v in pnls if v > 0]
        losses = [v for v in pnls if v < 0]
        gross_win, gross_loss = sum(wins), abs(sum(losses))
        equity_curve, peak, max_dd = 0.0, 0.0, 0.0
        for value in pnls:
            equity_curve += value
            peak = max(peak, equity_curve)
            if peak > 0:
                max_dd = max(max_dd, (peak - equity_curve) / peak * 100.0)
        n = len(pnls)
        expectancy = sum(pnls) / n
        reliability = n / (n + 5.0)
        adjusted_expectancy = reliability * expectancy + (1.0 - reliability) * prior
        # Score is deliberately not a probability or a return forecast.
        score = adjusted_expectancy / (1.0 + max_dd / 100.0)
        eligible = n >= min_trades
        ranked.append({"symbol": key[0], "market": key[1], "timeframe": key[2], "side": key[3],
                       "trade_count": n, "wins": len(wins), "losses": len(losses),
                       "win_rate_pct": len(wins) / n * 100.0,
                       "net_pnl_usdt": sum(pnls), "expectancy_usdt": expectancy,
                       "adjusted_expectancy_usdt": adjusted_expectancy,
                       "profit_factor": gross_win / gross_loss if gross_loss else (None if not gross_win else 99.0),
                       "max_closed_trade_drawdown_pct": max_dd,
                       "reliability_pct": reliability * 100.0, "score": score,
                       "eligible": eligible,
                       "status": "قابل رتبه‌بندی" if eligible else "نمونه ناکافی"})
    ranked.sort(key=lambda x: (x["eligible"], x["score"], x["trade_count"]), reverse=True)
    for index, item in enumerate(ranked, 1):
        item["rank"] = index if item["eligible"] else None
    return {"period": period, "min_trades": min_trades, "prior_expectancy_usdt": prior,
            "strategy_count": len(ranked), "eligible_count": sum(1 for x in ranked if x["eligible"]),
            "rankings": ranked,
            "method": "Bayesian-style shrinkage toward period-wide expectancy; drawdown-penalized score",
            "warning": "رتبه‌بندی توصیفی داده‌های گذشته است؛ تضمین‌کننده سود یا پیش‌بینی آینده نیست.",
            "source": "paper_learning_events", "read_only": True, "real_orders_enabled": False}


def get_strategy_entry_adjustments(*, period: str = "all", min_trades: int = 5) -> dict:
    """Return conservative historical multipliers for exact paper-trade scopes.

    This is a ranking aid only: it never converts HOLD to BUY/SELL and never
    blocks a signal. Small samples are strongly shrunk toward neutral.
    """
    report = get_strategy_rankings(period=period, min_trades=min_trades)
    adjustments = {}
    for row in report.get("rankings", []):
        n = int(row.get("trade_count") or 0)
        reliability = max(0.0, min(1.0, float(row.get("reliability_pct") or 0.0) / 100.0))
        adjusted = float(row.get("adjusted_expectancy_usdt") or 0.0)
        prior = float(report.get("prior_expectancy_usdt") or 0.0)
        scale = max(abs(prior), 0.10)
        # Bounded to 0.80..1.20; evidence from few trades has little influence.
        multiplier = 1.0 + 0.20 * reliability * math.tanh(adjusted / scale)
        adjustments[(str(row["symbol"]).upper(), str(row["market"]).lower(),
                     str(row["timeframe"]).lower(), str(row["side"]).upper())] = {
            "multiplier": round(max(0.80, min(1.20, multiplier)), 4),
            "trade_count": n, "eligible": bool(row.get("eligible")),
            "adjusted_expectancy_usdt": round(adjusted, 8),
            "reliability_pct": round(reliability * 100.0, 2),
            "status": "تاریخچه کافی" if row.get("eligible") else "نمونه کم؛ اثر محدود",
        }
    return {"period": report["period"], "min_trades": report["min_trades"],
            "adjustments": adjustments, "source": "paper_learning_events",
            "read_only": True, "real_orders_enabled": False,
            "warning": "ضریب فقط ترتیب فرصت‌های آزمایشی را تعدیل می‌کند؛ سیگنال HOLD را تغییر نمی‌دهد."}



def get_regime_aware_strategy_selection(*, regime: str, period: str = "all", min_trades: int = 5) -> dict:
    """Conservative regime-conditioned historical multipliers for paper candidate ordering."""
    periods = {"day": 1, "week": 7, "month": 30, "all": None}
    period = str(period).lower().strip()
    if period not in periods:
        raise ValueError("period باید یکی از day, week, month, all باشد")
    regime = str(regime).upper().strip()
    allowed = {"UPTREND", "DOWNTREND", "RANGE", "HIGH_VOLATILITY", "TRANSITION"}
    if regime not in allowed:
        raise ValueError("regime نامعتبر است")
    min_trades = int(min_trades)
    if min_trades < 2 or min_trades > 500:
        raise ValueError("min_trades باید بین ۲ تا ۵۰۰ باشد")
    cutoff = time.time() - periods[period] * 86400 if periods[period] else None
    init_db(backfill_learning=False)
    with _connect() as conn:
        if cutoff is None:
            rows = _rows(conn, "SELECT * FROM paper_learning_events ORDER BY closed_at,trade_id")
        else:
            rows = _rows(conn, "SELECT * FROM paper_learning_events WHERE closed_at>=? ORDER BY closed_at,trade_id", (cutoff,))
    tagged = []
    untagged = 0
    for row in rows:
        context = _safe_json_object(row.get("context_json", "{}"))
        decision_context = context.get("decision_context") if isinstance(context.get("decision_context"), dict) else {}
        tag = str(decision_context.get("market_regime") or context.get("market_regime") or "").upper().strip()
        if not tag:
            untagged += 1
            continue
        if tag in allowed:
            tagged.append((row, tag))
    selected = [(row, tag) for row, tag in tagged if tag == regime]
    prior_values = [float(row.get("net_pnl") or 0.0) for row, tag in tagged]
    prior = sum(prior_values) / len(prior_values) if prior_values else 0.0
    grouped = {}
    for row, tag in selected:
        key = (str(row["symbol"]).upper(), str(row["market"]).lower(),
               str(row["timeframe"]).lower(), str(row["side"]).upper())
        grouped.setdefault(key, []).append(float(row.get("net_pnl") or 0.0))
    adjustments = {}
    for key, pnls in grouped.items():
        n = len(pnls)
        expectancy = sum(pnls) / n
        reliability = n / (n + 10.0)
        adjusted = reliability * expectancy + (1.0 - reliability) * prior
        scale = max(abs(prior), 0.10)
        multiplier = 1.0 + 0.10 * reliability * math.tanh(adjusted / scale)
        adjustments[key] = {
            "multiplier": round(max(0.90, min(1.10, multiplier)), 4),
            "trade_count": n, "eligible": n >= min_trades,
            "expectancy_usdt": round(expectancy, 8),
            "adjusted_expectancy_usdt": round(adjusted, 8),
            "reliability_pct": round(reliability * 100.0, 2),
            "status": "سابقه همین رژیم کافی" if n >= min_trades else "نمونه محدود؛ تعدیل بسیار محتاطانه",
        }
    return {"regime": regime, "period": period, "min_trades": min_trades,
            "adjustments": adjustments, "tagged_trade_count": len(tagged),
            "regime_trade_count": len(selected), "untagged_trade_count": untagged,
            "prior_expectancy_usdt": round(prior, 8),
            "source": "paper_learning_events.context_json.market_regime",
            "read_only": True, "real_orders_enabled": False,
            "warning": "فقط ترتیب فرصت‌های آزمایشی را با ضریب محدود تعدیل می‌کند؛ سیگنال یا مجوز ورود ایجاد نمی‌کند."}


def get_performance_analytics(*, period: str = "all") -> dict:
    """Read-only net performance analytics from durable closed-trade learning events."""
    periods = {"day": 1, "week": 7, "month": 30, "all": None}
    period = str(period).lower().strip()
    if period not in periods:
        raise ValueError("period باید یکی از day, week, month, all باشد")
    cutoff = time.time() - periods[period] * 86400 if periods[period] else None
    init_db(backfill_learning=False)
    with _connect() as c:
        if cutoff is None:
            rows = _rows(c, "SELECT * FROM paper_learning_events ORDER BY closed_at,trade_id")
        else:
            rows = _rows(c, "SELECT * FROM paper_learning_events WHERE closed_at>=? ORDER BY closed_at,trade_id", (cutoff,))
    groups = {}
    for row in rows:
        key = (row["symbol"], row["market"], row["timeframe"], row["side"])
        groups.setdefault(key, []).append(row)
    def summarize(items):
        pnls = [float(x["net_pnl"] or 0) for x in items]
        wins = [x for x in pnls if x > 0]
        losses = [x for x in pnls if x < 0]
        gross_win, gross_loss = sum(wins), abs(sum(losses))
        return {"trade_count": len(pnls), "wins": len(wins), "losses": len(losses),
                "breakeven": len(pnls)-len(wins)-len(losses),
                "win_rate_pct": len(wins)/len(pnls)*100 if pnls else 0.0,
                "net_pnl_usdt": sum(pnls), "avg_pnl_usdt": sum(pnls)/len(pnls) if pnls else 0.0,
                "expectancy_usdt": sum(pnls)/len(pnls) if pnls else 0.0,
                "profit_factor": gross_win/gross_loss if gross_loss else (None if not gross_win else 99.0),
                "avg_return_pct": sum(float(x["return_pct"] or 0) for x in items)/len(items) if items else 0.0}
    by_scope = []
    for key, items in groups.items():
        entry = summarize(items)
        entry.update({"symbol":key[0],"market":key[1],"timeframe":key[2],"side":key[3]})
        by_scope.append(entry)
    by_scope.sort(key=lambda x: (x["net_pnl_usdt"], x["trade_count"]), reverse=True)
    overall = summarize(rows)
    return {"period":period,"cutoff":cutoff,"overall":overall,"by_symbol_market_timeframe_side":by_scope,
            "sample_warning": "آمار گذشته تضمین‌کننده عملکرد آینده نیست؛ نمونه کم اعتبار آماری کافی ندارد.",
            "source":"paper_learning_events","read_only":True,"real_orders_enabled":False}


def get_regime_performance(*, period: str = "all") -> dict:
    """Summarize only explicitly recorded market_regime labels in trade context."""
    periods = {"day": 1, "week": 7, "month": 30, "all": None}
    period = str(period).lower().strip()
    if period not in periods:
        raise ValueError("period باید یکی از day, week, month, all باشد")
    cutoff = time.time() - periods[period] * 86400 if periods[period] else None
    init_db(backfill_learning=False)
    with _connect() as c:
        if cutoff is None:
            rows = _rows(c, "SELECT * FROM paper_learning_events ORDER BY closed_at,trade_id")
        else:
            rows = _rows(c, "SELECT * FROM paper_learning_events WHERE closed_at>=? ORDER BY closed_at,trade_id", (cutoff,))
    groups = {}
    untagged = 0
    for row in rows:
        context = _safe_json_object(row.get("context_json", "{}"))
        decision_context = context.get("decision_context") if isinstance(context.get("decision_context"), dict) else {}
        regime = str(decision_context.get("market_regime") or context.get("market_regime") or "").upper().strip()
        if not regime:
            untagged += 1
            continue
        groups.setdefault(regime, []).append(float(row.get("net_pnl") or 0.0))
    results = []
    for regime, pnls in groups.items():
        wins = [x for x in pnls if x > 0]
        losses = [x for x in pnls if x < 0]
        results.append({"regime": regime, "trade_count": len(pnls), "wins": len(wins),
                        "losses": len(losses), "win_rate_pct": round(len(wins)/len(pnls)*100, 2),
                        "net_pnl_usdt": round(sum(pnls), 8),
                        "expectancy_usdt": round(sum(pnls)/len(pnls), 8),
                        "profit_factor": round(sum(wins)/abs(sum(losses)), 6) if losses else (None if not wins else 99.0),
                        "sample_status": "نمونه محدود" if len(pnls) < 5 else "قابل بررسی"})
    results.sort(key=lambda x: (x["trade_count"], x["net_pnl_usdt"]), reverse=True)
    return {"period": period, "regimes": results, "tagged_trade_count": sum(map(len, groups.values())),
            "untagged_trade_count": untagged, "source": "paper_learning_events.context_json.market_regime",
            "read_only": True, "real_orders_enabled": False,
            "warning": "معاملات قدیمی بدون برچسب رژیم قابل انتساب نیستند؛ هیچ رژیمی از روی حدس به گذشته الصاق نمی‌شود."}