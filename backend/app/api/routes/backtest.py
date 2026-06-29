"""
Backtesting API routes.
POST /backtest/run  — start a backtest (runs as background task)
GET  /backtest/runs — list completed runs (in-memory for now)
GET  /backtest/runs/{run_id} — get full result with equity curve
"""

from __future__ import annotations

import asyncio
import datetime
import uuid
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from app.core.backtest.backtest_engine import BacktestEngine, BacktestResult, SYMBOLS

router = APIRouter()

# In-memory store (replace with DB in production)
_runs: dict[str, dict[str, Any]] = {}


class BacktestRequest(BaseModel):
    symbol: str = "ALL"                  # specific symbol or "ALL"
    start_date: str = "2024-01-01"
    end_date: str = "2024-12-31"
    initial_balance: float = 50000.0


async def _run_backtest_task(run_id: str, req: BacktestRequest) -> None:
    engine = BacktestEngine()
    _runs[run_id]["status"] = "RUNNING"
    try:
        if req.symbol.upper() == "ALL":
            symbol_results = await engine.run_all(
                req.start_date, req.end_date, req.initial_balance
            )
            # Aggregate
            all_trades = []
            total_pnl  = 0.0
            wins = losses = 0
            equity = req.initial_balance
            for sym, res in symbol_results.items():
                all_trades.extend([asdict(t) for t in res.trades])
                total_pnl  += res.total_pnl
                wins       += res.wins
                losses     += res.losses
                equity     += res.total_pnl
            total = wins + losses
            wr = wins / total * 100 if total else 0
            _runs[run_id].update({
                "status":          "COMPLETED",
                "symbol":          "ALL",
                "total_trades":    total,
                "wins":            wins,
                "losses":          losses,
                "win_rate":        round(wr, 2),
                "total_pnl":       round(total_pnl, 2),
                "final_balance":   round(req.initial_balance + total_pnl, 2),
                "per_symbol":      {sym: asdict(res) for sym, res in symbol_results.items()},
                "trades":          all_trades[-200:],  # cap at 200 for response size
                "completed_at":    datetime.datetime.utcnow().isoformat(),
            })
        else:
            if req.symbol.upper() not in SYMBOLS:
                _runs[run_id]["status"] = "FAILED"
                _runs[run_id]["error"]  = f"Unknown symbol: {req.symbol}. Use one of {SYMBOLS}"
                return
            res: BacktestResult = await engine.run(
                req.symbol.upper(), req.start_date, req.end_date, req.initial_balance
            )
            _runs[run_id].update({
                "status":          "COMPLETED",
                **{k: v for k, v in asdict(res).items() if k != "trades"},
                "trades":          [asdict(t) for t in res.trades[-200:]],
                "completed_at":    datetime.datetime.utcnow().isoformat(),
            })
    except Exception as exc:
        _runs[run_id]["status"] = "FAILED"
        _runs[run_id]["error"]  = str(exc)


@router.post("/run")
async def run_backtest(req: BacktestRequest, background_tasks: BackgroundTasks):
    """Start a backtest run asynchronously. Poll GET /runs/{run_id} for status."""
    run_id = str(uuid.uuid4())[:8]
    _runs[run_id] = {
        "run_id":          run_id,
        "symbol":          req.symbol,
        "start_date":      req.start_date,
        "end_date":        req.end_date,
        "initial_balance": req.initial_balance,
        "status":          "QUEUED",
        "started_at":      datetime.datetime.utcnow().isoformat(),
    }
    background_tasks.add_task(_run_backtest_task, run_id, req)
    return {"run_id": run_id, "status": "QUEUED"}


@router.get("/runs")
async def list_runs():
    """List all backtest runs (most recent first)."""
    runs = sorted(_runs.values(), key=lambda r: r.get("started_at", ""), reverse=True)
    # Return summary without the large trades list
    return [
        {k: v for k, v in r.items() if k not in ("trades", "per_symbol", "equity_curve")}
        for r in runs
    ]


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get full backtest result including equity curve and trades."""
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail="Run not found")
    return _runs[run_id]


@router.get("/runs/{run_id}/trades")
async def get_run_trades(
    run_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    result: str | None = Query(default=None, description="Filter: WIN, LOSS, BE"),
):
    """Paginated list of individual trades from a backtest run."""
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail="Run not found")
    trades = _runs[run_id].get("trades", [])
    if result:
        trades = [t for t in trades if t.get("result") == result.upper()]
    start = (page - 1) * page_size
    return {
        "total": len(trades),
        "page":  page,
        "trades": trades[start:start + page_size],
    }
