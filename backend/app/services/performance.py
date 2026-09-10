"""
Performance measurement over recorded trades.

Plain arithmetic on closed trades: what happened, not what might. Every figure
is derived from the trade log, so it says the same thing the broker statement
would.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Any

from app.services.store import store


def _r(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


async def summary(mode: str | None = None, limit: int = 500) -> dict[str, Any]:
    trades = [t for t in await store.trades(limit=limit) if t["status"] == "CLOSED"]
    if mode:
        trades = [t for t in trades if t["mode"] == mode]

    pnls = [t["realized_pl"] or 0.0 for t in trades]
    rs = [t["r_multiple"] or 0.0 for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))

    by_session: dict[str, list[float]] = defaultdict(list)
    by_reason: dict[str, int] = defaultdict(int)
    for trade in trades:
        by_session[trade["session"] or "UNKNOWN"].append(trade["realized_pl"] or 0.0)
        by_reason[trade["exit_reason"] or "UNKNOWN"] += 1

    return {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 2) if trades else 0.0,
        "total_pnl": round(sum(pnls), 2),
        "average_win": round(_r(wins), 2),
        "average_loss": round(_r(losses), 2),
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else 0.0,
        "expectancy_r": round(_r(rs), 3),
        "best_trade": round(max(pnls), 2) if pnls else 0.0,
        "worst_trade": round(min(pnls), 2) if pnls else 0.0,
        "max_consecutive_losses": _longest_losing_streak(pnls),
        "by_session": {
            name: {
                "trades": len(values),
                "pnl": round(sum(values), 2),
                "win_rate": round(
                    len([v for v in values if v > 0]) / len(values) * 100, 2
                ) if values else 0.0,
            }
            for name, values in sorted(by_session.items())
        },
        "by_exit_reason": dict(sorted(by_reason.items())),
        "equity_curve": await equity_curve(mode),
    }


async def equity_curve(mode: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
    """Cumulative realised P&L, oldest first."""
    trades = [t for t in await store.trades(limit=limit) if t["status"] == "CLOSED"]
    if mode:
        trades = [t for t in trades if t["mode"] == mode]
    trades.sort(key=lambda t: t["closed_at"] or "")
    running = 0.0
    curve = []
    for trade in trades:
        running += trade["realized_pl"] or 0.0
        curve.append(
            {
                "time": trade["closed_at"],
                "cumulative_pnl": round(running, 2),
                "pnl": round(trade["realized_pl"] or 0.0, 2),
                "r_multiple": round(trade["r_multiple"] or 0.0, 3),
            }
        )
    return curve


async def today(mode: str | None = None) -> dict[str, Any]:
    midnight = dt.datetime.combine(
        dt.datetime.now(dt.timezone.utc).date(), dt.time.min, tzinfo=dt.timezone.utc
    )
    return {
        "date": midnight.date().isoformat(),
        "realized_pl": round(await store.realized_pl_since(midnight, mode), 2),
        "trades_opened": await store.trades_opened_since(midnight),
    }


def _longest_losing_streak(pnls: list[float]) -> int:
    longest = current = 0
    for pnl in pnls:
        current = current + 1 if pnl < 0 else 0
        longest = max(longest, current)
    return longest
