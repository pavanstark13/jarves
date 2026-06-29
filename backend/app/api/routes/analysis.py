from fastapi import APIRouter, HTTPException

from app.core.ai.ai_orchestrator import AIOrchestrator
from app.core.strategy.strategy_engine import StrategyEngine
from app.schemas.analysis import AnalysisRequest, AnalysisResult

router = APIRouter()
_strategy = StrategyEngine()


@router.post("/run", response_model=AnalysisResult)
async def run_analysis(request: AnalysisRequest):
    """
    Run all 7 market-understanding engines on the provided OHLCV bars.
    Returns a StrategyEngine result with setup quality 0-100.
    """
    bars = [b.model_dump() for b in request.bars]

    if len(bars) < 20:
        raise HTTPException(
            status_code=422,
            detail="Minimum 20 bars required for analysis",
        )

    economic_events = []

    result = _strategy.run(
        bars=bars,
        symbol=request.symbol,
        timeframe=request.timeframe,
        spread=request.current_spread or 0.0,
        economic_events=economic_events,
    )
    return result


@router.post("/run-with-ai", response_model=AnalysisResult)
async def run_analysis_with_ai(request: AnalysisRequest):
    """
    Same as /run but also generates an AI explanation via Claude.
    Requires ANTHROPIC_API_KEY to be configured.
    """
    bars = [b.model_dump() for b in request.bars]

    if len(bars) < 20:
        raise HTTPException(status_code=422, detail="Minimum 20 bars required")

    result = _strategy.run(
        bars=bars,
        symbol=request.symbol,
        timeframe=request.timeframe,
        spread=request.current_spread or 0.0,
    )

    try:
        ai = AIOrchestrator()
        from app.schemas.risk import RiskCheckResult
        # Provide a minimal stub risk result for the explanation
        stub_risk = RiskCheckResult(
            approved=result.setup_quality >= 70,
            rejection_reason=None if result.setup_quality >= 70 else "Setup quality below threshold",
            checks_passed=[],
            checks_failed=[],
        )
        result.ai_explanation = ai.explain_trade(result, stub_risk)
    except Exception as exc:
        result.ai_explanation = f"[AI explanation unavailable: {exc}]"

    return result
