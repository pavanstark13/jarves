"""
MetaTrader 5 adapter — for MultiBank and any other MT5 broker.

This talks to a MetaTrader 5 *terminal* running on the same machine through
MetaQuotes' official Python package. The terminal holds the connection to the
broker; this process drives the terminal.

MT5 differs from a REST venue in ways that silently break integrations, so each
one is handled explicitly here:

  * **Size is in lots, not ounces.** One gold lot is normally 100 oz. The agent
    reasons in ounces throughout; the conversion happens only here, rounded
    down to the broker's volume step.
  * **Times are server times.** MT5 stamps candles and ticks in the broker's
    timezone but encodes them as if they were UTC. MultiBank and most others
    run UTC+2/+3, so treating them as UTC would shift the London and New York
    session windows by hours. The offset is detected at startup and removed.
  * **Filling modes are per symbol.** Sending FOK to a symbol that only accepts
    IOC gets the order rejected with "Unsupported filling mode". The mode is
    read from the symbol and matched.
  * **Stops have a minimum distance.** Servers reject a stop placed closer than
    `trade_stops_level` points from the market.
  * **Symbol names vary by broker.** Gold may be XAUUSD, XAUUSD.m, GOLD or a
    suffixed variant. The symbol is discovered from the terminal, or pinned
    with MT5_SYMBOL.
  * **The API is synchronous and single-threaded.** Every call is serialised
    onto one worker thread so it never blocks the event loop and never runs
    two terminal calls at once.

Only positions carrying our magic number are ever read or touched, so manual
trades in the same account are left completely alone.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

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
from app.instrument import GOLD, SYMBOL, InstrumentSpec

logger = logging.getLogger(__name__)

# Names gold trades under across MT5 brokers, best match first.
GOLD_SYMBOL_CANDIDATES = ("XAUUSD", "GOLD", "XAUUSD.", "XAUUSDm", "XAUUSD_", "XAU/USD")

TIMEFRAMES = ("M1", "M5", "M15", "M30", "H1", "H4", "D1")

# MT5 truncates order comments; keep well inside the limit.
MAX_COMMENT = 31


def _load_mt5() -> Any:
    """
    Import the MetaTrader5 package, with an error that says what to do.

    MetaQuotes publishes Windows wheels only — there is no Linux build — so an
    import failure here is almost always "this is not running on Windows next
    to a terminal" rather than a missing pip install.
    """
    try:
        import MetaTrader5 as mt5  # type: ignore[import-not-found]
    except ImportError as exc:
        raise BrokerError(
            "The MetaTrader5 package is not available. MetaQuotes publishes it "
            "for Windows only, and it drives a MetaTrader 5 terminal running on "
            "the same machine. Run this backend on Windows alongside the "
            "terminal and 'pip install MetaTrader5', or set BROKER=oanda. "
            "See the MetaTrader 5 section of the README."
        ) from exc
    return mt5


class Mt5Broker(Broker):
    name = "mt5"

    def __init__(
        self,
        login: int | None = None,
        password: str | None = None,
        server: str | None = None,
        terminal_path: str | None = None,
        symbol: str | None = None,
        magic: int | None = None,
    ) -> None:
        self._login = login if login is not None else settings.MT5_LOGIN
        self._password = password if password is not None else settings.MT5_PASSWORD
        self._server = server if server is not None else settings.MT5_SERVER
        self._path = terminal_path if terminal_path is not None else settings.MT5_TERMINAL_PATH
        self._symbol_override = symbol if symbol is not None else settings.MT5_SYMBOL
        self._magic = magic if magic is not None else settings.MT5_MAGIC

        self._mt5: Any = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mt5")
        self._connected = False
        self._symbol: str = self._symbol_override or ""
        self._server_offset = dt.timedelta(0)
        self.spec: InstrumentSpec = GOLD

    # ── plumbing ──────────────────────────────────────────────────────────────

    @property
    def venue(self) -> str:
        return f"mt5:{self._server}" if self._server else "mt5"

    @property
    def configured(self) -> bool:
        return bool(self._login and self._password and self._server)

    @property
    def symbol(self) -> str:
        return self._symbol or self._symbol_override or SYMBOL

    async def _call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Run a terminal call on the single MT5 worker thread."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, lambda: fn(*args, **kwargs))

    def _fail(self, action: str) -> BrokerError:
        code, description = self._mt5.last_error()
        return BrokerError(f"MT5 {action} failed ({code}): {description}")

    async def connect(self) -> None:
        """Attach to the terminal and log the account in. Idempotent."""
        if self._connected:
            return
        self._mt5 = _load_mt5()
        if not self.configured:
            raise BrokerError(
                "MT5_LOGIN, MT5_PASSWORD and MT5_SERVER are not set. For "
                "MultiBank these are the credentials and server name shown in "
                "the terminal under File > Open an Account."
            )

        options: dict[str, Any] = {
            "login": int(self._login),
            "password": self._password,
            "server": self._server,
            "timeout": 60_000,
        }
        if self._path:
            options["path"] = self._path

        if not await self._call(self._mt5.initialize, **options):
            raise self._fail("initialize")

        self._connected = True
        await self._resolve_symbol()
        await self._detect_server_offset()
        logger.info(
            "MT5 connected: %s on %s, trading %s", self._login, self._server, self._symbol
        )

    async def shutdown(self) -> None:
        if self._connected and self._mt5 is not None:
            await self._call(self._mt5.shutdown)
        self._connected = False
        self._executor.shutdown(wait=False)

    # ── symbol discovery ──────────────────────────────────────────────────────

    async def _resolve_symbol(self) -> str:
        """
        Find what this broker calls gold, and put it in Market Watch.

        A pinned MT5_SYMBOL is used as given; otherwise the terminal's own
        symbol list decides, so a broker suffix like XAUUSD.m is picked up
        rather than guessed at.
        """
        if self._symbol_override:
            if not await self._call(self._mt5.symbol_select, self._symbol_override, True):
                raise BrokerError(
                    f"MT5_SYMBOL '{self._symbol_override}' is not available on this "
                    f"account. Check the exact name in the terminal's Market Watch."
                )
            self._symbol = self._symbol_override
            return self._symbol

        symbols = await self._call(self._mt5.symbols_get)
        if not symbols:
            raise self._fail("symbols_get")
        names = [s.name for s in symbols]

        match = next((c for c in GOLD_SYMBOL_CANDIDATES if c in names), None)
        if match is None:
            # Fall back to any symbol that looks like spot gold against the dollar.
            gold_like = [
                n for n in names
                if n.upper().startswith(("XAUUSD", "GOLD")) and "XAUEUR" not in n.upper()
            ]
            gold_like.sort(key=len)  # the plainest name first
            match = gold_like[0] if gold_like else None

        if match is None:
            raise BrokerError(
                "No gold symbol found on this MT5 account. Set MT5_SYMBOL to the "
                "exact name shown in the terminal's Market Watch."
            )

        if not await self._call(self._mt5.symbol_select, match, True):
            raise BrokerError(f"Could not select {match} in Market Watch")
        self._symbol = match
        return match

    # ── server time ───────────────────────────────────────────────────────────

    async def _detect_server_offset(self) -> dt.timedelta:
        """
        Work out how far the broker's clock runs from UTC.

        MT5 reports times in the server's timezone but encodes them as Unix
        timestamps, so a candle stamped 10:00 on a UTC+3 server is really 07:00
        UTC. Getting this wrong shifts every session gate by hours, so the
        offset is measured from a live tick and can be pinned in config.
        """
        if settings.MT5_SERVER_UTC_OFFSET_HOURS is not None:
            self._server_offset = dt.timedelta(hours=settings.MT5_SERVER_UTC_OFFSET_HOURS)
            logger.info("MT5 server offset pinned to %s", self._server_offset)
            return self._server_offset

        tick = await self._call(self._mt5.symbol_info_tick, self._symbol)
        if tick is None:
            logger.warning("No tick available to measure the MT5 server offset; assuming UTC")
            return self._server_offset

        raw = dt.datetime.fromtimestamp(tick.time, tz=dt.timezone.utc)
        difference = (raw - dt.datetime.now(dt.timezone.utc)).total_seconds()

        # A stale tick (the market is shut) makes this meaningless. Only trust a
        # measurement inside a plausible timezone range.
        if abs(difference) > 14 * 3600:
            logger.warning(
                "The last MT5 tick is %.1f hours from now — the market is "
                "probably closed. Set MT5_SERVER_UTC_OFFSET_HOURS so session "
                "windows are not shifted.",
                difference / 3600,
            )
            return self._server_offset

        # Servers sit on whole or half hours.
        self._server_offset = dt.timedelta(minutes=round(difference / 1800.0) * 30)
        logger.info("MT5 server clock detected at UTC%+.1fh",
                    self._server_offset.total_seconds() / 3600)
        return self._server_offset

    def _to_utc(self, server_epoch: float) -> dt.datetime:
        """Convert an MT5 timestamp into real UTC."""
        raw = dt.datetime.fromtimestamp(server_epoch, tz=dt.timezone.utc)
        return raw - self._server_offset

    # ── contract spec ─────────────────────────────────────────────────────────

    async def load_instrument_spec(self) -> InstrumentSpec:
        """Read the real gold contract from the terminal and cache it."""
        await self.connect()
        info = await self._call(self._mt5.symbol_info, self._symbol)
        if info is None:
            raise self._fail(f"symbol_info({self._symbol})")

        contract_size = float(getattr(info, "trade_contract_size", 100.0)) or 100.0
        volume_step = float(getattr(info, "volume_step", 0.01)) or 0.01
        volume_min = float(getattr(info, "volume_min", 0.01)) or 0.01
        volume_max = float(getattr(info, "volume_max", 100.0)) or 100.0
        digits = int(getattr(info, "digits", 2))
        point = float(getattr(info, "point", 10 ** -digits)) or 10 ** -digits
        stops_level = float(getattr(info, "trade_stops_level", 0.0))

        units_step = volume_step * contract_size
        self.spec = InstrumentSpec(
            symbol=self._symbol,
            price_precision=digits,
            tick_size=point,
            units_step=units_step,
            units_precision=0 if units_step >= 1 else 2,
            min_trade_units=volume_min * contract_size,
            max_trade_units=volume_max * contract_size,
            contract_size=contract_size,
            min_stop_distance=stops_level * point,
        )
        logger.info(
            "%s contract: 1 lot = %g oz, step %g lots (%g oz), %d digits, "
            "min stop %.2f",
            self._symbol, contract_size, volume_step, units_step, digits,
            self.spec.min_stop_distance,
        )
        return self.spec

    def _filling_mode(self, info: Any) -> int:
        """
        Pick a filling mode the symbol actually accepts.

        `filling_mode` is a bitmask; sending an unsupported one is a very
        common cause of rejected MT5 orders.
        """
        mask = int(getattr(info, "filling_mode", 0))
        if mask & 1:                       # SYMBOL_FILLING_FOK
            return self._mt5.ORDER_FILLING_FOK
        if mask & 2:                       # SYMBOL_FILLING_IOC
            return self._mt5.ORDER_FILLING_IOC
        return self._mt5.ORDER_FILLING_RETURN

    # ── market data ───────────────────────────────────────────────────────────

    async def get_candles(self, granularity: str = "M15", count: int = 300) -> list[Candle]:
        """Completed candles, oldest first. Position 1 skips the forming bar."""
        await self.connect()
        timeframe = granularity.upper()
        if timeframe not in TIMEFRAMES:
            raise BrokerError(f"Unsupported granularity: {granularity}")
        constant = getattr(self._mt5, f"TIMEFRAME_{timeframe}")

        rates = await self._call(
            self._mt5.copy_rates_from_pos, self._symbol, constant, 1, count
        )
        if rates is None or len(rates) == 0:
            raise self._fail(f"copy_rates_from_pos({self._symbol}, {timeframe})")

        return [
            Candle(
                time=self._to_utc(float(row["time"])),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["tick_volume"]),
            )
            for row in rates
        ]

    async def get_quote(self) -> Quote:
        await self.connect()
        tick = await self._call(self._mt5.symbol_info_tick, self._symbol)
        if tick is None:
            raise self._fail(f"symbol_info_tick({self._symbol})")
        info = await self._call(self._mt5.symbol_info, self._symbol)

        # The symbol has to be quoting and open for orders, not merely visible.
        trade_mode = int(getattr(info, "trade_mode", 0)) if info else 0
        tradeable = bool(tick.bid and tick.ask) and trade_mode != 0
        return Quote(
            time=self._to_utc(float(tick.time)),
            bid=float(tick.bid),
            ask=float(tick.ask),
            tradeable=tradeable,
        )

    # ── account and positions ─────────────────────────────────────────────────

    async def get_account(self) -> Account:
        await self.connect()
        info = await self._call(self._mt5.account_info)
        if info is None:
            raise self._fail("account_info")
        return Account(
            balance=float(info.balance),
            nav=float(info.equity),
            unrealized_pl=float(info.profit),
            margin_available=float(info.margin_free),
            currency=info.currency,
            venue=self.venue,
        )

    async def get_open_positions(self) -> list[Position]:
        """Only positions this agent opened — manual trades are never touched."""
        await self.connect()
        raw = await self._call(self._mt5.positions_get, symbol=self._symbol)
        positions: list[Position] = []
        for item in raw or []:
            if int(getattr(item, "magic", 0)) != self._magic:
                continue
            units = self.spec.lots_to_units(float(item.volume))
            entry = float(item.price_open)
            stop = float(item.sl) or None
            positions.append(
                Position(
                    trade_id=str(item.ticket),
                    direction="LONG" if int(item.type) == self._mt5.POSITION_TYPE_BUY else "SHORT",
                    units=units,
                    entry_price=entry,
                    stop_loss=stop,
                    take_profit=float(item.tp) or None,
                    opened_at=self._to_utc(float(item.time)),
                    unrealized_pl=float(item.profit),
                    initial_risk=abs(entry - stop) if stop else 0.0,
                )
            )
        return positions

    async def get_closed_trades(self, count: int = 50) -> list[dict[str, Any]]:
        """Recently closed gold positions, newest first."""
        await self.connect()
        end = dt.datetime.now(dt.timezone.utc) + self._server_offset + dt.timedelta(days=1)
        start = end - dt.timedelta(days=30)
        deals = await self._call(self._mt5.history_deals_get, start, end)

        by_position: dict[int, list[Any]] = {}
        for deal in deals or []:
            if int(getattr(deal, "magic", 0)) != self._magic:
                continue
            by_position.setdefault(int(deal.position_id), []).append(deal)

        closed: list[dict[str, Any]] = []
        for position_id, position_deals in by_position.items():
            entries = [d for d in position_deals if int(d.entry) == self._mt5.DEAL_ENTRY_IN]
            exits = [d for d in position_deals if int(d.entry) != self._mt5.DEAL_ENTRY_IN]
            if not entries or not exits:
                continue  # still open
            realized = sum(
                float(d.profit) + float(getattr(d, "swap", 0.0)) + float(getattr(d, "commission", 0.0))
                for d in position_deals
            )
            last_exit = max(exits, key=lambda d: d.time)
            closed.append(
                {
                    "trade_id": str(position_id),
                    "direction": "LONG" if int(entries[0].type) == self._mt5.DEAL_TYPE_BUY else "SHORT",
                    "units": self.spec.lots_to_units(float(entries[0].volume)),
                    "entry_price": float(entries[0].price),
                    "exit_price": float(last_exit.price),
                    "realized_pl": realized,
                    "opened_at": self._to_utc(float(entries[0].time)).isoformat(),
                    "closed_at": self._to_utc(float(last_exit.time)).isoformat(),
                }
            )
        closed.sort(key=lambda row: row["closed_at"], reverse=True)
        return closed[:count]

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
        """A market order with the stop and target attached, sized in lots."""
        await self.connect()

        volume = self.spec.units_to_lots(self.spec.round_units(abs(units)))
        if volume <= 0:
            return OrderResult(accepted=False, reason="Position size rounded to zero lots")

        info = await self._call(self._mt5.symbol_info, self._symbol)
        tick = await self._call(self._mt5.symbol_info_tick, self._symbol)
        if info is None or tick is None:
            raise self._fail("symbol_info/tick before order")

        is_long = direction == "LONG"
        price = float(tick.ask if is_long else tick.bid)

        stop = self.spec.round_price(stop_loss)
        target = self.spec.round_price(take_profit)

        # The server rejects stops placed too close to the market; say so
        # clearly instead of letting it come back as an opaque retcode.
        minimum = self.spec.min_stop_distance
        if minimum > 0:
            if abs(price - stop) < minimum or abs(target - price) < minimum:
                return OrderResult(
                    accepted=False,
                    reason=(
                        f"Stop or target is inside the broker's minimum distance of "
                        f"${minimum:.2f} from {price:.2f}"
                    ),
                )

        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": self._symbol,
            "volume": volume,
            "type": self._mt5.ORDER_TYPE_BUY if is_long else self._mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": stop,
            "tp": target,
            "deviation": settings.MT5_SLIPPAGE_POINTS,
            "magic": self._magic,
            "comment": (reason or client_id)[:MAX_COMMENT],
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._filling_mode(info),
        }

        result = await self._call(self._mt5.order_send, request)
        if result is None:
            raise self._fail("order_send")
        if int(result.retcode) != self._mt5.TRADE_RETCODE_DONE:
            return OrderResult(
                accepted=False,
                reason=f"Rejected ({result.retcode}): {getattr(result, 'comment', '')}",
            )

        ticket = await self._position_id_for_deal(int(result.deal))
        return OrderResult(
            accepted=True,
            trade_id=str(ticket),
            fill_price=float(result.price),
            units=self.spec.lots_to_units(float(result.volume)),
            reason="filled",
        )

    async def _position_id_for_deal(self, deal_ticket: int) -> int:
        """
        The position a fill opened. Reading it from the deal is reliable on both
        netting and hedging accounts, where the order ticket is not.
        """
        deals = await self._call(self._mt5.history_deals_get, ticket=deal_ticket)
        if deals:
            return int(deals[0].position_id)
        return deal_ticket

    async def modify_stop(self, trade_id: str, stop_loss: float) -> bool:
        await self.connect()
        position = await self._position(trade_id)
        if position is None:
            return False
        request = {
            "action": self._mt5.TRADE_ACTION_SLTP,
            "symbol": self._symbol,
            "position": int(trade_id),
            "sl": self.spec.round_price(stop_loss),
            "tp": float(position.tp),
        }
        result = await self._call(self._mt5.order_send, request)
        if result is None or int(result.retcode) != self._mt5.TRADE_RETCODE_DONE:
            code = getattr(result, "retcode", "no response")
            logger.warning("MT5 stop modification refused for %s: %s", trade_id, code)
            return False
        return True

    async def close_position(self, trade_id: str, reason: str = "") -> OrderResult:
        """Close by sending the opposite deal against the position ticket."""
        await self.connect()
        position = await self._position(trade_id)
        if position is None:
            return OrderResult(accepted=False, reason="No such open MT5 position")

        info = await self._call(self._mt5.symbol_info, self._symbol)
        tick = await self._call(self._mt5.symbol_info_tick, self._symbol)
        if info is None or tick is None:
            raise self._fail("symbol_info/tick before close")

        was_long = int(position.type) == self._mt5.POSITION_TYPE_BUY
        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": self._symbol,
            "volume": float(position.volume),
            "type": self._mt5.ORDER_TYPE_SELL if was_long else self._mt5.ORDER_TYPE_BUY,
            "position": int(trade_id),
            "price": float(tick.bid if was_long else tick.ask),
            "deviation": settings.MT5_SLIPPAGE_POINTS,
            "magic": self._magic,
            "comment": (reason or "close")[:MAX_COMMENT],
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._filling_mode(info),
        }

        result = await self._call(self._mt5.order_send, request)
        if result is None or int(result.retcode) != self._mt5.TRADE_RETCODE_DONE:
            return OrderResult(
                accepted=False,
                reason=f"Close refused ({getattr(result, 'retcode', 'no response')}): "
                       f"{getattr(result, 'comment', '')}",
            )
        return OrderResult(
            accepted=True,
            trade_id=str(trade_id),
            fill_price=float(result.price),
            units=self.spec.lots_to_units(float(result.volume)),
            reason=reason or "closed",
        )

    async def _position(self, trade_id: str) -> Any | None:
        raw = await self._call(self._mt5.positions_get, ticket=int(trade_id))
        if not raw:
            return None
        item = raw[0]
        if int(getattr(item, "magic", 0)) != self._magic:
            return None  # not ours to touch
        return item
