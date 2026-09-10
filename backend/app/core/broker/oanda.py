"""
OANDA v20 REST client, scoped to XAU_USD.

Notes that matter for gold specifically:
  * Prices must be sent at the instrument's display precision (3 decimals for
    XAU_USD). Sending 5 decimals — the FX default — gets the order rejected
    with PRICE_PRECISION_EXCEEDED.
  * Units are whole troy ounces, so sizing rounds toward zero.
  * The contract spec is read from the account at startup rather than assumed,
    and the hard-coded defaults are only a fallback.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

import httpx

from app.config import settings
from app.core.broker.base import (
    Account,
    Broker,
    BrokerError,
    Candle,
    OrderResult,
    Position,
    Quote,
)
from app.instrument import GOLD, OANDA_INSTRUMENT, InstrumentSpec

logger = logging.getLogger(__name__)

PRACTICE_URL = "https://api-fxpractice.oanda.com/v3"
LIVE_URL = "https://api-fxtrade.oanda.com/v3"

# Agent timeframe -> OANDA granularity.
GRANULARITY = {
    "M1": "M1", "M5": "M5", "M15": "M15", "M30": "M30",
    "H1": "H1", "H4": "H4", "D1": "D",
}

TRADE_TAG = "jarves-gold"


def _parse_time(raw: str) -> dt.datetime:
    """OANDA RFC3339 timestamps carry nanoseconds; trim to microseconds."""
    text = raw.replace("Z", "+00:00")
    if "." in text:
        head, tail = text.split(".", 1)
        frac, _, offset = tail.partition("+")
        text = f"{head}.{frac[:6]}" + (f"+{offset}" if offset else "")
    return dt.datetime.fromisoformat(text).astimezone(dt.timezone.utc)


class OandaBroker(Broker):
    name = "oanda"

    def __init__(
        self,
        api_key: str | None = None,
        account_id: str | None = None,
        environment: str | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.OANDA_API_KEY
        self._account_id = account_id if account_id is not None else settings.OANDA_ACCOUNT_ID
        env = (environment or settings.OANDA_ENVIRONMENT).lower()
        self._live_env = env == "live"
        self._base = LIVE_URL if self._live_env else PRACTICE_URL
        self.spec: InstrumentSpec = GOLD

    # ── plumbing ──────────────────────────────────────────────────────────────

    @property
    def venue(self) -> str:
        return "oanda-live" if self._live_env else "oanda-practice"

    @property
    def configured(self) -> bool:
        return bool(self._api_key and self._account_id)

    def _require_credentials(self) -> None:
        if not self.configured:
            raise BrokerError(
                "OANDA_API_KEY and OANDA_ACCOUNT_ID are not set. Add them to "
                "backend/.env — a practice account is free at oanda.com."
            )

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept-Datetime-Format": "RFC3339",
        }

    async def _request(
        self, method: str, path: str, *, params: dict | None = None, json: dict | None = None
    ) -> dict[str, Any]:
        self._require_credentials()
        url = f"{self._base}{path}"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.request(
                    method, url, headers=self._headers, params=params, json=json
                )
        except httpx.HTTPError as exc:
            raise BrokerError(f"OANDA unreachable: {exc}") from exc

        if response.status_code >= 400:
            detail = response.text
            try:
                payload = response.json()
                detail = payload.get("errorMessage") or payload.get("message") or detail
            except ValueError:
                pass
            raise BrokerError(f"OANDA {response.status_code}: {detail}")
        return response.json()

    # ── contract spec ─────────────────────────────────────────────────────────

    async def load_instrument_spec(self) -> InstrumentSpec:
        """Read XAU_USD's real contract details from the account and cache them."""
        data = await self._request(
            "GET",
            f"/accounts/{self._account_id}/instruments",
            params={"instruments": OANDA_INSTRUMENT},
        )
        entries = data.get("instruments", [])
        if not entries:
            raise BrokerError(
                f"{OANDA_INSTRUMENT} is not tradeable on this OANDA account."
            )
        info = entries[0]
        self.spec = InstrumentSpec(
            price_precision=int(info.get("displayPrecision", GOLD.price_precision)),
            tick_size=10 ** -int(info.get("displayPrecision", GOLD.price_precision)),
            units_precision=int(info.get("tradeUnitsPrecision", GOLD.units_precision)),
            min_trade_units=float(info.get("minimumTradeSize", GOLD.min_trade_units)),
            max_trade_units=float(info.get("maximumOrderUnits", GOLD.max_trade_units)),
        )
        logger.info(
            "Loaded %s spec: precision=%d min_units=%s",
            OANDA_INSTRUMENT, self.spec.price_precision, self.spec.min_trade_units,
        )
        return self.spec

    # ── market data ───────────────────────────────────────────────────────────

    async def get_candles(self, granularity: str = "M15", count: int = 300) -> list[Candle]:
        """Completed mid-price candles, oldest first. Forming bars are dropped."""
        gran = GRANULARITY.get(granularity.upper())
        if gran is None:
            raise BrokerError(f"Unsupported granularity: {granularity}")
        data = await self._request(
            "GET",
            f"/instruments/{OANDA_INSTRUMENT}/candles",
            # count+1 because the newest bar is usually still forming.
            params={"granularity": gran, "count": min(count + 1, 5000), "price": "M"},
        )
        candles: list[Candle] = []
        for row in data.get("candles", []):
            if not row.get("complete", False):
                continue
            mid = row.get("mid", {})
            candles.append(
                Candle(
                    time=_parse_time(row["time"]),
                    open=float(mid["o"]),
                    high=float(mid["h"]),
                    low=float(mid["l"]),
                    close=float(mid["c"]),
                    volume=float(row.get("volume", 0)),
                )
            )
        return candles[-count:]

    async def get_candles_range(
        self, granularity: str, start: dt.datetime, end: dt.datetime
    ) -> list[Candle]:
        """
        Every completed candle between two instants, paging through OANDA's
        5000-bar response limit. Used to load backtest history.
        """
        gran = GRANULARITY.get(granularity.upper())
        if gran is None:
            raise BrokerError(f"Unsupported granularity: {granularity}")

        candles: list[Candle] = []
        cursor = start
        seen: set[dt.datetime] = set()
        while cursor < end:
            data = await self._request(
                "GET",
                f"/instruments/{OANDA_INSTRUMENT}/candles",
                params={
                    "granularity": gran,
                    "from": cursor.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                    "to": end.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                    "count": 5000,
                    "price": "M",
                },
            )
            page = data.get("candles", [])
            if not page:
                break
            added = 0
            for row in page:
                if not row.get("complete", False):
                    continue
                when = _parse_time(row["time"])
                if when in seen:
                    continue
                seen.add(when)
                mid = row.get("mid", {})
                candles.append(
                    Candle(
                        time=when,
                        open=float(mid["o"]),
                        high=float(mid["h"]),
                        low=float(mid["l"]),
                        close=float(mid["c"]),
                        volume=float(row.get("volume", 0)),
                    )
                )
                added += 1
            last_time = _parse_time(page[-1]["time"])
            if added == 0 or last_time <= cursor:
                break
            cursor = last_time + dt.timedelta(seconds=1)

        candles.sort(key=lambda c: c.time)
        return candles

    async def get_quote(self) -> Quote:
        data = await self._request(
            "GET",
            f"/accounts/{self._account_id}/pricing",
            params={"instruments": OANDA_INSTRUMENT},
        )
        prices = data.get("prices", [])
        if not prices:
            raise BrokerError("OANDA returned no price for XAU_USD")
        price = prices[0]
        bids = price.get("bids") or []
        asks = price.get("asks") or []
        if not bids or not asks:
            raise BrokerError("OANDA price has no bid/ask depth")
        return Quote(
            time=_parse_time(price["time"]),
            bid=float(bids[0]["price"]),
            ask=float(asks[0]["price"]),
            tradeable=price.get("tradeable", price.get("status") == "tradeable"),
        )

    # ── account and positions ─────────────────────────────────────────────────

    async def get_account(self) -> Account:
        data = await self._request("GET", f"/accounts/{self._account_id}/summary")
        acct = data["account"]
        return Account(
            balance=float(acct["balance"]),
            nav=float(acct.get("NAV", acct["balance"])),
            unrealized_pl=float(acct.get("unrealizedPL", 0.0)),
            margin_available=float(acct.get("marginAvailable", 0.0)),
            currency=acct.get("currency", "USD"),
            venue=self.venue,
        )

    async def get_open_positions(self) -> list[Position]:
        data = await self._request("GET", f"/accounts/{self._account_id}/openTrades")
        positions: list[Position] = []
        for trade in data.get("trades", []):
            if trade.get("instrument") != OANDA_INSTRUMENT:
                continue
            units = float(trade["currentUnits"])
            stop_order = trade.get("stopLossOrder") or {}
            tp_order = trade.get("takeProfitOrder") or {}
            entry = float(trade["price"])
            stop = float(stop_order["price"]) if stop_order.get("price") else None
            positions.append(
                Position(
                    trade_id=str(trade["id"]),
                    direction="LONG" if units > 0 else "SHORT",
                    units=abs(units),
                    entry_price=entry,
                    stop_loss=stop,
                    take_profit=float(tp_order["price"]) if tp_order.get("price") else None,
                    opened_at=_parse_time(trade["openTime"]),
                    unrealized_pl=float(trade.get("unrealizedPL", 0.0)),
                    initial_risk=abs(entry - stop) if stop else 0.0,
                )
            )
        return positions

    async def get_closed_trades(self, count: int = 50) -> list[dict[str, Any]]:
        """Recently closed gold trades, newest first — used to reconcile results."""
        data = await self._request(
            "GET",
            f"/accounts/{self._account_id}/trades",
            params={"state": "CLOSED", "instrument": OANDA_INSTRUMENT, "count": count},
        )
        out: list[dict[str, Any]] = []
        for trade in data.get("trades", []):
            units = float(trade.get("initialUnits", 0))
            out.append(
                {
                    "trade_id": str(trade["id"]),
                    "direction": "LONG" if units > 0 else "SHORT",
                    "units": abs(units),
                    "entry_price": float(trade["price"]),
                    "exit_price": float(trade.get("averageClosePrice", 0.0)),
                    "realized_pl": float(trade.get("realizedPL", 0.0)),
                    "opened_at": trade.get("openTime", ""),
                    "closed_at": trade.get("closeTime", ""),
                }
            )
        return out

    # ── orders ────────────────────────────────────────────────────────────────

    async def place_order(
        self,
        direction: str,
        units: float,
        stop_loss: float,
        take_profit: float,
        client_id: str,
        reason: str = "",
    ) -> OrderResult:
        """
        Market order with the protective stop and target attached on fill, so
        the position is never live without a stop even if this process dies.
        """
        signed = int(abs(units)) if direction == "LONG" else -int(abs(units))
        if signed == 0:
            return OrderResult(accepted=False, reason="Position size rounded to zero units")

        order: dict[str, Any] = {
            "type": "MARKET",
            "instrument": OANDA_INSTRUMENT,
            "units": str(signed),
            "timeInForce": "FOK",
            "positionFill": "DEFAULT",
            "stopLossOnFill": {
                "price": self.spec.format_price(stop_loss),
                "timeInForce": "GTC",
            },
            "takeProfitOnFill": {
                "price": self.spec.format_price(take_profit),
                "timeInForce": "GTC",
            },
            # The client ID makes the order idempotent: OANDA rejects a repeat
            # of an ID it has already seen, so a retry cannot double the size.
            "clientExtensions": {"id": client_id, "tag": TRADE_TAG, "comment": reason[:128]},
            "tradeClientExtensions": {"id": client_id, "tag": TRADE_TAG, "comment": reason[:128]},
        }

        data = await self._request(
            "POST", f"/accounts/{self._account_id}/orders", json={"order": order}
        )

        cancel = data.get("orderCancelTransaction")
        if cancel:
            return OrderResult(accepted=False, reason=f"Rejected: {cancel.get('reason', 'unknown')}")

        fill = data.get("orderFillTransaction")
        if not fill:
            return OrderResult(accepted=False, reason="No fill transaction returned")

        opened = fill.get("tradeOpened") or {}
        return OrderResult(
            accepted=True,
            trade_id=str(opened.get("tradeID", fill.get("id", ""))),
            fill_price=float(fill.get("price", 0.0)),
            units=abs(float(opened.get("units", signed))),
            reason="filled",
        )

    async def modify_stop(self, trade_id: str, stop_loss: float) -> bool:
        await self._request(
            "PUT",
            f"/accounts/{self._account_id}/trades/{trade_id}/orders",
            json={"stopLoss": {"price": self.spec.format_price(stop_loss), "timeInForce": "GTC"}},
        )
        return True

    async def close_position(self, trade_id: str, reason: str = "") -> OrderResult:
        data = await self._request(
            "PUT",
            f"/accounts/{self._account_id}/trades/{trade_id}/close",
            json={"units": "ALL"},
        )
        fill = data.get("orderFillTransaction") or {}
        return OrderResult(
            accepted=bool(fill),
            trade_id=trade_id,
            fill_price=float(fill.get("price", 0.0)),
            units=abs(float(fill.get("units", 0.0))),
            reason=reason or "closed",
        )
