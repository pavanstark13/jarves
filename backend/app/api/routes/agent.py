"""Agent control and observation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import settings
from app.core.agent import get_agent
from app.core.broker.base import BrokerError
from app.services.store import store

router = APIRouter()


class FlattenRequest(BaseModel):
    reason: str = Field(default="closed by operator", max_length=120)


@router.get("/status")
async def status():
    """Everything about what the agent is doing and why."""
    return await get_agent().status()


@router.post("/start")
async def start():
    """Begin trading. Refused while a risk halt is in force."""
    result = await get_agent().start()
    if not result["enabled"]:
        raise HTTPException(status_code=409, detail=result["message"])
    return result


@router.post("/stop")
async def stop(reason: str = Query(default="stopped by operator")):
    """Stop opening trades. Open positions keep their broker-side stop and target."""
    return await get_agent().stop(reason)


@router.post("/cycle")
async def run_cycle(force: bool = Query(default=True)):
    """
    Run one cycle now. With force=true (the default) it evaluates and reports
    without opening anything while the agent is stopped.
    """
    report = await get_agent().cycle(force=force)
    return report.as_dict()


@router.get("/evaluate")
async def evaluate():
    """What the strategy makes of the market right now, gate by gate."""
    report = await get_agent().cycle(force=True)
    if report.error:
        raise HTTPException(status_code=502, detail=report.error)
    return {
        "decision": report.decision.as_dict() if report.decision else None,
        "risk": report.verdict.as_dict() if report.verdict else None,
        "actions": report.actions,
    }


@router.post("/flatten")
async def flatten(request: FlattenRequest):
    """Close every open gold position immediately."""
    try:
        return await get_agent().flatten(request.reason)
    except BrokerError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/reset-halt")
async def reset_halt():
    """Clear a drawdown halt. Deliberately manual — a halt means something broke."""
    return await get_agent().clear_halt()


@router.get("/decisions")
async def decisions(limit: int = Query(default=50, ge=1, le=500)):
    """The audit trail: every evaluation, taken or not."""
    return await store.recent_decisions(limit)


@router.get("/events")
async def events(limit: int = Query(default=50, ge=1, le=500)):
    """Lifecycle log — starts, stops, halts, entries, exits, errors."""
    return await store.events(limit)


@router.get("/config")
async def config():
    """The operating limits currently in force."""
    return {
        "mode": "live" if settings.is_live else "paper",
        "broker_environment": settings.OANDA_ENVIRONMENT,
        "scan_interval_seconds": settings.SCAN_INTERVAL_SECONDS,
        "risk": {
            "risk_per_trade_pct": settings.RISK_PER_TRADE_PCT,
            "max_daily_loss_pct": settings.MAX_DAILY_LOSS_PCT,
            "max_drawdown_pct": settings.MAX_DRAWDOWN_PCT,
            "max_trades_per_day": settings.MAX_TRADES_PER_DAY,
            "max_open_positions": settings.MAX_OPEN_POSITIONS,
            "max_consecutive_losses": settings.MAX_CONSECUTIVE_LOSSES,
            "cooldown_minutes": settings.COOLDOWN_MINUTES,
            "max_leverage": settings.MAX_LEVERAGE,
        },
        "trade": {
            "min_risk_reward": settings.MIN_RISK_REWARD,
            "stop_atr_multiple": settings.STOP_ATR_MULTIPLE,
            "min_stop_usd": settings.MIN_STOP_USD,
            "max_stop_usd": settings.MAX_STOP_USD,
            "breakeven_at_r": settings.BREAKEVEN_AT_R,
            "trail_start_r": settings.TRAIL_START_R,
            "trail_atr_multiple": settings.TRAIL_ATR_MULTIPLE,
            "max_trade_hours": settings.MAX_TRADE_HOURS,
        },
        "market": {
            "session_windows_utc": settings.SESSION_WINDOWS,
            "rollover_window_utc": settings.ROLLOVER_WINDOW,
            "max_spread_usd": settings.MAX_SPREAD_USD,
            "max_spread_atr_ratio": settings.MAX_SPREAD_ATR_RATIO,
            "min_atr_usd": settings.MIN_ATR_USD,
            "max_atr_usd": settings.MAX_ATR_USD,
            "max_extension_atr": settings.MAX_EXTENSION_ATR,
            "news_blackout_before_min": settings.NEWS_BLACKOUT_BEFORE_MIN,
            "news_blackout_after_min": settings.NEWS_BLACKOUT_AFTER_MIN,
        },
    }
