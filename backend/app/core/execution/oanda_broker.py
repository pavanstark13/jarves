"""
OANDA Practice Account Broker
Supports: EURUSD, USDJPY, GBPUSD, USDCHF, AUDUSD, USDCAD, XAUUSD, BTCUSD
Free practice account: https://www.oanda.com/us-en/trading/demo-account/

Required env vars:
  OANDA_API_KEY     — from My Services > Manage API Access
  OANDA_ACCOUNT_ID  — shown on My Account dashboard
  OANDA_PRACTICE    — "true" (default) uses practice endpoint
"""

from __future__ import annotations
import datetime
from typing import Any

import httpx

from app.config import settings

PRACTICE_URL = "https://api-fxpractice.oanda.com/v3"
LIVE_URL = "https://api-fxtrade.oanda.com/v3"

# OANDA instrument names differ from generic symbols
INSTRUMENT_MAP: dict[str, str] = {
    "EURUSD":  "EUR_USD",
    "USDJPY":  "USD_JPY",
    "GBPUSD":  "GBP_USD",
    "USDCHF":  "USD_CHF",
    "AUDUSD":  "AUD_USD",
    "USDCAD":  "USD_CAD",
    "XAUUSD":  "XAU_USD",
    "BTCUSD":  "BTC_USD",
}

GRANULARITY_MAP: dict[str, str] = {
    "M1": "M1", "M5": "M5", "M15": "M15", "M30": "M30",
    "H1": "H1", "H4": "H4", "D1": "D",
}

# Pip sizes for position-size calculation
PIP_SIZE: dict[str, float] = {
    "EURUSD": 0.0001, "USDJPY": 0.01, "GBPUSD": 0.0001,
    "USDCHF": 0.0001, "AUDUSD": 0.0001, "USDCAD": 0.0001,
    "XAUUSD": 0.01,   "BTCUSD": 1.0,
}


class OANDABroker:
    def __init__(self) -> None:
        practice = getattr(settings, "OANDA_PRACTICE", "true").lower() != "false"
        self._base = PRACTICE_URL if practice else LIVE_URL
        self._api_key = getattr(settings, "OANDA_API_KEY", "")
        self._account = getattr(settings, "OANDA_ACCOUNT_ID", "")
        self._mode = "PRACTICE" if practice else "LIVE"

    # ── headers ──────────────────────────────────────────────────────────────

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type":  "application/json",
        }

    def _require_keys(self) -> None:
        if not self._api_key or not self._account:
            raise ValueError(
                "OANDA_API_KEY and OANDA_ACCOUNT_ID must be set in .env. "
                "Get a free practice account at https://www.oanda.com"
            )

    def _instrument(self, symbol: str) -> str:
        instr = INSTRUMENT_MAP.get(symbol.upper())
        if not instr:
            raise ValueError(f"Unsupported symbol: {symbol}. Supported: {list(INSTRUMENT_MAP)}")
        return instr

    # ── account ───────────────────────────────────────────────────────────────

    async def get_account(self) -> dict[str, Any]:
        self._require_keys()
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{self._base}/accounts/{self._account}/summary", headers=self._headers)
            r.raise_for_status()
        acct = r.json()["account"]
        return {
            "id":         acct["id"],
            "balance":    float(acct["balance"]),
            "nav":        float(acct["NAV"]),
            "unrealized": float(acct["unrealizedPL"]),
            "margin_used":float(acct.get("marginUsed", 0)),
            "currency":   acct["currency"],
            "mode":       self._mode,
        }

    # ── positions ─────────────────────────────────────────────────────────────

    async def get_open_positions(self) -> list[dict[str, Any]]:
        self._require_keys()
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{self._base}/accounts/{self._account}/openPositions", headers=self._headers)
            r.raise_for_status()
        positions = []
        for pos in r.json().get("positions", []):
            symbol = pos["instrument"].replace("_", "")
            long  = pos.get("long",  {})
            short = pos.get("short", {})
            if float(long.get("units", 0)) != 0:
                positions.append({
                    "symbol":    symbol,
                    "direction": "LONG",
                    "units":     float(long["units"]),
                    "avg_price": float(long.get("averagePrice", 0)),
                    "unrealized":float(long.get("unrealizedPL", 0)),
                })
            if float(short.get("units", 0)) != 0:
                positions.append({
                    "symbol":    symbol,
                    "direction": "SHORT",
                    "units":     abs(float(short["units"])),
                    "avg_price": float(short.get("averagePrice", 0)),
                    "unrealized":float(short.get("unrealizedPL", 0)),
                })
        return positions

    # ── orders ────────────────────────────────────────────────────────────────

    async def place_market_order(
        self,
        symbol:    str,
        direction: str,   # "LONG" or "SHORT"
        units:     float,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        comment:   str = "",
    ) -> dict[str, Any]:
        self._require_keys()
        instr = self._instrument(symbol)
        signed_units = str(int(units)) if direction == "LONG" else str(-int(units))

        order: dict[str, Any] = {
            "type":       "MARKET",
            "instrument": instr,
            "units":      signed_units,
        }
        if stop_loss is not None:
            order["stopLossOnFill"] = {"price": f"{stop_loss:.5f}", "timeInForce": "GTC"}
        if take_profit is not None:
            order["takeProfitOnFill"] = {"price": f"{take_profit:.5f}", "timeInForce": "GTC"}
        if comment:
            order["clientExtensions"] = {"comment": comment[:128]}

        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                f"{self._base}/accounts/{self._account}/orders",
                headers=self._headers,
                json={"order": order},
            )
            r.raise_for_status()

        data = r.json()
        fill = data.get("orderFillTransaction", {})
        return {
            "order_id":    fill.get("id", ""),
            "symbol":      symbol,
            "direction":   direction,
            "units":       units,
            "fill_price":  float(fill.get("price", 0)),
            "stop_loss":   stop_loss,
            "take_profit": take_profit,
            "timestamp":   fill.get("time", datetime.datetime.utcnow().isoformat()),
            "mode":        self._mode,
        }

    async def close_position(self, symbol: str, direction: str = "ALL") -> dict[str, Any]:
        self._require_keys()
        instr = self._instrument(symbol)
        body: dict[str, Any] = {}
        if direction == "LONG":
            body = {"longUnits": "ALL"}
        elif direction == "SHORT":
            body = {"shortUnits": "ALL"}
        else:
            body = {"longUnits": "ALL", "shortUnits": "ALL"}

        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.put(
                f"{self._base}/accounts/{self._account}/positions/{instr}/close",
                headers=self._headers,
                json=body,
            )
            r.raise_for_status()
        return {"symbol": symbol, "closed": True, "response": r.json()}

    # ── candles (for scanner) ─────────────────────────────────────────────────

    async def get_candles(
        self, symbol: str, timeframe: str = "H1", count: int = 300
    ) -> list[dict[str, Any]]:
        """Use OANDA candles (free, no extra API key needed for practice accounts)."""
        self._require_keys()
        instr = self._instrument(symbol)
        gran  = GRANULARITY_MAP.get(timeframe.upper(), "H1")
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                f"{self._base}/instruments/{instr}/candles",
                headers=self._headers,
                params={"granularity": gran, "count": count, "price": "M"},
            )
            r.raise_for_status()
        bars = []
        for c_ in r.json().get("candles", []):
            m = c_.get("mid", {})
            bars.append({
                "timestamp": c_["time"],
                "open":  float(m.get("o", 0)),
                "high":  float(m.get("h", 0)),
                "low":   float(m.get("l", 0)),
                "close": float(m.get("c", 0)),
                "volume": float(c_.get("volume", 0)),
            })
        return bars

    # ── pricing ───────────────────────────────────────────────────────────────

    async def get_price(self, symbol: str) -> dict[str, Any]:
        self._require_keys()
        instr = self._instrument(symbol)
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                f"{self._base}/accounts/{self._account}/pricing",
                headers=self._headers,
                params={"instruments": instr},
            )
            r.raise_for_status()
        prices = r.json().get("prices", [{}])[0]
        bid = float(prices.get("bids", [{}])[0].get("price", 0))
        ask = float(prices.get("asks", [{}])[0].get("price", 0))
        return {
            "symbol": symbol,
            "bid": bid, "ask": ask,
            "spread": round(ask - bid, 6),
            "mid": round((bid + ask) / 2, 6),
        }
