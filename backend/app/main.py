from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    market_data,
    analysis,
    risk,
    execution,
    journal,
    analytics,
    backtest,
    auto_trade,
    ai_insights,
)
from app.core.scanner.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Jarves Trading Bot API",
    description="Decision-support system for algorithmic trading.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market_data.router, prefix="/market-data", tags=["Market Data"])
app.include_router(analysis.router,    prefix="/analysis",    tags=["Analysis"])
app.include_router(risk.router,        prefix="/risk",        tags=["Risk"])
app.include_router(execution.router,   prefix="/execution",   tags=["Execution"])
app.include_router(journal.router,     prefix="/journal",     tags=["Journal"])
app.include_router(analytics.router,   prefix="/analytics",   tags=["Analytics"])
app.include_router(backtest.router,    prefix="/backtest",    tags=["Backtest"])
app.include_router(auto_trade.router,  prefix="/auto-trade",  tags=["Auto Trade"])
app.include_router(ai_insights.router,  prefix="/ai-insights",  tags=["AI Insights"])


@app.get("/health")
async def health():
    return {"status": "ok"}
