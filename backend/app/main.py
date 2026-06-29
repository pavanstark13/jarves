from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    market_data,
    analysis,
    risk,
    execution,
    journal,
    analytics,
)

app = FastAPI(
    title="Jarves Trading Bot API",
    description="Decision-support system for algorithmic trading with strict Analysis/Risk/Execution separation.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market_data.router, prefix="/market-data", tags=["Market Data"])
app.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])
app.include_router(risk.router, prefix="/risk", tags=["Risk"])
app.include_router(execution.router, prefix="/execution", tags=["Execution"])
app.include_router(journal.router, prefix="/journal", tags=["Journal"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])


@app.get("/health")
async def health():
    return {"status": "ok"}
