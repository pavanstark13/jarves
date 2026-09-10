"""
Jarves — an automated gold (XAU/USD) trading agent.

One instrument, one strategy, one loop. The API exposes what the agent sees,
what it decided and why, and the controls to start, stop and flatten it.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import agent as agent_routes
from app.api.routes import backtest as backtest_routes
from app.api.routes import market as market_routes
from app.api.routes import trades as trades_routes
from app.config import settings
from app.core.agent import get_agent
from app.core.broker.base import BrokerError
from app.core.broker.paper import PaperBroker
from app.core.scheduler import scheduler_running, start_scheduler, stop_scheduler
from app.database.connection import init_db
from app.instrument import DISPLAY_NAME, SYMBOL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    trading_agent = get_agent()

    # Read the real contract details for gold from the broker, so price
    # rounding and minimum size follow the venue rather than our defaults.
    if trading_agent.market and trading_agent.market.configured:
        try:
            spec = await trading_agent.market.load_instrument_spec()
            trading_agent.risk.spec = spec
            if isinstance(trading_agent.broker, PaperBroker):
                trading_agent.broker.spec = spec
        except BrokerError as exc:
            logger.warning("Could not read the gold contract spec: %s", exc)
    else:
        logger.warning(
            "OANDA credentials are not configured — the agent can start but has "
            "no market data. Set OANDA_API_KEY and OANDA_ACCOUNT_ID."
        )

    # Restore simulated state so a restart does not forget open paper trades.
    if isinstance(trading_agent.broker, PaperBroker):
        from app.services.store import store

        trading_agent.broker.restore(
            realized_pl=await store.realized_pl(mode="paper"),
            positions=await store.open_positions(mode="paper"),
        )

    start_scheduler()
    if settings.AGENT_AUTOSTART:
        await trading_agent.start()

    logger.info(
        "%s ready — %s in %s mode", settings.APP_NAME, SYMBOL,
        "LIVE" if settings.is_live else "paper",
    )
    yield
    stop_scheduler()
    await trading_agent.stop("API shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    description=f"Rule-based automated trading agent for {DISPLAY_NAME} ({SYMBOL}).",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_routes.router, prefix="/agent", tags=["Agent"])
app.include_router(market_routes.router, prefix="/market", tags=["Market"])
app.include_router(trades_routes.router, prefix="/trades", tags=["Trades"])
app.include_router(backtest_routes.router, prefix="/backtest", tags=["Backtest"])


@app.get("/health", tags=["Meta"])
async def health():
    trading_agent = get_agent()
    return {
        "status": "ok",
        "symbol": SYMBOL,
        "mode": "live" if settings.is_live else "paper",
        "agent_enabled": trading_agent.enabled,
        "scheduler_running": scheduler_running(),
        "broker_configured": bool(trading_agent.market and trading_agent.market.configured),
    }
