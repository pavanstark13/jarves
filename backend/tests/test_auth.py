"""
API access control.

The endpoints here can start trading and close positions, so who may call them
matters as much as what they do.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.auth import check_startup_safety
from app.core.agent import TradingAgent, set_agent
from app.core.broker.paper import PaperBroker
from app.main import app

from factories import BASE_TIME
from fakes import FakeCalendar, FakeMarket

TOKEN = "a-long-random-token-value"


@pytest.fixture
def client():
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


@pytest.fixture
def secured(monkeypatch):
    monkeypatch.setattr("app.api.auth.settings.API_TOKEN", TOKEN)


# ── with no token configured ─────────────────────────────────────────────────

def test_an_unconfigured_api_stays_open_for_local_use(client):
    assert client.get("/agent/status").status_code == 200


def test_health_reports_whether_a_token_is_required(client):
    assert client.get("/health").json()["auth_required"] is False


# ── with a token configured ──────────────────────────────────────────────────

def test_reading_the_agent_requires_the_token(client, secured):
    assert client.get("/agent/status").status_code == 401


def test_the_controls_require_the_token(client, secured):
    for method, path in (
        ("post", "/agent/start"),
        ("post", "/agent/stop"),
        ("post", "/agent/cycle"),
        ("post", "/agent/reset-halt"),
    ):
        response = getattr(client, method)(path)
        assert response.status_code == 401, f"{path} was reachable without a token"


def test_flatten_cannot_be_called_anonymously(client, secured):
    response = client.post("/agent/flatten", json={"reason": "hostile"})
    assert response.status_code == 401


def test_a_bearer_token_is_accepted(client, secured):
    response = client.get("/agent/status", headers={"Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 200


def test_the_header_form_is_accepted_too(client, secured):
    response = client.get("/agent/status", headers={"X-API-Token": TOKEN})
    assert response.status_code == 200


def test_a_wrong_token_is_rejected(client, secured):
    response = client.get("/agent/status", headers={"Authorization": "Bearer not-the-token"})
    assert response.status_code == 401


def test_a_token_prefix_is_not_enough(client, secured):
    response = client.get("/agent/status", headers={"Authorization": f"Bearer {TOKEN[:10]}"})
    assert response.status_code == 401


def test_market_trades_and_backtest_are_protected_as_well(client, secured):
    for path in ("/market/price", "/trades", "/trades/performance", "/backtest/runs"):
        assert client.get(path).status_code == 401, f"{path} was reachable without a token"
        assert client.get(path, headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 200


def test_health_stays_open_so_uptime_checks_work(client, secured):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["auth_required"] is True


# ── the startup guard ────────────────────────────────────────────────────────

def test_live_trading_without_a_token_refuses_to_start(monkeypatch):
    monkeypatch.setattr("app.api.auth.settings.API_TOKEN", "")
    monkeypatch.setattr("app.api.auth.settings.AGENT_MODE", "live")
    monkeypatch.setattr("app.api.auth.settings.EXECUTION_CONFIRMED", True)

    with pytest.raises(RuntimeError, match="AGENT_MODE=live with no API_TOKEN"):
        check_startup_safety()


def test_live_trading_with_a_token_is_allowed(monkeypatch):
    monkeypatch.setattr("app.api.auth.settings.API_TOKEN", TOKEN)
    monkeypatch.setattr("app.api.auth.settings.AGENT_MODE", "live")
    monkeypatch.setattr("app.api.auth.settings.EXECUTION_CONFIRMED", True)
    check_startup_safety()   # does not raise


def test_paper_mode_without_a_token_only_warns(monkeypatch, caplog):
    monkeypatch.setattr("app.api.auth.settings.API_TOKEN", "")
    monkeypatch.setattr("app.api.auth.settings.AGENT_MODE", "paper")
    check_startup_safety()
    assert "API_TOKEN is not set" in caplog.text
