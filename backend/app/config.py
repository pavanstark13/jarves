"""
Central configuration for the XAU/USD (gold) trading agent.

Every value here is a hard operating parameter — thresholds the agent measures
current market data against. There is no model, no forecast and no sentiment
input anywhere in this system: a trade is either allowed by these numbers or
it is not taken.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    APP_NAME: str = "Jarves Gold Agent"
    ENVIRONMENT: str = "development"

    # ── Storage ───────────────────────────────────────────────────────────────
    # SQLite by default so the agent runs standalone with no extra services.
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/jarves.db"

    # ── Broker selection ──────────────────────────────────────────────────────
    # "oanda" — OANDA v20 REST, works anywhere.
    # "mt5"   — MetaTrader 5 terminal (MultiBank and other MT5 brokers).
    #           The backend must run on Windows, on the same machine as the
    #           terminal: MetaQuotes publishes no Linux build of its package.
    BROKER: str = "oanda"

    # ── Broker: OANDA v20 ─────────────────────────────────────────────────────
    OANDA_API_KEY: str = ""
    OANDA_ACCOUNT_ID: str = ""
    # "practice" (fxpractice, demo money) or "live" (real money).
    OANDA_ENVIRONMENT: str = "practice"

    # ── Broker: MetaTrader 5 ──────────────────────────────────────────────────
    # Credentials as shown in the terminal. For MultiBank the server name looks
    # like "MultiBankGroup-Live" or "MEXAtlantic-Demo" — copy it exactly.
    MT5_LOGIN: int = 0
    MT5_PASSWORD: str = ""
    MT5_SERVER: str = ""
    # Path to terminal64.exe. Leave empty to attach to a terminal already running.
    MT5_TERMINAL_PATH: str = ""
    # Pin the broker's gold symbol (e.g. "XAUUSD.m"). Empty discovers it.
    MT5_SYMBOL: str = ""
    # Tags this agent's orders so manual trades in the same account are ignored.
    MT5_MAGIC: int = 8_829_001
    # Maximum slippage tolerated on a market order, in points.
    MT5_SLIPPAGE_POINTS: int = 20
    # Hours the broker's clock runs ahead of UTC (MultiBank is typically +2/+3).
    # Leave unset to measure it from a live tick; pin it if the detection warns.
    MT5_SERVER_UTC_OFFSET_HOURS: float | None = None

    # ── Agent execution mode ──────────────────────────────────────────────────
    # "paper" — the full pipeline runs and decisions are recorded, but no order
    #           is ever sent to the broker.
    # "live"  — approved signals are sent to OANDA.
    # Live execution additionally requires EXECUTION_CONFIRMED=true, so a stray
    # environment variable cannot by itself start sending real orders.
    AGENT_MODE: str = "paper"
    EXECUTION_CONFIRMED: bool = False
    # Simulated starting balance for paper mode.
    PAPER_STARTING_BALANCE: float = 10_000.0
    # Start the trading loop as soon as the API boots.
    AGENT_AUTOSTART: bool = False
    # How often the agent re-evaluates the market and manages open trades.
    SCAN_INTERVAL_SECONDS: int = 60

    # ── Risk limits ───────────────────────────────────────────────────────────
    RISK_PER_TRADE_PCT: float = 0.5        # % of NAV risked between entry and stop
    MAX_DAILY_LOSS_PCT: float = 2.0        # halts trading for the UTC day
    MAX_DRAWDOWN_PCT: float = 10.0         # halts the agent until manually reset
    MAX_TRADES_PER_DAY: int = 3
    MAX_OPEN_POSITIONS: int = 1
    MAX_CONSECUTIVE_LOSSES: int = 2
    COOLDOWN_MINUTES: int = 60             # pause after hitting consecutive losses
    MIN_ACCOUNT_BALANCE: float = 100.0     # refuse to trade below this NAV
    MAX_LEVERAGE: float = 5.0              # cap position notional at 5x NAV

    # ── Trade construction ────────────────────────────────────────────────────
    MIN_RISK_REWARD: float = 2.0           # reward:risk of the take-profit
    STOP_ATR_MULTIPLE: float = 1.0         # ATR padding beyond the swing point
    MIN_STOP_USD: float = 2.50             # floor on stop distance, $/oz
    MAX_STOP_USD: float = 12.00            # ceiling on stop distance, $/oz
    BREAKEVEN_AT_R: float = 1.0            # move stop to entry at +1R
    TRAIL_START_R: float = 1.5             # begin ATR trailing at +1.5R
    TRAIL_ATR_MULTIPLE: float = 1.5
    MAX_TRADE_HOURS: float = 12.0          # time stop for a trade going nowhere

    # ── Market condition gates ────────────────────────────────────────────────
    MAX_SPREAD_USD: float = 0.60           # absolute spread cap, $/oz
    MAX_SPREAD_ATR_RATIO: float = 0.25     # spread must stay small vs volatility
    MIN_ATR_USD: float = 1.00              # below this the market is too dead
    MAX_ATR_USD: float = 20.00             # above this it is too disorderly
    MAX_EXTENSION_ATR: float = 2.5         # skip entries already extended from EMA

    # Trading windows, UTC hours (London + New York). Gold's liquidity outside
    # these hours is thin and the spread gate rejects most of it anyway.
    SESSION_WINDOWS: str = "07:00-11:00,12:30-17:00"
    # OANDA's daily rollover — spreads blow out, never hold or open through it.
    ROLLOVER_WINDOW: str = "20:45-22:15"
    TRADE_ON_FRIDAY_CLOSE: bool = False    # avoid the last hours of the week

    # ── Economic calendar blackout ────────────────────────────────────────────
    # Gold is priced in USD, so USD releases are what move it.
    NEWS_BLACKOUT_BEFORE_MIN: int = 30
    NEWS_BLACKOUT_AFTER_MIN: int = 15
    FLATTEN_BEFORE_NEWS: bool = True       # close open trades ahead of a release
    # Optional free calendar feed (https://fcsapi.com). Without a key the agent
    # falls back to the fixed-schedule blackout table in core/market/calendar.py.
    FCS_API_KEY: str = ""

    # ── Derived helpers ───────────────────────────────────────────────────────
    @property
    def is_live(self) -> bool:
        """True only when both the mode and the explicit confirmation are set."""
        return self.AGENT_MODE.lower() == "live" and self.EXECUTION_CONFIRMED

    @property
    def broker_configured(self) -> bool:
        return bool(self.OANDA_API_KEY and self.OANDA_ACCOUNT_ID)


settings = Settings()
