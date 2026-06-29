"""
AI Insights API — deep trade intelligence powered by Google Gemini.

POST /ai-insights/analyze        — full analysis from trade journal data
POST /ai-insights/strategy       — generate personalized strategy
POST /ai-insights/pair/{symbol}  — deep per-pair analysis
POST /ai-insights/silent-periods — identify when NOT to trade
"""

from __future__ import annotations

import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.ai.trade_analyst import TradeAnalyst

router = APIRouter()
_analyst = TradeAnalyst()


class TradeRecord(BaseModel):
    symbol: str
    direction: str
    session: str = ""
    entry_price: float = 0
    exit_price: float = 0
    stop_loss: float = 0
    take_profit: float = 0
    result: str = ""          # WIN / LOSS / BE
    r_multiple: float = 0
    pnl: float = 0
    setup_quality: float = 0
    entry_time: str = ""
    exit_time: str = ""
    exit_reason: str = ""     # TP_HIT / SL_HIT / MANUAL
    strategy_tag: str = ""    # SMC_OB / SMC_FVG / BREAKOUT / etc.
    notes: str = ""


class AnalyzeRequest(BaseModel):
    trades: list[TradeRecord]
    account_balance: float = 50000.0


class PairRequest(BaseModel):
    trades: list[TradeRecord]
    symbol: str


@router.post("/analyze")
async def analyze_trades(req: AnalyzeRequest):
    """Full AI analysis of trade journal — patterns, pairs, sessions, strategy."""
    if len(req.trades) < 3:
        raise HTTPException(status_code=422, detail="Need at least 3 trades for meaningful analysis.")
    try:
        result = _analyst.full_analysis(req.trades, req.account_balance)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI analysis failed: {e}")


@router.post("/strategy")
async def generate_strategy(req: AnalyzeRequest):
    """Generate a personalized trading strategy based on what's working."""
    if len(req.trades) < 5:
        raise HTTPException(status_code=422, detail="Need at least 5 trades to generate a strategy.")
    try:
        result = _analyst.generate_strategy(req.trades, req.account_balance)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Strategy generation failed: {e}")


@router.post("/pair/{symbol}")
async def analyze_pair(symbol: str, req: AnalyzeRequest):
    """Deep analysis for a specific symbol."""
    pair_trades = [t for t in req.trades if t.symbol.upper() == symbol.upper()]
    if len(pair_trades) < 2:
        raise HTTPException(status_code=422, detail=f"Need at least 2 trades for {symbol}.")
    try:
        result = _analyst.pair_deep_dive(symbol, pair_trades, req.account_balance)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Pair analysis failed: {e}")


@router.post("/silent-periods")
async def silent_periods(req: AnalyzeRequest):
    """Identify when NOT to trade — losing sessions, conditions, setups to avoid."""
    if len(req.trades) < 5:
        raise HTTPException(status_code=422, detail="Need at least 5 trades.")
    try:
        result = _analyst.identify_silent_periods(req.trades)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Analysis failed: {e}")
