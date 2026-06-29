"""
AnalyticsService — Computes performance metrics from trade history.

Metrics:
  - Win rate
  - Profit factor (gross profit / gross loss)
  - Expectancy in R
  - Max drawdown
  - R multiples distribution
  - Session breakdown
"""

import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import PerformanceSnapshot
from app.models.trade import TradeJournal


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def compute_performance(
        self,
        symbol: str | None = None,
        since: datetime.datetime | None = None,
    ) -> dict[str, Any]:
        """Compute full performance metrics from journal entries."""
        stmt = select(TradeJournal).where(TradeJournal.result.isnot(None))
        if symbol:
            stmt = stmt.where(TradeJournal.symbol == symbol)
        if since:
            stmt = stmt.where(TradeJournal.created_at >= since)
        result = await self._db.execute(stmt)
        entries = list(result.scalars().all())

        if not entries:
            return {"message": "No closed trades found", "total_trades": 0}

        wins = [e for e in entries if e.result == "WIN"]
        losses = [e for e in entries if e.result == "LOSS"]
        breakevens = [e for e in entries if e.result == "BE"]

        total = len(entries)
        win_rate = len(wins) / total if total else 0.0

        gross_profit = sum(e.pnl for e in wins if e.pnl is not None)
        gross_loss = abs(sum(e.pnl for e in losses if e.pnl is not None))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        r_multiples = [e.r_multiple for e in entries if e.r_multiple is not None]
        expectancy = sum(r_multiples) / len(r_multiples) if r_multiples else 0.0

        # Max drawdown (sequential equity curve)
        pnl_series = [e.pnl for e in sorted(entries, key=lambda x: x.created_at) if e.pnl is not None]
        max_drawdown, max_drawdown_pct = self._compute_max_drawdown(pnl_series)

        # Session breakdown
        sessions = ["LONDON", "NEW_YORK", "OVERLAP", "ASIA", "KILL_ZONE"]
        session_stats: dict[str, Any] = {}
        for sess in sessions:
            sess_entries = [e for e in entries if e.session == sess]
            if sess_entries:
                sess_wins = sum(1 for e in sess_entries if e.result == "WIN")
                session_stats[sess] = {
                    "total": len(sess_entries),
                    "win_rate": round(sess_wins / len(sess_entries), 4),
                }

        # Direction breakdown
        long_entries  = [e for e in entries if e.direction == "LONG"]
        short_entries = [e for e in entries if e.direction == "SHORT"]
        long_pnl  = sum(e.pnl for e in long_entries  if e.pnl is not None)
        short_pnl = sum(e.pnl for e in short_entries if e.pnl is not None)

        return {
            "total_trades": total,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "breakeven_trades": len(breakevens),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else None,
            "expectancy_r": round(expectancy, 4),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "net_pnl": round(gross_profit - gross_loss, 2),
            "total_pnl": round(gross_profit - gross_loss, 2),
            "max_drawdown": round(max_drawdown, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 4),
            "r_multiples": [round(r, 3) for r in r_multiples],
            "session_stats": session_stats,
            "session_performance": session_stats,
            "long_trades": len(long_entries),
            "short_trades": len(short_entries),
            "long_pnl": round(long_pnl, 2),
            "short_pnl": round(short_pnl, 2),
        }

    def _compute_max_drawdown(self, pnl_series: list[float]) -> tuple[float, float]:
        if not pnl_series:
            return 0.0, 0.0
        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        max_dd_pct = 0.0
        for pnl in pnl_series:
            equity += pnl
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd / peak if peak > 0 else 0.0
        return max_dd, max_dd_pct

    async def save_snapshot(self, metrics: dict[str, Any], symbol: str | None = None) -> PerformanceSnapshot:
        """Persist a performance snapshot."""
        session_perf = metrics.get("session_performance", {})
        snapshot = PerformanceSnapshot(
            snapshot_date=datetime.datetime.utcnow(),
            symbol=symbol,
            total_trades=metrics.get("total_trades", 0),
            winning_trades=metrics.get("winning_trades", 0),
            losing_trades=metrics.get("losing_trades", 0),
            breakeven_trades=metrics.get("breakeven_trades", 0),
            win_rate=metrics.get("win_rate"),
            profit_factor=metrics.get("profit_factor"),
            expectancy=metrics.get("expectancy_r"),
            total_pnl=metrics.get("net_pnl"),
            max_drawdown=metrics.get("max_drawdown"),
            max_drawdown_pct=metrics.get("max_drawdown_pct"),
            london_win_rate=session_perf.get("LONDON", {}).get("win_rate"),
            ny_win_rate=session_perf.get("NEW_YORK", {}).get("win_rate"),
            overlap_win_rate=session_perf.get("OVERLAP", {}).get("win_rate"),
            asia_win_rate=session_perf.get("ASIA", {}).get("win_rate"),
        )
        self._db.add(snapshot)
        await self._db.flush()
        await self._db.refresh(snapshot)
        return snapshot
