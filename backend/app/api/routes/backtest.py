"""
Backtesting: replay the live rules over real gold history.

Runs are kept in memory and executed in the background — a long history takes
a while to page out of the broker.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.backtest import Backtester

logger = logging.getLogger(__name__)
router = APIRouter()

_runs: dict[str, dict[str, Any]] = {}
MAX_RUNS = 20


class BacktestRequest(BaseModel):
    days: int = Field(default=60, ge=5, le=365)
    starting_balance: float = Field(default=10_000.0, gt=0)
    assumed_spread: float = Field(default=0.30, ge=0.0, le=5.0)


async def _execute(run_id: str, request: BacktestRequest) -> None:
    try:
        result = await Backtester().run(
            days=request.days,
            starting_balance=request.starting_balance,
            assumed_spread=request.assumed_spread,
        )
        _runs[run_id].update(
            status="COMPLETE",
            finished_at=dt.datetime.now(dt.timezone.utc).isoformat(),
            result=result.as_dict(),
        )
    except Exception as exc:
        logger.exception("Backtest %s failed", run_id)
        _runs[run_id].update(
            status="FAILED",
            finished_at=dt.datetime.now(dt.timezone.utc).isoformat(),
            error=f"{type(exc).__name__}: {exc}",
        )


@router.post("/run")
async def run_backtest(request: BacktestRequest):
    """Start a backtest. Poll /backtest/runs/{id} for the result."""
    run_id = uuid.uuid4().hex[:12]
    _runs[run_id] = {
        "run_id": run_id,
        "status": "RUNNING",
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "request": request.model_dump(),
    }
    for stale in list(_runs)[:-MAX_RUNS]:
        _runs.pop(stale, None)
    asyncio.create_task(_execute(run_id, request))
    return {"run_id": run_id, "status": "RUNNING"}


@router.get("/runs")
async def list_runs():
    return [
        {k: v for k, v in run.items() if k != "result"}
        | ({"summary": {k: v for k, v in run["result"].items()
                        if k not in ("trades", "equity_curve")}} if run.get("result") else {})
        for run in sorted(_runs.values(), key=lambda r: r["started_at"], reverse=True)
    ]


@router.get("/runs/{run_id}")
async def get_run(run_id: str, include_trades: bool = Query(default=True)):
    run = _runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="No such backtest run")
    if not include_trades and run.get("result"):
        payload = dict(run)
        payload["result"] = {k: v for k, v in run["result"].items() if k != "trades"}
        return payload
    return run
