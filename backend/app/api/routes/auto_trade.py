"""
Auto-Trade / Scanner API routes.
GET  /auto-trade/status      — scanner status + recent signals
POST /auto-trade/toggle      — enable or disable scanner
GET  /auto-trade/positions   — live OANDA open positions
GET  /auto-trade/account     — OANDA account summary
POST /auto-trade/scan        — trigger a manual scan immediately
POST /auto-trade/close/{sym} — close position for a symbol
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.scanner.scanner_engine import scanner
from app.core.execution.oanda_broker import OANDABroker

router = APIRouter()
_broker = OANDABroker()


class ToggleRequest(BaseModel):
    enabled: bool


@router.get("/status")
async def get_status():
    """Current scanner status and recent signal feed."""
    return scanner.get_status()


@router.post("/toggle")
async def toggle_scanner(req: ToggleRequest):
    """Enable or disable the automatic scanner."""
    scanner.enabled = req.enabled
    return {
        "enabled": scanner.enabled,
        "message": "Scanner enabled" if req.enabled else "Scanner disabled",
    }


@router.post("/scan")
async def trigger_scan():
    """Trigger a manual scan immediately (regardless of enabled state)."""
    prev = scanner.enabled
    scanner.enabled = True
    signals = await scanner.run_scan()
    scanner.enabled = prev
    return {
        "signals_fired": len(signals),
        "signals": [
            {
                "symbol": s.symbol,
                "direction": s.direction,
                "placement_status": s.placement_status,
                "reasoning": s.reasoning,
            }
            for s in signals
        ],
    }


@router.get("/positions")
async def get_positions():
    """Live open positions from OANDA practice account."""
    try:
        return await _broker.get_open_positions()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OANDA error: {exc}")


@router.get("/account")
async def get_account():
    """OANDA practice account summary (balance, NAV, unrealized P&L)."""
    try:
        return await _broker.get_account()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OANDA error: {exc}")


@router.post("/close/{symbol}")
async def close_position(symbol: str):
    """Close all open position for a symbol on OANDA."""
    try:
        result = await _broker.close_position(symbol.upper())
        scanner._open_symbols.discard(symbol.upper())
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OANDA error: {exc}")
