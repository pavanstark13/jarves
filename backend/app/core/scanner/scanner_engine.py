"""
Strategy Scanner — Runs SMCStrategy on all 8 symbols every 5 minutes.
When a valid signal fires, it places a paper trade via OANDA.

Enable/disable via POST /auto-trade/toggle.
State is stored in-memory (use Redis in production scale-out).
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from dataclasses import dataclass, field, asdict
from typing import Any

from app.core.data_collection.price_collector import PriceCollector
from app.core.strategy.smc_strategy import SMCStrategy, Signal
from app.core.execution.oanda_broker import OANDABroker, PIP_SIZE

logger = logging.getLogger(__name__)

SYMBOLS = ["EURUSD", "USDJPY", "GBPUSD", "USDCHF", "AUDUSD", "USDCAD", "XAUUSD", "BTCUSD"]

# Risk: 1% of account equity per trade
RISK_PCT = 0.01


@dataclass
class ScannerSignal:
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    confidence: float
    session: str
    filters_passed: list[str]
    filters_failed: list[str]
    reasoning: str
    fired_at: str
    placement_status: str   # PLACED / FAILED / SKIPPED / NO_TRADE
    placement_error: str
    oanda_order_id: str
    units: float


class ScannerEngine:
    def __init__(self) -> None:
        self._collector = PriceCollector()
        self._strategy  = SMCStrategy()
        self._broker    = OANDABroker()

        self.enabled: bool = False
        self.last_scan_at: str = ""
        self.next_scan_at: str = ""
        self.signals: list[ScannerSignal] = []     # rolling last-100
        self._open_symbols: set[str] = set()       # symbols with open paper trades

    # ── main scan ─────────────────────────────────────────────────────────────

    async def run_scan(self) -> list[ScannerSignal]:
        if not self.enabled:
            return []

        self.last_scan_at = datetime.datetime.utcnow().isoformat()
        logger.info("Scanner: starting scan of %d symbols", len(SYMBOLS))

        # Refresh open OANDA positions
        await self._refresh_open_symbols()

        fired: list[ScannerSignal] = []
        for symbol in SYMBOLS:
            signal = await self._scan_symbol(symbol)
            if signal:
                fired.append(signal)
                self.signals.append(signal)

        # Keep only last 100
        self.signals = self.signals[-100:]

        next_dt = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        self.next_scan_at = next_dt.isoformat()
        logger.info("Scanner: scan complete. %d signal(s) fired.", len(fired))
        return fired

    async def _scan_symbol(self, symbol: str) -> ScannerSignal | None:
        try:
            # Fetch bars from OANDA (no Twelve Data quota consumed)
            m15 = await self._broker.get_candles(symbol, "M15", count=100)
            h1  = await self._broker.get_candles(symbol, "H1",  count=200)
            h4  = await self._broker.get_candles(symbol, "H4",  count=200)
            d1  = await self._broker.get_candles(symbol, "D1",  count=100)
        except Exception as exc:
            # OANDA may not have the key configured; fall back to Twelve Data
            try:
                m15 = await self._collector.fetch(symbol, "M15", count=100)
                h1  = await self._collector.fetch(symbol, "H1",  count=200)
                h4  = await self._collector.fetch(symbol, "H4",  count=200)
                d1  = await self._collector.fetch(symbol, "D1",  count=100)
            except Exception as exc2:
                logger.warning("Scanner: %s fetch failed: %s", symbol, exc2)
                return None

        if len(m15) < 30:
            return None

        try:
            sig: Signal = self._strategy.evaluate(
                symbol=symbol,
                h1_bars=h1,
                h4_bars=h4,
                d1_bars=d1,
                m15_bars=m15,
                news_events=[],
            )
        except Exception as exc:
            logger.warning("Scanner: strategy eval failed for %s: %s", symbol, exc)
            return None

        now = datetime.datetime.utcnow().isoformat()
        scanner_sig = ScannerSignal(
            symbol=symbol,
            direction=sig.direction,
            entry_price=sig.entry_price,
            stop_loss=sig.stop_loss,
            take_profit=sig.take_profit,
            risk_reward=sig.risk_reward,
            confidence=sig.confidence,
            session=sig.session,
            filters_passed=sig.filters_passed,
            filters_failed=sig.filters_failed,
            reasoning=sig.reasoning,
            fired_at=now,
            placement_status="NO_TRADE",
            placement_error="",
            oanda_order_id="",
            units=0,
        )

        if sig.direction == "NO_TRADE":
            return None  # don't log NO_TRADE signals in the feed

        # Skip if already holding a position on this symbol
        if symbol in self._open_symbols:
            scanner_sig.placement_status = "SKIPPED"
            scanner_sig.placement_error  = "Already have open position"
            logger.info("Scanner: %s signal skipped — open position exists", symbol)
            return scanner_sig

        # Place the trade
        await self._place_trade(scanner_sig)
        return scanner_sig

    async def _place_trade(self, sig: ScannerSignal) -> None:
        try:
            account = await self._broker.get_account()
            balance = account["balance"]
            risk_amount = balance * RISK_PCT
            sl_distance = abs(sig.entry_price - sig.stop_loss)
            if sl_distance <= 0:
                sig.placement_status = "FAILED"
                sig.placement_error  = "Zero SL distance"
                return

            units = max(1, int(risk_amount / sl_distance))
            sig.units = units

            result = await self._broker.place_market_order(
                symbol=sig.symbol,
                direction=sig.direction,
                units=units,
                stop_loss=sig.stop_loss,
                take_profit=sig.take_profit,
                comment=f"Jarves SMC {sig.session}",
            )
            sig.placement_status = "PLACED"
            sig.oanda_order_id   = result.get("order_id", "")
            self._open_symbols.add(sig.symbol)
            logger.info(
                "Scanner: placed %s %s @ %.5f SL=%.5f TP=%.5f units=%d",
                sig.direction, sig.symbol, sig.entry_price,
                sig.stop_loss, sig.take_profit, units,
            )
        except Exception as exc:
            sig.placement_status = "FAILED"
            sig.placement_error  = str(exc)
            logger.error("Scanner: order placement failed for %s: %s", sig.symbol, exc)

    async def _refresh_open_symbols(self) -> None:
        try:
            positions = await self._broker.get_open_positions()
            self._open_symbols = {p["symbol"] for p in positions}
        except Exception:
            pass   # keep existing set if OANDA unreachable

    # ── status ────────────────────────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        return {
            "enabled":        self.enabled,
            "last_scan_at":   self.last_scan_at,
            "next_scan_at":   self.next_scan_at,
            "signals_today":  self._count_today(),
            "open_symbols":   list(self._open_symbols),
            "signals_feed":   [asdict(s) for s in reversed(self.signals[-20:])],
        }

    def _count_today(self) -> int:
        today = datetime.datetime.utcnow().date().isoformat()
        return sum(1 for s in self.signals if s.fired_at.startswith(today))


# Singleton used by both the scheduler and the API routes
scanner = ScannerEngine()
