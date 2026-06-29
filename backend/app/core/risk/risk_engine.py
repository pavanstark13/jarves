"""
RiskEngine — The most critical layer.

Runs 8 checks in sequence.  Any failure immediately returns approved=False.
If all pass, calculates position size using the fractional Kelly / fixed-risk
formula:
  position_size = (account_balance * risk_pct) / (stop_loss_pips * pip_value)
"""

from app.config import settings
from app.schemas.risk import AccountState, RiskCheckRequest, RiskCheckResult


class RiskEngine:
    def check(self, request: RiskCheckRequest) -> RiskCheckResult:
        checks_passed: list[str] = []
        checks_failed: list[str] = []

        acct = request.account_state
        analysis = request.analysis_result

        # --- Guard against zero account balance ---
        if acct.account_balance <= 0:
            return RiskCheckResult(
                approved=False,
                rejection_reason="Account balance is zero or negative",
                checks_passed=checks_passed,
                checks_failed=["account_balance"],
            )

        # 1. Daily loss check
        daily_loss_pct = (abs(acct.daily_pnl) / acct.account_balance) * 100 if acct.daily_pnl < 0 else 0
        max_daily = settings.RISK_MAX_DAILY_LOSS_PCT
        if daily_loss_pct >= max_daily:
            checks_failed.append(f"daily_loss ({daily_loss_pct:.2f}% >= {max_daily}%)")
            return RiskCheckResult(
                approved=False,
                rejection_reason=f"Daily loss limit hit: {daily_loss_pct:.2f}% (max {max_daily}%)",
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        checks_passed.append(f"daily_loss ({daily_loss_pct:.2f}% < {max_daily}%)")

        # 2. Weekly loss check
        weekly_loss_pct = (abs(acct.weekly_pnl) / acct.account_balance) * 100 if acct.weekly_pnl < 0 else 0
        max_weekly = settings.RISK_MAX_WEEKLY_LOSS_PCT
        if weekly_loss_pct >= max_weekly:
            checks_failed.append(f"weekly_loss ({weekly_loss_pct:.2f}% >= {max_weekly}%)")
            return RiskCheckResult(
                approved=False,
                rejection_reason=f"Weekly loss limit hit: {weekly_loss_pct:.2f}% (max {max_weekly}%)",
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        checks_passed.append(f"weekly_loss ({weekly_loss_pct:.2f}% < {max_weekly}%)")

        # 3. Total drawdown check
        if acct.peak_balance > 0:
            drawdown_pct = ((acct.peak_balance - acct.account_balance) / acct.peak_balance) * 100
        else:
            drawdown_pct = 0.0
        max_dd = settings.RISK_MAX_DRAWDOWN_PCT
        if drawdown_pct >= max_dd:
            checks_failed.append(f"drawdown ({drawdown_pct:.2f}% >= {max_dd}%)")
            return RiskCheckResult(
                approved=False,
                rejection_reason=f"Max drawdown hit: {drawdown_pct:.2f}% (max {max_dd}%)",
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        checks_passed.append(f"drawdown ({drawdown_pct:.2f}% < {max_dd}%)")

        # 4. Setup quality check
        min_quality = settings.MIN_SETUP_QUALITY
        if analysis.setup_quality < min_quality:
            checks_failed.append(f"setup_quality ({analysis.setup_quality} < {min_quality})")
            return RiskCheckResult(
                approved=False,
                rejection_reason=f"Setup quality too low: {analysis.setup_quality:.1f} (min {min_quality})",
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        checks_passed.append(f"setup_quality ({analysis.setup_quality:.1f} >= {min_quality})")

        # 5. Risk/reward check
        entry = request.entry_price
        sl = request.stop_loss
        tp = request.take_profit
        risk_pips = abs(entry - sl)
        reward_pips = abs(tp - entry)
        rr = reward_pips / risk_pips if risk_pips > 0 else 0.0
        min_rr = settings.MIN_RISK_REWARD
        if rr < min_rr:
            checks_failed.append(f"risk_reward ({rr:.2f} < {min_rr})")
            return RiskCheckResult(
                approved=False,
                rejection_reason=f"Risk/reward too low: {rr:.2f}R (min {min_rr}R)",
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        checks_passed.append(f"risk_reward ({rr:.2f}R >= {min_rr}R)")

        # 6. Spread vs ATR check
        atr = request.atr
        spread = request.current_spread
        if atr and spread and atr > 0:
            spread_atr_ratio = spread / atr
            if spread_atr_ratio > 2.0:
                checks_failed.append(f"spread_atr_ratio ({spread_atr_ratio:.2f} > 2.0)")
                return RiskCheckResult(
                    approved=False,
                    rejection_reason=f"Spread too wide: {spread_atr_ratio:.2f}x ATR (max 2.0x)",
                    checks_passed=checks_passed,
                    checks_failed=checks_failed,
                )
            checks_passed.append(f"spread_atr ({spread_atr_ratio:.2f}x ATR < 2.0x)")
        else:
            checks_passed.append("spread_atr (skipped — no spread/ATR provided)")

        # 7. News engine score check
        news_engine_output = next(
            (e for e in analysis.engines if e.engine_name == "NewsEngine"), None
        )
        if news_engine_output and news_engine_output.confidence == 0.0:
            checks_failed.append("news_engine_score (0.0 — high impact news)")
            return RiskCheckResult(
                approved=False,
                rejection_reason=f"High-impact news nearby: {news_engine_output.signal}",
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        checks_passed.append("news_engine_score (clear)")

        # --- All checks passed — compute position size ---
        risk_pct = request.risk_pct or settings.RISK_DEFAULT_RISK_PCT
        risk_amount = acct.account_balance * (risk_pct / 100.0)

        # Position size in lots
        if request.stop_loss_pips and request.pip_value:
            position_size = risk_amount / (request.stop_loss_pips * request.pip_value)
        else:
            # Fallback: use price difference as approximate pips (× 10000 for FX)
            price_sl_diff = abs(entry - sl)
            pip_value = request.pip_value or 10.0
            pips = price_sl_diff * 10000  # approximate for 4-decimal FX
            position_size = risk_amount / (pips * pip_value) if pips > 0 else 0.0

        position_size = round(max(position_size, 0.01), 2)

        return RiskCheckResult(
            approved=True,
            position_size=position_size,
            risk_amount=round(risk_amount, 2),
            risk_pct_used=risk_pct,
            risk_reward=round(rr, 3),
            checks_passed=checks_passed,
            checks_failed=[],
        )
