"""
Risk control — the layer that can only ever say no.

The strategy decides whether a setup exists. This decides whether the account
can afford to take it, and how large it may be. Position size is arithmetic,
not judgement: risk a fixed fraction of net asset value between entry and the
stop, and let the stop distance determine the number of ounces.

    units = (NAV x risk%) / (entry - stop)

Every limit here is an account-level fact — realised losses today, drawdown
from the peak, positions already open — measured before each order.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

from app.config import settings
from app.core.broker.base import Account, Position
from app.core.strategy import Decision
from app.instrument import GOLD, InstrumentSpec


@dataclass
class Check:
    name: str
    passed: bool
    detail: str

    def __post_init__(self) -> None:
        self.passed = bool(self.passed)

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass
class RiskVerdict:
    approved: bool
    units: float = 0.0
    risk_amount: float = 0.0
    risk_pct: float = 0.0
    notional: float = 0.0
    checks: list[Check] = field(default_factory=list)
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "units": self.units,
            "risk_amount": round(self.risk_amount, 2),
            "risk_pct": round(self.risk_pct, 3),
            "notional": round(self.notional, 2),
            "reason": self.reason,
            "checks": [c.as_dict() for c in self.checks],
        }


@dataclass
class DayBook:
    """The trading day's running totals, kept by the agent and read here."""

    date: dt.date
    start_nav: float
    peak_nav: float
    realized_pl: float = 0.0
    trades_opened: int = 0
    consecutive_losses: int = 0
    cooldown_until: dt.datetime | None = None
    halted: bool = False
    halt_reason: str = ""

    def daily_loss_pct(self, nav: float) -> float:
        """Loss so far today as a positive percentage of the day's opening NAV."""
        if self.start_nav <= 0:
            return 0.0
        change = (nav - self.start_nav) / self.start_nav * 100.0
        return -change if change < 0 else 0.0

    def drawdown_pct(self, nav: float) -> float:
        if self.peak_nav <= 0:
            return 0.0
        return max(0.0, (self.peak_nav - nav) / self.peak_nav * 100.0)

    def as_dict(self, nav: float | None = None) -> dict[str, Any]:
        payload = {
            "date": self.date.isoformat(),
            "start_nav": round(self.start_nav, 2),
            "peak_nav": round(self.peak_nav, 2),
            "realized_pl": round(self.realized_pl, 2),
            "trades_opened": self.trades_opened,
            "consecutive_losses": self.consecutive_losses,
            "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None,
            "halted": self.halted,
            "halt_reason": self.halt_reason,
        }
        if nav is not None:
            payload["daily_loss_pct"] = round(self.daily_loss_pct(nav), 3)
            payload["drawdown_pct"] = round(self.drawdown_pct(nav), 3)
        return payload


class RiskManager:
    def __init__(self, spec: InstrumentSpec | None = None) -> None:
        self.spec = spec or GOLD

    def evaluate(
        self,
        decision: Decision,
        account: Account,
        open_positions: list[Position],
        book: DayBook,
        now: dt.datetime | None = None,
    ) -> RiskVerdict:
        now = now or dt.datetime.now(dt.timezone.utc)
        checks: list[Check] = []

        def deny(reason: str) -> RiskVerdict:
            return RiskVerdict(approved=False, checks=checks, reason=reason)

        # ── The agent must not already be halted ──────────────────────────────
        if book.halted:
            checks.append(Check("halt", False, book.halt_reason))
            return deny(book.halt_reason)
        checks.append(Check("halt", True, "Agent is not halted"))

        # ── Account has to be worth trading ───────────────────────────────────
        if account.nav < settings.MIN_ACCOUNT_BALANCE:
            detail = f"NAV ${account.nav:,.2f} is below the ${settings.MIN_ACCOUNT_BALANCE:,.2f} floor"
            checks.append(Check("account", False, detail))
            return deny(detail)
        checks.append(Check("account", True, f"NAV ${account.nav:,.2f}"))

        # ── Drawdown from the equity peak ─────────────────────────────────────
        drawdown = book.drawdown_pct(account.nav)
        if drawdown >= settings.MAX_DRAWDOWN_PCT:
            detail = (
                f"Drawdown {drawdown:.2f}% has reached the {settings.MAX_DRAWDOWN_PCT:.2f}% "
                f"limit — trading halted until manually reset"
            )
            checks.append(Check("drawdown", False, detail))
            return deny(detail)
        checks.append(
            Check("drawdown", True, f"Drawdown {drawdown:.2f}% of {settings.MAX_DRAWDOWN_PCT:.2f}%")
        )

        # ── Today's losses ────────────────────────────────────────────────────
        daily_loss = book.daily_loss_pct(account.nav)
        if daily_loss >= settings.MAX_DAILY_LOSS_PCT:
            detail = (
                f"Down {daily_loss:.2f}% today, at the {settings.MAX_DAILY_LOSS_PCT:.2f}% "
                f"daily limit — no more trades today"
            )
            checks.append(Check("daily_loss", False, detail))
            return deny(detail)
        checks.append(
            Check("daily_loss", True, f"Down {daily_loss:.2f}% of {settings.MAX_DAILY_LOSS_PCT:.2f}% today")
        )

        # ── Cool-down after consecutive losses ────────────────────────────────
        if book.cooldown_until and now < book.cooldown_until:
            minutes = (book.cooldown_until - now).total_seconds() / 60
            detail = (
                f"Cooling off after {book.consecutive_losses} losses in a row — "
                f"{minutes:.0f} min remaining"
            )
            checks.append(Check("cooldown", False, detail))
            return deny(detail)
        checks.append(Check("cooldown", True, "Not in a cool-down period"))

        # ── Concurrency and frequency ─────────────────────────────────────────
        if len(open_positions) >= settings.MAX_OPEN_POSITIONS:
            detail = f"Already holding {len(open_positions)} of {settings.MAX_OPEN_POSITIONS} allowed positions"
            checks.append(Check("open_positions", False, detail))
            return deny(detail)
        checks.append(
            Check("open_positions", True, f"{len(open_positions)}/{settings.MAX_OPEN_POSITIONS} open")
        )

        if book.trades_opened >= settings.MAX_TRADES_PER_DAY:
            detail = f"Daily cap reached: {book.trades_opened}/{settings.MAX_TRADES_PER_DAY} trades"
            checks.append(Check("trades_today", False, detail))
            return deny(detail)
        checks.append(
            Check("trades_today", True, f"{book.trades_opened}/{settings.MAX_TRADES_PER_DAY} trades today")
        )

        # ── The trade itself must be coherent ─────────────────────────────────
        coherent, detail = self._levels_are_sane(decision)
        checks.append(Check("trade_levels", coherent, detail))
        if not coherent:
            return deny(detail)

        # ── Size it ───────────────────────────────────────────────────────────
        risk_amount = account.nav * (settings.RISK_PER_TRADE_PCT / 100.0)
        raw_units = risk_amount / decision.risk_per_unit
        units = self.spec.round_units(raw_units)

        if units < self.spec.min_trade_units:
            detail = (
                f"Risking ${risk_amount:,.2f} over a ${decision.risk_per_unit:.2f} stop "
                f"sizes to {raw_units:.2f} oz, below the {self.spec.min_trade_units:g} oz minimum"
            )
            checks.append(Check("position_size", False, detail))
            return deny(detail)

        units = min(units, self.spec.max_trade_units)

        # ── Leverage ceiling ──────────────────────────────────────────────────
        notional = units * decision.entry
        max_notional = account.nav * settings.MAX_LEVERAGE
        if notional > max_notional:
            capped = self.spec.round_units(max_notional / decision.entry)
            if capped < self.spec.min_trade_units:
                detail = (
                    f"Leverage cap of {settings.MAX_LEVERAGE:g}x NAV leaves room for "
                    f"{capped:g} oz, below the minimum trade size"
                )
                checks.append(Check("leverage", False, detail))
                return deny(detail)
            units = capped
            notional = units * decision.entry
            risk_amount = units * decision.risk_per_unit
            checks.append(
                Check("leverage", True, f"Size capped to {units:g} oz by the {settings.MAX_LEVERAGE:g}x limit")
            )
        else:
            checks.append(
                Check(
                    "leverage",
                    True,
                    f"${notional:,.0f} notional is {notional / account.nav:.2f}x NAV "
                    f"(max {settings.MAX_LEVERAGE:g}x)",
                )
            )

        # Recompute the exact risk of the size actually being sent.
        risk_amount = units * decision.risk_per_unit
        risk_pct = risk_amount / account.nav * 100.0
        checks.append(
            Check(
                "position_size",
                True,
                f"{units:g} oz risks ${risk_amount:,.2f} ({risk_pct:.2f}% of NAV) "
                f"over a ${decision.risk_per_unit:.2f} stop",
            )
        )

        return RiskVerdict(
            approved=True,
            units=units,
            risk_amount=risk_amount,
            risk_pct=risk_pct,
            notional=notional,
            checks=checks,
            reason=f"Approved: {units:g} oz risking ${risk_amount:,.2f}",
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def _levels_are_sane(self, decision: Decision) -> tuple[bool, str]:
        """Guard against a malformed order reaching the broker."""
        if not decision.is_trade:
            return False, "No trade signal to size"
        if decision.risk_per_unit <= 0:
            return False, "Stop distance is zero"
        if decision.action == "LONG":
            if not (decision.stop_loss < decision.entry < decision.take_profit):
                return False, "Long levels are not ordered stop < entry < target"
        else:
            if not (decision.take_profit < decision.entry < decision.stop_loss):
                return False, "Short levels are not ordered target < entry < stop"
        reward = abs(decision.take_profit - decision.entry)
        # Rounding the target to the venue's price precision moves the ratio by
        # a fraction of a cent; compare at the precision we report.
        rr = round(reward / decision.risk_per_unit, 2)
        if rr < settings.MIN_RISK_REWARD:
            return False, f"Reward:risk {rr:.2f} is below the {settings.MIN_RISK_REWARD:.2f} minimum"
        return True, (
            f"{decision.action} {decision.entry:.2f} / stop {decision.stop_loss:.2f} / "
            f"target {decision.take_profit:.2f} at {rr:.2f}R"
        )


def new_day_book(nav: float, day: dt.date | None = None, peak_nav: float | None = None) -> DayBook:
    day = day or dt.datetime.now(dt.timezone.utc).date()
    return DayBook(date=day, start_nav=nav, peak_nav=max(peak_nav or nav, nav))
