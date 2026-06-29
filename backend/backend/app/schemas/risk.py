from typing import Optional

from pydantic import BaseModel

from app.schemas.analysis import AnalysisResult


class AccountState(BaseModel):
    account_balance: float
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    peak_balance: float  # for drawdown calc
    open_positions: int = 0
    margin_used: float = 0.0


class RiskCheckRequest(BaseModel):
    analysis_result: AnalysisResult
    account_state: AccountState
    symbol: str
    direction: str  # BUY / SELL
    entry_price: float
    stop_loss: float
    take_profit: float
    current_spread: Optional[float] = None
    atr: Optional[float] = None
    risk_pct: Optional[float] = None  # defaults to settings value
    pip_value: Optional[float] = 10.0  # USD per pip per lot (standard lot)
    stop_loss_pips: Optional[float] = None  # override for pip calc


class RiskCheckResult(BaseModel):
    approved: bool
    rejection_reason: Optional[str] = None
    position_size: Optional[float] = None  # in lots
    risk_amount: Optional[float] = None    # USD at risk
    risk_pct_used: Optional[float] = None
    risk_reward: Optional[float] = None
    checks_passed: list[str] = []
    checks_failed: list[str] = []
    ai_explanation: Optional[str] = None
