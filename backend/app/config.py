from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://jarves:jarves@localhost:5432/jarves"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Google Gemini (for AI explanations — free tier at aistudio.google.com)
    GOOGLE_API_KEY: str = ""

    # Market data — Twelve Data (https://twelvedata.com, free tier)
    TWELVE_DATA_API_KEY: str = ""

    # News — NewsAPI (https://newsapi.org, free tier)
    NEWS_API_KEY: str = ""

    # Economic calendar — FCS API (https://fcsapi.com, free tier)
    FCS_API_KEY: str = ""

    # Broker (legacy)
    BROKER_API_KEY: str = ""
    BROKER_API_SECRET: str = ""

    # OANDA Practice Account (https://www.oanda.com)
    OANDA_API_KEY: str = ""
    OANDA_ACCOUNT_ID: str = ""
    OANDA_PRACTICE: str = "true"

    # App
    ENVIRONMENT: str = "development"

    # Risk parameters
    RISK_MAX_DAILY_LOSS_PCT: float = 2.0
    RISK_MAX_WEEKLY_LOSS_PCT: float = 5.0
    RISK_MAX_DRAWDOWN_PCT: float = 10.0
    RISK_DEFAULT_RISK_PCT: float = 0.5

    # Strategy thresholds
    MIN_SETUP_QUALITY: float = 70.0
    MIN_RISK_REWARD: float = 1.5


settings = Settings()
