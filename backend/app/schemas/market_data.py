import datetime
from typing import Optional

from pydantic import BaseModel


class OHLCVBar(BaseModel):
    timestamp: datetime.datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class PriceBarCreate(OHLCVBar):
    symbol: str
    timeframe: str


class PriceBarRead(PriceBarCreate):
    id: int

    model_config = {"from_attributes": True}


class NewsItemCreate(BaseModel):
    title: str
    source: Optional[str] = None
    url: Optional[str] = None
    content: Optional[str] = None
    sentiment: Optional[str] = None
    symbols: Optional[str] = None
    published_at: datetime.datetime


class NewsItemRead(NewsItemCreate):
    id: int
    fetched_at: datetime.datetime

    model_config = {"from_attributes": True}


class EconomicEventCreate(BaseModel):
    name: str
    currency: str
    impact: str  # low/medium/high
    scheduled_at: datetime.datetime
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    is_released: bool = False


class EconomicEventRead(EconomicEventCreate):
    id: int

    model_config = {"from_attributes": True}
