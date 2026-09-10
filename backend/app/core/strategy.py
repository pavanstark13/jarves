"""
The gold strategy: trend continuation from a pullback, decided by rules.

Every gate below is a measurement of data that already exists — a moving
average that is where it is, a bar that closed where it closed, a spread that
is what the broker is quoting right now. Nothing here forecasts, scores
sentiment, or asks a model for an opinion. If a single gate fails, the answer
is STAND_ASIDE, and the failure is recorded with the number that caused it.

The shape of a trade:

  Regime      H4 EMA50/EMA200 stacked and sloping     -> direction, or nothing
  Alignment   D1 EMA20 slope does not oppose it       -> no trading into the daily tide
  Bias        H1 EMA20/EMA50 stacked the same way     -> the intermediate trend agrees
  Structure   M15 swings are still higher/lower      -> the trend is intact on entry TF
  Pullback    price back at value (EMA20 or an FVG)   -> we buy the dip, never the spike
  Trigger     last M15 bar closed back in-trend       -> the pullback is over
  Volatility  M15 ATR inside a workable band          -> not dead, not disorderly
  Spread      live spread small vs that ATR           -> the cost does not eat the edge
  Extension   price not stretched far from EMA20      -> no chasing
  Stop        structural stop within risk bounds      -> the trade is sizeable

Stops go beyond the swing that would invalidate the idea; the target is a
fixed multiple of that distance. Both are decided before entry and neither
moves against the position afterwards.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

from app.config import settings
from app.core import indicators as ind
from app.core.broker.base import Candle, Quote
from app.core.market import session as session_clock
from app.core.market.calendar import Blackout
from app.instrument import GOLD, SYMBOL

# Bars each timeframe needs before it can be trusted.
MIN_BARS = {"M15": 120, "H1": 220, "H4": 220, "D1": 60}

STAND_ASIDE = "STAND_ASIDE"
LONG = "LONG"
SHORT = "SHORT"


@dataclass
class Gate:
    """One rule, its verdict, and the number behind the verdict."""

    name: str
    passed: bool
    detail: str

    def __post_init__(self) -> None:
        # Comparisons against numpy values return numpy booleans, which are not
        # JSON serialisable. Normalise here so callers never have to care.
        self.passed = bool(self.passed)

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass
class Decision:
    time: dt.datetime
    action: str                       # LONG | SHORT | STAND_ASIDE
    symbol: str = SYMBOL
    entry: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_per_unit: float = 0.0        # $/oz between entry and stop
    risk_reward: float = 0.0
    gates: list[Gate] = field(default_factory=list)
    readings: dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    @property
    def is_trade(self) -> bool:
        return self.action in (LONG, SHORT)

    @property
    def failed_gates(self) -> list[Gate]:
        return [g for g in self.gates if not g.passed]

    @property
    def blocker(self) -> str:
        failed = self.failed_gates
        return failed[0].detail if failed else ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "time": self.time.isoformat(),
            "action": self.action,
            "symbol": self.symbol,
            "entry": round(self.entry, 3),
            "stop_loss": round(self.stop_loss, 3),
            "take_profit": round(self.take_profit, 3),
            "risk_per_unit": round(self.risk_per_unit, 3),
            "risk_reward": round(self.risk_reward, 2),
            "gates": [g.as_dict() for g in self.gates],
            "readings": self.readings,
            "summary": self.summary,
        }


@dataclass
class MarketSnapshot:
    """Everything the strategy is allowed to look at, all of it observed."""

    time: dt.datetime
    quote: Quote
    m15: list[Candle]
    h1: list[Candle]
    h4: list[Candle]
    d1: list[Candle]
    blackout: Blackout


def _closes(candles: list[Candle]) -> list[float]:
    return [c.close for c in candles]


class GoldStrategy:
    """Rule set for XAU/USD. Stateless — the same snapshot always decides the same."""

    # RSI 50 is the momentum midline: a pullback pushes RSI through it, and
    # the trigger bar pushes it back. Both are crossings of the same level.
    RSI_MIDLINE = 50.0
    PULLBACK_LOOKBACK = 10    # bars the pullback must have happened within
    STRUCTURE_LOOKBACK = 60   # bars used to read swing structure (15h of M15)
    SWING_LOOKBACK = 30       # bars to source the structural stop from

    def evaluate(self, snapshot: MarketSnapshot) -> Decision:
        now = snapshot.time
        gates: list[Gate] = []
        readings: dict[str, Any] = {}

        # ── Gate: enough completed history on every timeframe ─────────────────
        missing = [
            f"{tf} has {len(bars)}/{need} bars"
            for tf, bars, need in (
                ("M15", snapshot.m15, MIN_BARS["M15"]),
                ("H1", snapshot.h1, MIN_BARS["H1"]),
                ("H4", snapshot.h4, MIN_BARS["H4"]),
                ("D1", snapshot.d1, MIN_BARS["D1"]),
            )
            if len(bars) < need
        ]
        if missing:
            gates.append(Gate("data", False, "Insufficient history: " + "; ".join(missing)))
            return self._stand_aside(now, gates, readings, "Waiting for enough completed candles")
        gates.append(Gate("data", True, "All four timeframes have full history"))

        # ── Gate: the venue is actually quoting a usable market ───────────────
        quote = snapshot.quote
        if not quote.tradeable or quote.spread <= 0:
            gates.append(Gate("market_open", False, "Broker is not quoting a tradeable market"))
            return self._stand_aside(now, gates, readings, "Market is not tradeable right now")
        gates.append(Gate("market_open", True, f"Quoting {quote.bid:.2f}/{quote.ask:.2f}"))

        # ── Gate: inside a session we are willing to trade ────────────────────
        clock = session_clock.evaluate(now)
        readings["session"] = clock.as_dict()
        gates.append(Gate("session", clock.can_open, clock.reason()))

        # ── Gate: no US release inside the blackout window ────────────────────
        readings["news"] = snapshot.blackout.as_dict()
        gates.append(Gate("news", not snapshot.blackout.active, snapshot.blackout.reason()))

        # ── Direction: H4 regime ──────────────────────────────────────────────
        h4_closes = _closes(snapshot.h4)
        h4_ema50 = ind.ema(h4_closes, 50)
        h4_ema200 = ind.ema(h4_closes, 200)
        h4_slope = ind.slope(h4_ema50, 6)
        h4_price = h4_closes[-1]
        readings["h4"] = {
            "close": round(h4_price, 3),
            "ema50": round(float(h4_ema50[-1]), 3),
            "ema200": round(float(h4_ema200[-1]), 3),
            "ema50_slope": round(h4_slope, 3),
        }

        if h4_ema50[-1] > h4_ema200[-1] and h4_slope > 0 and h4_price > h4_ema50[-1]:
            direction = LONG
        elif h4_ema50[-1] < h4_ema200[-1] and h4_slope < 0 and h4_price < h4_ema50[-1]:
            direction = SHORT
        else:
            gates.append(
                Gate(
                    "regime",
                    False,
                    f"H4 has no trend: EMA50 {h4_ema50[-1]:.2f} vs EMA200 "
                    f"{h4_ema200[-1]:.2f}, slope {h4_slope:+.2f}",
                )
            )
            return self._stand_aside(now, gates, readings, "No H4 trend to trade with")

        gates.append(
            Gate(
                "regime",
                True,
                f"H4 {direction}: EMA50 {h4_ema50[-1]:.2f} "
                f"{'>' if direction == LONG else '<'} EMA200 {h4_ema200[-1]:.2f}, "
                f"slope {h4_slope:+.2f}",
            )
        )

        # ── Gate: the daily tide is not against us ────────────────────────────
        d1_closes = _closes(snapshot.d1)
        d1_ema20 = ind.ema(d1_closes, 20)
        d1_slope = ind.slope(d1_ema20, 3)
        readings["d1"] = {
            "close": round(d1_closes[-1], 3),
            "ema20": round(float(d1_ema20[-1]), 3),
            "ema20_slope": round(d1_slope, 3),
        }
        daily_ok = d1_slope >= 0 if direction == LONG else d1_slope <= 0
        gates.append(
            Gate(
                "daily_alignment",
                daily_ok,
                f"D1 EMA20 slope {d1_slope:+.2f} "
                f"{'supports' if daily_ok else 'opposes'} a {direction}",
            )
        )

        # ── Gate: H1 agrees with the H4 direction ─────────────────────────────
        h1_closes = _closes(snapshot.h1)
        h1_ema20 = ind.ema(h1_closes, 20)
        h1_ema50 = ind.ema(h1_closes, 50)
        readings["h1"] = {
            "close": round(h1_closes[-1], 3),
            "ema20": round(float(h1_ema20[-1]), 3),
            "ema50": round(float(h1_ema50[-1]), 3),
        }
        if direction == LONG:
            bias_ok = h1_ema20[-1] > h1_ema50[-1] and h1_closes[-1] > h1_ema50[-1]
        else:
            bias_ok = h1_ema20[-1] < h1_ema50[-1] and h1_closes[-1] < h1_ema50[-1]
        gates.append(
            Gate(
                "bias",
                bias_ok,
                f"H1 EMA20 {h1_ema20[-1]:.2f} / EMA50 {h1_ema50[-1]:.2f} "
                f"{'confirm' if bias_ok else 'do not confirm'} the {direction}",
            )
        )

        # ── The entry timeframe ───────────────────────────────────────────────
        m15 = snapshot.m15
        m_closes = _closes(m15)
        m_highs = [c.high for c in m15]
        m_lows = [c.low for c in m15]
        m_ema20 = ind.ema(m_closes, 20)
        atr = ind.atr(m_highs, m_lows, m_closes, 14)
        last = m15[-1]
        rsi_now = ind.rsi(m_closes, 14)
        rsi_hist = ind.rsi_series(
            m_closes[-(self.PULLBACK_LOOKBACK + 30):], 14
        )[-self.PULLBACK_LOOKBACK:]
        readings["m15"] = {
            "close": round(last.close, 3),
            "ema20": round(float(m_ema20[-1]), 3),
            "atr14": round(atr, 3),
            "rsi14": round(rsi_now, 1),
            "bar_time": last.time.isoformat(),
        }

        # ── Gate: the M15 chart is still building trend structure ─────────────
        structure_ok, shape = ind.swing_structure(
            m_highs, m_lows, direction, self.STRUCTURE_LOOKBACK
        )
        bos = ind.broke_structure(m_highs, m_lows, m_closes, direction, self.STRUCTURE_LOOKBACK)
        structure_ok = structure_ok or bos
        readings["m15"]["structure"] = shape
        readings["m15"]["break_of_structure"] = bos
        gates.append(
            Gate(
                "structure",
                structure_ok,
                f"M15 swings show {shape}"
                + (" with a confirmed break of structure" if bos else "")
                + ("" if structure_ok else " — not a trending structure"),
            )
        )

        # ── Gate: price actually pulled back to value ─────────────────────────
        distance_to_ema = abs(last.close - float(m_ema20[-1]))
        touched = ind.touched_level(m_highs, m_lows, m_ema20, direction, self.PULLBACK_LOOKBACK)
        gaps = ind.fair_value_gaps(m_highs, m_lows, direction, lookback=30)
        in_gap = any(low <= last.close <= high for low, high in gaps)
        if direction == LONG:
            reset = any(v < self.RSI_MIDLINE for v in rsi_hist if v == v)
        else:
            reset = any(v > self.RSI_MIDLINE for v in rsi_hist if v == v)
        pullback_ok = (touched or in_gap) and reset
        where = "traded back to the EMA20" if touched else (
            "closed inside an unfilled imbalance" if in_gap else "never returned to value"
        )
        gates.append(
            Gate(
                "pullback",
                pullback_ok,
                f"price {where} within {self.PULLBACK_LOOKBACK} bars and momentum "
                f"{'reset through' if reset else 'never crossed'} RSI {self.RSI_MIDLINE:.0f}",
            )
        )

        # ── Gate: the pullback is over — last bar closed back in trend ────────
        if direction == LONG:
            trigger_ok = (
                last.close > last.open
                and last.close > float(m_ema20[-1])
                and rsi_now >= self.RSI_MIDLINE
            )
        else:
            trigger_ok = (
                last.close < last.open
                and last.close < float(m_ema20[-1])
                and rsi_now <= self.RSI_MIDLINE
            )
        gates.append(
            Gate(
                "trigger",
                trigger_ok,
                f"last M15 bar {'reclaimed' if trigger_ok else 'did not reclaim'} the EMA20 "
                f"in the {direction} direction (close {last.close:.2f}, RSI {rsi_now:.1f})",
            )
        )

        # ── Gate: volatility is workable ──────────────────────────────────────
        vol_ok = settings.MIN_ATR_USD <= atr <= settings.MAX_ATR_USD
        gates.append(
            Gate(
                "volatility",
                vol_ok,
                f"M15 ATR ${atr:.2f} "
                f"{'inside' if vol_ok else 'outside'} the ${settings.MIN_ATR_USD:.2f}-"
                f"${settings.MAX_ATR_USD:.2f} band",
            )
        )

        # ── Gate: the spread is not eating the trade ──────────────────────────
        spread = quote.spread
        spread_ratio = spread / atr if atr > 0 else 99.0
        spread_ok = spread <= settings.MAX_SPREAD_USD and spread_ratio <= settings.MAX_SPREAD_ATR_RATIO
        readings["spread"] = {"usd": round(spread, 3), "atr_ratio": round(spread_ratio, 3)}
        gates.append(
            Gate(
                "spread",
                spread_ok,
                f"spread ${spread:.2f} = {spread_ratio:.2f} ATR "
                f"(limits ${settings.MAX_SPREAD_USD:.2f} / {settings.MAX_SPREAD_ATR_RATIO:.2f} ATR)",
            )
        )

        # ── Gate: not chasing an extended move ────────────────────────────────
        extension = distance_to_ema / atr if atr > 0 else 99.0
        extension_ok = extension <= settings.MAX_EXTENSION_ATR
        gates.append(
            Gate(
                "extension",
                extension_ok,
                f"price is {extension:.2f} ATR from the M15 EMA20 "
                f"(max {settings.MAX_EXTENSION_ATR:.2f})",
            )
        )

        # ── Build the trade levels from structure ─────────────────────────────
        entry = GOLD.round_price(quote.ask if direction == LONG else quote.bid)
        stop, stop_note = self._structural_stop(direction, entry, m_highs, m_lows, atr)
        stop = GOLD.round_price(stop)
        risk = abs(entry - stop)
        stop_ok = settings.MIN_STOP_USD <= risk <= settings.MAX_STOP_USD
        gates.append(
            Gate(
                "stop_distance",
                stop_ok,
                f"structural stop is ${risk:.2f} away ({stop_note}); allowed "
                f"${settings.MIN_STOP_USD:.2f}-${settings.MAX_STOP_USD:.2f}",
            )
        )

        target = (
            entry + risk * settings.MIN_RISK_REWARD
            if direction == LONG
            else entry - risk * settings.MIN_RISK_REWARD
        )

        decision = Decision(
            time=now,
            action=direction if all(g.passed for g in gates) else STAND_ASIDE,
            entry=entry,
            stop_loss=stop,
            take_profit=GOLD.round_price(target),
            risk_per_unit=round(risk, 3),
            risk_reward=settings.MIN_RISK_REWARD,
            gates=gates,
            readings=readings,
        )
        decision.summary = self._summarise(decision, direction)
        return decision

    # ── helpers ───────────────────────────────────────────────────────────────

    def _structural_stop(
        self, direction: str, entry: float, highs: list[float], lows: list[float], atr: float
    ) -> tuple[float, str]:
        """
        Place the stop beyond the swing that would prove the setup wrong, with an
        ATR buffer so ordinary noise does not reach it.
        """
        buffer = settings.STOP_ATR_MULTIPLE * atr
        if direction == LONG:
            swing = ind.last_swing_low(lows, lookback=self.SWING_LOOKBACK)
            if swing is None:
                swing = min(lows[-10:])
                note = "10-bar low"
            else:
                note = "last swing low"
            stop = swing - buffer
            floor = entry - settings.MIN_STOP_USD
            if stop > floor:
                stop, note = floor, f"{note}, widened to the minimum stop"
            return stop, note

        swing = ind.last_swing_high(highs, lookback=self.SWING_LOOKBACK)
        if swing is None:
            swing = max(highs[-10:])
            note = "10-bar high"
        else:
            note = "last swing high"
        stop = swing + buffer
        ceiling = entry + settings.MIN_STOP_USD
        if stop < ceiling:
            stop, note = ceiling, f"{note}, widened to the minimum stop"
        return stop, note

    def _stand_aside(
        self, now: dt.datetime, gates: list[Gate], readings: dict[str, Any], why: str
    ) -> Decision:
        return Decision(time=now, action=STAND_ASIDE, gates=gates, readings=readings, summary=why)

    @staticmethod
    def _summarise(decision: Decision, direction: str) -> str:
        if decision.is_trade:
            return (
                f"{direction} {SYMBOL} at {decision.entry:.2f}, stop {decision.stop_loss:.2f} "
                f"(${decision.risk_per_unit:.2f}/oz), target {decision.take_profit:.2f} "
                f"at {decision.risk_reward:.1f}R — all {len(decision.gates)} gates passed"
            )
        failed = decision.failed_gates
        names = ", ".join(g.name for g in failed)
        return f"Stand aside — {direction} setup blocked by: {names}"
