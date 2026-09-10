"""The HTTP surface: what the console reads and the controls it drives."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.agent import TradingAgent, set_agent
from app.core.broker.paper import PaperBroker
from app.main import app

from factories import BASE_TIME
from fakes import FakeCalendar, FakeMarket


@pytest.fixture
def client():
    """The API wired to a scripted market instead of a real broker."""
    market = FakeMarket(now=BASE_TIME)
    clock = lambda: BASE_TIME  # noqa: E731
    set_agent(
        TradingAgent(
            broker=PaperBroker(market, starting_balance=10_000.0, clock=clock),
            market=market,
            calendar=FakeCalendar(),
            clock=clock,
        )
    )
    with TestClient(app) as test_client:
        yield test_client
    set_agent(None)


def test_health_reports_the_mode_and_never_claims_live_by_accident(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["symbol"] == "XAUUSD"
    assert body["mode"] == "paper"


def test_status_describes_the_agent(client):
    body = client.get("/agent/status").json()
    assert body["symbol"] == "XAUUSD"
    assert body["enabled"] is False
    assert "session" in body


def test_config_exposes_the_limits_in_force(client):
    body = client.get("/agent/config").json()
    assert body["risk"]["max_daily_loss_pct"] > 0
    assert body["trade"]["min_risk_reward"] >= 1
    assert "session_windows_utc" in body["market"]


def test_start_then_cycle_opens_a_trade_and_stop_ends_it(client):
    assert client.post("/agent/start").json()["enabled"] is True

    report = client.post("/agent/cycle?force=false").json()
    assert report["decision"]["action"] == "LONG"
    assert any("Opened" in action for action in report["actions"])

    trades = client.get("/trades").json()
    assert len(trades) == 1
    assert trades[0]["status"] == "OPEN"

    assert client.get("/trades/open").json()[0]["direction"] == "LONG"
    assert client.post("/agent/stop").json()["enabled"] is False


def test_flatten_closes_the_open_position(client):
    client.post("/agent/start")
    client.post("/agent/cycle?force=false")
    result = client.post("/agent/flatten", json={"reason": "test"}).json()
    assert result["closed"] == 1
    assert client.get("/trades/open").json() == []


def test_the_decision_log_records_evaluations_that_did_not_trade(client):
    client.post("/agent/cycle?force=true")
    decisions = client.get("/agent/decisions").json()
    assert len(decisions) >= 1
    assert decisions[0]["detail"]["gates"]


def test_performance_is_reported_even_with_no_trades(client):
    body = client.get("/trades/performance").json()
    assert body["trades"] == 0
    assert body["win_rate"] == 0.0


def test_market_endpoints_serve_live_data(client):
    price = client.get("/market/price").json()
    assert price["ask"] > price["bid"]

    candles = client.get("/market/candles?timeframe=M15&count=50").json()
    assert candles["timeframe"] == "M15"
    assert len(candles["candles"]) == 50

    assert "can_open" in client.get("/market/session").json()


def test_starting_a_halted_agent_is_refused(client):
    client.post("/agent/start")
    client.post("/agent/cycle?force=false")
    # Halt through the store, the same way a drawdown breach would.
    import asyncio

    from app.services.store import store

    asyncio.run(store.set_state("halt", {"active": True, "reason": "drawdown limit"}))
    response = client.post("/agent/start")
    assert response.status_code == 409
    assert "drawdown" in response.json()["detail"]

    assert client.post("/agent/reset-halt").json()["halted"] is False
    assert client.post("/agent/start").status_code == 200


def test_an_unknown_backtest_run_is_a_404(client):
    assert client.get("/backtest/runs/nope").status_code == 404
