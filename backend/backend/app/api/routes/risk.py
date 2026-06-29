from fastapi import APIRouter

from app.core.ai.ai_orchestrator import AIOrchestrator
from app.core.risk.risk_engine import RiskEngine
from app.schemas.risk import RiskCheckRequest, RiskCheckResult

router = APIRouter()
_risk_engine = RiskEngine()


@router.post("/check", response_model=RiskCheckResult)
async def check_risk(request: RiskCheckRequest):
    """
    Run all 7 risk checks against the provided trade parameters and account state.
    Returns approved=True with position size if all checks pass, or
    approved=False with the first failing check's reason.
    """
    return _risk_engine.check(request)


@router.post("/check-with-ai", response_model=RiskCheckResult)
async def check_risk_with_ai(request: RiskCheckRequest):
    """
    Same as /check but appends an AI explanation from Claude.
    """
    result = _risk_engine.check(request)

    try:
        ai = AIOrchestrator()
        result.ai_explanation = ai.explain_trade(request.analysis_result, result)
    except Exception as exc:
        result.ai_explanation = f"[AI explanation unavailable: {exc}]"

    return result
