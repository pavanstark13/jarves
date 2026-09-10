"""
The MetaTrader 5 adapter, driven against a fake terminal.

These cover the conversions that silently break real MT5 integrations: lots
versus ounces, server time versus UTC, filling modes, stop distances and the
magic-number isolation that keeps the agent away from manual trades.

They do not prove the adapter works against a live MultiBank server — only a
real terminal can show that.
"""

from __future__ import annotations

import datetime as dt

import pytest

from app.core.broker.base import BrokerError
from app.core.broker.mt5 import Mt5Broker

from fake_mt5 import SYMBOL_FILLING_FOK, SYMBOL_FILLING_IOC, FakeTerminal

def utc_now() -> dt.datetime:
    """
    The fake terminal runs at real wall-clock time with its *server* clock
    shifted, which is exactly the situation the adapter has to unpick. Pinning
    a fake "now" here would instead look like a stale weekend tick.
    """
    return dt.datetime.now(dt.timezone.utc)


@pytest.fixture
def terminal(monkeypatch) -> FakeTerminal:
    return FakeTerminal().install(monkeypatch)


def broker(**kwargs) -> Mt5Broker:
    options = dict(login=123456, password="secret", server="MultiBankGroup-Live", magic=8_829_001)
    options.update(kwargs)
    return Mt5Broker(**options)


# ── connection and symbol discovery ──────────────────────────────────────────

async def test_credentials_are_passed_to_the_terminal(terminal):
    client = broker()
    await client.connect()
    assert terminal.init_kwargs["login"] == 123456
    assert terminal.init_kwargs["server"] == "MultiBankGroup-Live"


async def test_missing_credentials_say_where_to_find_them(terminal):
    with pytest.raises(BrokerError, match="MT5_LOGIN"):
        await broker(login=0, password="", server="").connect()


async def test_plain_gold_symbol_is_found(terminal):
    client = broker()
    await client.connect()
    assert client.symbol == "XAUUSD"
    assert "XAUUSD" in terminal.selected  # and put in Market Watch


async def test_a_broker_suffixed_symbol_is_discovered(monkeypatch):
    FakeTerminal(symbols=["EURUSD", "XAUUSD.m"]).install(monkeypatch)
    client = broker()
    await client.connect()
    assert client.symbol == "XAUUSD.m"


async def test_a_pinned_symbol_is_used_as_given(monkeypatch):
    FakeTerminal(symbols=["XAUUSD", "GOLD"]).install(monkeypatch)
    client = broker(symbol="GOLD")
    await client.connect()
    assert client.symbol == "GOLD"


async def test_a_pinned_symbol_the_account_lacks_is_an_error(monkeypatch):
    FakeTerminal(symbols=["XAUUSD"]).install(monkeypatch)
    with pytest.raises(BrokerError, match="Market Watch"):
        await broker(symbol="XAUUSD.raw").connect()


async def test_an_account_without_gold_is_an_error(monkeypatch):
    FakeTerminal(symbols=["EURUSD", "USDJPY"]).install(monkeypatch)
    with pytest.raises(BrokerError, match="No gold symbol"):
        await broker().connect()


# ── the contract ─────────────────────────────────────────────────────────────

async def test_the_contract_is_read_from_the_broker_not_assumed(terminal):
    spec = await broker().load_instrument_spec()
    assert spec.contract_size == 100.0        # 1 lot = 100 oz
    assert spec.units_step == pytest.approx(1.0)   # 0.01 lots = 1 oz
    assert spec.min_trade_units == pytest.approx(1.0)
    assert spec.price_precision == 2          # MT5 gold quotes 2 decimals
    assert spec.format_price(2401.2367) == "2401.24"


async def test_a_coarser_volume_step_widens_the_size_granularity(monkeypatch):
    FakeTerminal(volume_step=0.1, volume_min=0.1).install(monkeypatch)
    spec = await broker().load_instrument_spec()
    assert spec.units_step == pytest.approx(10.0)
    assert spec.round_units(37.0) == 30.0


async def test_the_minimum_stop_distance_is_taken_from_the_server(monkeypatch):
    FakeTerminal(stops_level=50, digits=2).install(monkeypatch)
    spec = await broker().load_instrument_spec()
    assert spec.min_stop_distance == pytest.approx(0.5)   # 50 points x 0.01


# ── server time ──────────────────────────────────────────────────────────────

async def test_server_time_is_converted_back_to_utc(terminal):
    """The fake server runs UTC+3, as MultiBank's typically does."""
    client = broker()
    await client.connect()
    assert client._server_offset == dt.timedelta(hours=3)

    quote = await client.get_quote()
    # The raw tick is stamped three hours ahead; the quote must read as now.
    assert abs((quote.time - utc_now()).total_seconds()) < 60


async def test_candle_times_are_utc_so_session_gates_are_not_shifted(terminal):
    client = broker()
    await client.connect()
    candles = await client.get_candles("M15", 10)
    now = utc_now()
    assert candles[-1].time <= now
    assert abs((candles[-1].time - now).total_seconds()) < 16 * 60
    # And they arrive oldest first.
    assert candles[0].time < candles[-1].time


async def test_a_pinned_offset_overrides_detection(monkeypatch):
    FakeTerminal(server_offset_hours=9.0).install(monkeypatch)   # a wrong clock
    monkeypatch.setattr("app.core.broker.mt5.settings.MT5_SERVER_UTC_OFFSET_HOURS", 3.0)
    client = broker()
    await client.connect()
    # The pinned value wins over anything measured from the tick.
    assert client._server_offset == dt.timedelta(hours=3)


async def test_a_stale_weekend_tick_does_not_produce_a_wild_offset(monkeypatch):
    terminal = FakeTerminal(server_offset_hours=3.0).install(monkeypatch)
    terminal.tick_age = dt.timedelta(days=2)   # the market has been shut since Friday
    client = broker()
    await client.connect()
    assert client._server_offset == dt.timedelta(0)   # refuses the bad measurement


# ── account and positions ────────────────────────────────────────────────────

async def test_account_uses_equity_as_nav(terminal):
    account = await broker().get_account()
    assert account.nav == 10_050.0        # equity, not balance
    assert account.balance == 10_000.0
    assert account.currency == "USD"


async def test_positions_are_reported_in_ounces_not_lots(terminal):
    client = broker()
    await client.load_instrument_spec()
    await client.place_order("LONG", 50, 2395.0, 2410.0, "cid", "test")

    positions = await client.get_open_positions()
    assert len(positions) == 1
    assert positions[0].units == pytest.approx(50.0)      # ounces
    assert terminal.positions[0].volume == pytest.approx(0.5)  # lots on the wire
    assert positions[0].direction == "LONG"


async def test_manual_trades_in_the_same_account_are_ignored(terminal):
    client = broker()
    await client.load_instrument_spec()
    await client.place_order("LONG", 50, 2395.0, 2410.0, "cid", "test")
    # Someone opens a gold trade by hand in the terminal.
    terminal.positions[0].magic = 0

    assert await client.get_open_positions() == []


# ── orders ───────────────────────────────────────────────────────────────────

async def test_ounces_are_converted_to_lots_and_rounded_down(terminal):
    client = broker()
    await client.load_instrument_spec()
    result = await client.place_order("LONG", 37.6, 2395.0, 2410.0, "cid", "test")

    assert result.accepted
    assert terminal.sent[0]["volume"] == pytest.approx(0.37)   # never 0.38
    assert result.units == pytest.approx(37.0)


async def test_a_long_buys_at_the_ask_with_stop_and_target_attached(terminal):
    client = broker()
    await client.load_instrument_spec()
    await client.place_order("LONG", 50, 2395.0, 2410.0, "cid", "test")

    request = terminal.sent[0]
    assert request["type"] == 0            # ORDER_TYPE_BUY
    assert request["price"] == 2400.30     # the ask
    assert request["sl"] == 2395.0
    assert request["tp"] == 2410.0
    assert request["magic"] == 8_829_001


async def test_a_short_sells_at_the_bid(terminal):
    client = broker()
    await client.load_instrument_spec()
    await client.place_order("SHORT", 50, 2405.0, 2390.0, "cid", "test")
    assert terminal.sent[0]["price"] == 2400.00


async def test_the_filling_mode_matches_what_the_symbol_accepts(monkeypatch):
    ioc = FakeTerminal(filling_mask=SYMBOL_FILLING_IOC).install(monkeypatch)
    client = broker()
    await client.load_instrument_spec()
    await client.place_order("LONG", 50, 2395.0, 2410.0, "cid", "test")
    assert ioc.sent[0]["type_filling"] == 1        # ORDER_FILLING_IOC

    fok = FakeTerminal(filling_mask=SYMBOL_FILLING_FOK).install(monkeypatch)
    client = broker()
    await client.load_instrument_spec()
    await client.place_order("LONG", 50, 2395.0, 2410.0, "cid", "test")
    assert fok.sent[0]["type_filling"] == 0        # ORDER_FILLING_FOK


async def test_a_stop_inside_the_brokers_minimum_distance_is_refused(monkeypatch):
    FakeTerminal(stops_level=500, digits=2).install(monkeypatch)  # $5 minimum
    client = broker()
    await client.load_instrument_spec()
    result = await client.place_order("LONG", 50, 2399.0, 2402.0, "cid", "test")

    assert not result.accepted
    assert "minimum distance" in result.reason


async def test_a_size_that_rounds_below_the_minimum_lot_is_refused(terminal):
    client = broker()
    await client.load_instrument_spec()
    result = await client.place_order("LONG", 0.4, 2395.0, 2410.0, "cid", "test")
    assert not result.accepted
    assert "zero lots" in result.reason


async def test_the_comment_is_truncated_to_what_mt5_accepts(terminal):
    client = broker()
    await client.load_instrument_spec()
    await client.place_order("LONG", 50, 2395.0, 2410.0, "cid", "x" * 200)
    assert len(terminal.sent[0]["comment"]) <= 31


async def test_the_trade_id_is_the_position_not_the_deal(terminal):
    client = broker()
    await client.load_instrument_spec()
    result = await client.place_order("LONG", 50, 2395.0, 2410.0, "cid", "test")
    assert result.trade_id == str(terminal.positions[0].ticket)


# ── managing and closing ─────────────────────────────────────────────────────

async def test_a_stop_can_be_moved_on_our_own_position(terminal):
    client = broker()
    await client.load_instrument_spec()
    result = await client.place_order("LONG", 50, 2395.0, 2410.0, "cid", "test")

    assert await client.modify_stop(result.trade_id, 2400.30)
    assert terminal.positions[0].sl == 2400.30


async def test_a_stop_on_someone_elses_position_is_refused(terminal):
    client = broker()
    await client.load_instrument_spec()
    result = await client.place_order("LONG", 50, 2395.0, 2410.0, "cid", "test")
    terminal.positions[0].magic = 0    # now a manual trade

    assert not await client.modify_stop(result.trade_id, 2400.30)


async def test_closing_sends_the_opposite_side_against_the_ticket(terminal):
    client = broker()
    await client.load_instrument_spec()
    result = await client.place_order("LONG", 50, 2395.0, 2410.0, "cid", "test")

    closed = await client.close_position(result.trade_id, "manual")
    assert closed.accepted
    request = terminal.sent[-1]
    assert request["type"] == 1                       # ORDER_TYPE_SELL
    assert request["position"] == int(result.trade_id)
    assert request["price"] == 2400.00                # sells at the bid
    assert await client.get_open_positions() == []


async def test_closed_trades_report_profit_net_of_swap_and_commission(terminal):
    client = broker()
    await client.load_instrument_spec()
    terminal.add_closed_position(magic=8_829_001, profit=50.0, commission=-2.0, swap=-1.0)

    closed = await client.get_closed_trades()
    assert len(closed) == 1
    assert closed[0]["realized_pl"] == pytest.approx(47.0)   # 50 - 2 - 1
    assert closed[0]["units"] == pytest.approx(5.0)          # 0.05 lots


async def test_closed_trades_from_manual_trading_are_not_counted(terminal):
    client = broker()
    await client.load_instrument_spec()
    terminal.add_closed_position(magic=0, profit=999.0)
    assert await client.get_closed_trades() == []


# ── the agent driving MT5 ────────────────────────────────────────────────────

async def test_the_agent_runs_a_full_cycle_through_the_mt5_adapter(terminal):
    """
    Proof that the adapter satisfies the interface the agent actually uses:
    paper mode fills against real MT5 quotes and candles, so this exercises
    the whole path from terminal to decision.
    """
    from app.core.agent import TradingAgent
    from app.core.broker.paper import PaperBroker

    from fakes import FakeCalendar

    market = broker()
    await market.load_instrument_spec()
    agent = TradingAgent(
        broker=PaperBroker(market, starting_balance=10_000.0, spec=market.spec),
        market=market,
        calendar=FakeCalendar(),
    )
    await agent.start()
    report = await agent.cycle()

    assert report.error == ""
    assert report.decision is not None
    assert report.decision.gates          # the gates were measured against MT5 data
    status = await agent.status()
    assert status["venue"] == "paper"
    assert status["account"]["nav"] == 10_000.0


async def test_live_mode_sends_orders_straight_to_the_terminal(terminal):
    """With BROKER=mt5 and live execution, the agent's broker *is* the terminal."""
    from app.core.agent import build_broker
    from app.core.broker.mt5 import Mt5Broker

    import app.core.agent as agent_module

    class LiveSettings:
        def __getattr__(self, name):
            from app.config import settings as real
            return getattr(real, name)
        is_live = True
        BROKER = "mt5"

    original = agent_module.settings
    agent_module.settings = LiveSettings()
    try:
        execution, market = build_broker()
        assert isinstance(execution, Mt5Broker)
        assert execution is market       # orders and data share one connection
    finally:
        agent_module.settings = original
