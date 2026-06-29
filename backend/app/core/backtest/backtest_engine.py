"""
Bar-by-bar backtesting engine.
Walks forward through M15 data, runs SMCStrategy at each step,
manages simulated positions with SL/TP hit detection.

Usage:
    engine = BacktestEngine()
    result = await engine.run("EURUSD", start="2024-01-01", end="2024-12-31")
"""

from __future__ import annotations

import asyncio
import datetime
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.core.data_collection.price_collector import PriceCollector
from app.core.strategy.smc_strategy import SMCStrategy, Signal

SYMBOLS = ["EURUSD", "USDJPY", "GBPUSD", "USDCHF", "AUDUSD", "USDCAD", "XAUUSD", "BTCUSD"]

# Approximate pip values per 1 unit of currency (for $-P&L calc on $50k account)
PIP_VALUE_PER_UNIT: dict[str, float] = {
    "EURUSD": 0.0001, "USDJPY": 0.000091, "GBPUSD": 0.0001,
    "USDCHF": 0.000092, "AUDUSD": 0.0001, "USDCAD": 0.000075,
    "XAUUSD": 0.01, "BTCUSD": 1.0,
}


@dataclass
class BacktestTrade:
    symbol: str
    direction: str
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    result: str            # WIN / LOSS / BE
    r_multiple: float
    pnl_usd: float
    session: str
    reasoning: str
    filters_passed: list[str]
    filters_failed: list[str]
    exit_reason: str       # TP_HIT / SL_HIT


@dataclass
class BacktestResult:
    symbol: str
    start_date: str
    end_date: str
    initial_balance: float
    final_balance: float
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float
    max_drawdown_pct: float
    expectancy_r: float
    total_pnl: float
    trades: list[BacktestTrade] = field(default_factory=list)
    equity_curve: list[dict] = field(default_factory=list)
    per_symbol: dict[str, Any] = field(default_factory=dict)


class BacktestEngine:
    INITIAL_BALANCE = 50_000.0
    RISK_PER_TRADE_PCT = 0.01   # 1% of account per trade
    MIN_BARS_REQUIRED = 50      # minimum bars before strategy can fire

    def __init__(self) -> None:
        self._collector = PriceCollector()
        self._strategy  = SMCStrategy()

    async def run(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        initial_balance: float = INITIAL_BALANCE,
    ) -> BacktestResult:
        """Run a backtest for a single symbol over a date range."""
        start_dt = datetime.datetime.fromisoformat(start_date)
        end_dt   = datetime.datetime.fromisoformat(end_date)

        # Fetch all required timeframe data
        m15_bars, h1_bars, h4_bars, d1_bars = await self._fetch_all_bars(
            symbol, start_dt, end_dt
        )

        if len(m15_bars) < self.MIN_BARS_REQUIRED:
            return self._empty_result(symbol, start_date, end_date, initial_balance, "Insufficient data")

        trades: list[BacktestTrade] = []
        balance = initial_balance
        peak_balance = initial_balance
        max_drawdown = 0.0
        equity_curve: list[dict] = [{"timestamp": m15_bars[0]["timestamp"], "equity": balance}]
        open_trade: dict | None = None

        for i in range(self.MIN_BARS_REQUIRED, len(m15_bars)):
            bar = m15_bars[i]
            bar_dt = self._parse_ts(bar["timestamp"])

            # Skip bars before start or after end
            if bar_dt < start_dt or bar_dt > end_dt:
                continue

            # ── Check SL/TP on open trade ───────────────────────────────────
            if open_trade:
                result = self._check_exit(open_trade, bar)
                if result:
                    trade = self._close_trade(open_trade, bar, result, balance)
                    balance += trade.pnl_usd
                    trades.append(trade)
                    open_trade = None
                    equity_curve.append({"timestamp": bar["timestamp"], "equity": balance})
                    peak_balance = max(peak_balance, balance)
                    dd = (peak_balance - balance) / peak_balance * 100
                    max_drawdown = max(max_drawdown, dd)
                    continue

            # ── Try to generate a new signal (only when no open trade) ───────
            if open_trade:
                continue

            m15_slice = m15_bars[max(0, i - 100):i + 1]
            h1_slice  = self._slice_by_time(h1_bars, bar_dt, 200)
            h4_slice  = self._slice_by_time(h4_bars, bar_dt, 200)
            d1_slice  = self._slice_by_time(d1_bars,  bar_dt, 100)

            if len(h1_slice) < 30 or len(h4_slice) < 20 or len(d1_slice) < 15:
                continue

            try:
                signal: Signal = self._strategy.evaluate(
                    symbol=symbol,
                    h1_bars=h1_slice,
                    h4_bars=h4_slice,
                    d1_bars=d1_slice,
                    m15_bars=m15_slice,
                    news_events=[],  # no live news in backtest
                )
            except Exception:
                continue

            if signal.direction == "NO_TRADE":
                continue

            # Open the trade on the next bar's open (realistic execution)
            if i + 1 >= len(m15_bars):
                break
            next_bar = m15_bars[i + 1]
            entry_price = float(next_bar["open"])
            risk_amount = balance * self.RISK_PER_TRADE_PCT

            # Adjust SL/TP relative to actual entry (signal was based on previous close)
            sl_distance = abs(signal.entry_price - signal.stop_loss)
            tp_distance = abs(signal.take_profit - signal.entry_price)
            if signal.direction == "LONG":
                sl = entry_price - sl_distance
                tp = entry_price + tp_distance
            else:
                sl = entry_price + sl_distance
                tp = entry_price - tp_distance

            if sl_distance <= 0:
                continue

            units = risk_amount / sl_distance

            open_trade = {
                "symbol":        symbol,
                "direction":     signal.direction,
                "entry_time":    next_bar["timestamp"],
                "entry_price":   entry_price,
                "stop_loss":     sl,
                "take_profit":   tp,
                "units":         units,
                "risk_amount":   risk_amount,
                "session":       signal.session,
                "reasoning":     signal.reasoning,
                "filters_passed": signal.filters_passed,
                "filters_failed": signal.filters_failed,
            }

        # Force-close any open trade at last bar
        if open_trade and m15_bars:
            last = m15_bars[-1]
            t = self._close_trade(open_trade, last, "MANUAL", balance)
            balance += t.pnl_usd
            trades.append(t)

        return self._build_result(
            symbol, start_date, end_date, initial_balance, balance,
            trades, equity_curve, max_drawdown
        )

    async def run_all(
        self,
        start_date: str,
        end_date: str,
        initial_balance: float = INITIAL_BALANCE,
    ) -> dict[str, BacktestResult]:
        """Run backtest across all 8 symbols concurrently."""
        tasks = [
            self.run(sym, start_date, end_date, initial_balance)
            for sym in SYMBOLS
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out: dict[str, BacktestResult] = {}
        for sym, res in zip(SYMBOLS, results):
            if isinstance(res, Exception):
                out[sym] = self._empty_result(sym, start_date, end_date, initial_balance, str(res))
            else:
                out[sym] = res
        return out

    # ── private helpers ───────────────────────────────────────────────────────

    async def _fetch_all_bars(
        self,
        symbol: str,
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
    ) -> tuple[list, list, list, list]:
        """Fetch M15, H1, H4, D1 bars. Returns 4 lists."""
        days = (end_dt - start_dt).days
        m15_count = min(days * 96, 5000)  # 96 M15 bars/day
        h1_count  = min(days * 24, 5000)
        h4_count  = min(days * 6,  5000)
        d1_count  = min(days,      5000)

        async def fetch(tf, count):
            try:
                return await self._collector.fetch(symbol, tf, count=count, end=end_dt)
            except Exception:
                return []

        m15, h1, h4, d1 = await asyncio.gather(
            fetch("M15", m15_count),
            fetch("H1",  h1_count),
            fetch("H4",  h4_count),
            fetch("D1",  d1_count),
        )
        # Filter to the requested date range
        return (
            [b for b in m15 if start_dt.isoformat()[:10] <= b["timestamp"][:10] <= end_dt.isoformat()[:10]],
            [b for b in h1  if start_dt.isoformat()[:10] <= b["timestamp"][:10] <= end_dt.isoformat()[:10]],
            [b for b in h4  if start_dt.isoformat()[:10] <= b["timestamp"][:10] <= end_dt.isoformat()[:10]],
            [b for b in d1  if start_dt.isoformat()[:10] <= b["timestamp"][:10] <= end_dt.isoformat()[:10]],
        )

    def _slice_by_time(self, bars: list[dict], before: datetime.datetime, count: int) -> list[dict]:
        """Return up to `count` bars with timestamp < `before`."""
        result = [b for b in bars if self._parse_ts(b["timestamp"]) < before]
        return result[-count:]

    @staticmethod
    def _parse_ts(ts: str) -> datetime.datetime:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                dt = datetime.datetime.strptime(ts[:19], fmt[:len(ts[:19])])
                return dt.replace(tzinfo=None)
            except ValueError:
                continue
        return datetime.datetime.min

    @staticmethod
    def _check_exit(trade: dict, bar: dict) -> str | None:
        """Check if the current bar hits SL or TP. Returns 'SL_HIT', 'TP_HIT', or None."""
        lo = float(bar["low"])
        hi = float(bar["high"])
        sl = trade["stop_loss"]
        tp = trade["take_profit"]
        direction = trade["direction"]

        if direction == "LONG":
            if lo <= sl:
                return "SL_HIT"
            if hi >= tp:
                return "TP_HIT"
        else:
            if hi >= sl:
                return "SL_HIT"
            if lo <= tp:
                return "TP_HIT"
        return None

    @staticmethod
    def _close_trade(trade: dict, bar: dict, exit_reason: str, balance: float) -> BacktestTrade:
        direction = trade["direction"]
        entry     = trade["entry_price"]
        sl        = trade["stop_loss"]
        tp        = trade["take_profit"]
        risk      = trade["risk_amount"]
        units     = trade["units"]

        if exit_reason == "TP_HIT":
            exit_price = tp
            tp_dist = abs(tp - entry)
            sl_dist = abs(entry - sl)
            r_multiple = tp_dist / sl_dist if sl_dist > 0 else 0
            result = "WIN"
        elif exit_reason == "SL_HIT":
            exit_price = sl
            r_multiple = -1.0
            result = "LOSS"
        else:
            exit_price = float(bar["close"])
            sl_dist = abs(entry - sl)
            pnl_dir = (exit_price - entry) if direction == "LONG" else (entry - exit_price)
            r_multiple = pnl_dir / sl_dist if sl_dist > 0 else 0
            result = "WIN" if r_multiple > 0.1 else ("LOSS" if r_multiple < -0.1 else "BE")

        # P&L in USD (approximate: risk × r_multiple)
        pnl_usd = risk * r_multiple

        return BacktestTrade(
            symbol=trade["symbol"],
            direction=direction,
            entry_time=trade["entry_time"],
            exit_time=bar["timestamp"],
            entry_price=entry,
            exit_price=exit_price,
            stop_loss=sl,
            take_profit=tp,
            result=result,
            r_multiple=round(r_multiple, 3),
            pnl_usd=round(pnl_usd, 2),
            session=trade.get("session", ""),
            reasoning=trade.get("reasoning", ""),
            filters_passed=trade.get("filters_passed", []),
            filters_failed=trade.get("filters_failed", []),
            exit_reason=exit_reason,
        )

    def _build_result(
        self, symbol, start_date, end_date, initial_balance, final_balance,
        trades, equity_curve, max_drawdown
    ) -> BacktestResult:
        wins   = [t for t in trades if t.result == "WIN"]
        losses = [t for t in trades if t.result == "LOSS"]
        total  = len(trades)
        win_rate = len(wins) / total * 100 if total else 0

        gross_profit = sum(t.pnl_usd for t in wins)
        gross_loss   = abs(sum(t.pnl_usd for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        avg_win  = np.mean([t.r_multiple for t in wins])  if wins   else 0
        avg_loss = abs(np.mean([t.r_multiple for t in losses])) if losses else 0
        wr_frac  = win_rate / 100
        expectancy = (wr_frac * avg_win) - ((1 - wr_frac) * avg_loss)

        return BacktestResult(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_balance=initial_balance,
            final_balance=round(final_balance, 2),
            total_trades=total,
            wins=len(wins),
            losses=len(losses),
            win_rate=round(win_rate, 2),
            profit_factor=round(profit_factor, 3),
            max_drawdown_pct=round(max_drawdown, 2),
            expectancy_r=round(float(expectancy), 3),
            total_pnl=round(final_balance - initial_balance, 2),
            trades=trades,
            equity_curve=equity_curve,
        )

    def _empty_result(self, symbol, start_date, end_date, initial_balance, reason) -> BacktestResult:
        return BacktestResult(
            symbol=symbol, start_date=start_date, end_date=end_date,
            initial_balance=initial_balance, final_balance=initial_balance,
            total_trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0,
            max_drawdown_pct=0.0, expectancy_r=0.0, total_pnl=0.0,
            trades=[], equity_curve=[], per_symbol={"error": reason},
        )
