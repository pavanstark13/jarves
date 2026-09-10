# Jarves — Gold Trading Agent

An automated trading agent for one instrument: **spot gold, XAU/USD**.

It trades on rules applied to current market data. There is no forecasting
model, no sentiment scoring and no language model anywhere in the decision
path. Every cycle it measures the same set of conditions and either finds all
of them satisfied — in which case it takes the trade — or it stands aside and
records which measurement stopped it.

```
backend/   FastAPI service: the agent loop, strategy, risk control, brokers, storage
frontend/  Next.js console: what the agent sees, what it decided, and the controls
```

Two brokers are supported. Set `BROKER` to pick one:

| `BROKER` | Venue | Runs on |
| --- | --- | --- |
| `oanda` | OANDA v20 REST | anywhere, including Docker on Linux |
| `mt5` | MetaTrader 5 terminal — MultiBank and other MT5 brokers | **Windows only**, beside the terminal |

## How it decides

A trade needs every one of these to be true. They are checked in order on each
cycle, and the failing measurement is written to the decision log.

| Gate | What is measured |
| --- | --- |
| `data` | Enough completed candles on M15, H1, H4 and D1 |
| `market_open` | The broker is quoting a tradeable two-sided market |
| `session` | Inside the London or New York windows, outside rollover and the weekend |
| `news` | No high-impact US release inside the blackout window |
| `regime` | H4 EMA50/EMA200 stacked and sloping — this sets the only direction traded |
| `daily_alignment` | The D1 EMA20 slope does not oppose that direction |
| `bias` | H1 EMA20/EMA50 stacked the same way, price on the correct side of the EMA50 |
| `structure` | M15 swings still higher-high/higher-low (or the mirror), or a confirmed break of structure |
| `pullback` | Price traded back to the M15 EMA20 or into an unfilled imbalance, and RSI reset through 50 |
| `trigger` | The last completed M15 bar closed back through the EMA20 in the trend direction |
| `volatility` | M15 ATR inside a workable band — neither dead nor disorderly |
| `spread` | The live spread is small both absolutely and against ATR |
| `extension` | Price is not stretched far from the EMA20, so entries never chase |
| `stop_distance` | The structural stop produces risk inside the allowed band |

Decisions are made only on **completed** candles. A forming bar can still
change, so it is never fed to the strategy.

**Stop** goes beyond the swing that would invalidate the setup, padded by an
ATR multiple. **Target** is a fixed multiple of that distance (2R by default).
Both are set before entry and attached to the order at the broker, so the
position is never live without protection even if this process dies.

While a trade is open: the stop moves to breakeven at +1R, then trails by an
ATR multiple from +1.5R, and never moves back the other way. A trade that has
not reached 1R within the time limit is closed. Open positions are closed ahead
of a scheduled release.

## How it sizes and when it stops

Position size is arithmetic, not judgement:

```
units = (NAV × risk% ) / (entry − stop)     rounded down, capped by leverage
```

Trading stops when any of these is true — the limits are checked before every
order, and a breach halts the agent rather than failing a single trade:

- the daily loss limit is reached (resets the next UTC day);
- drawdown from the equity peak reaches its limit (**persists across restarts**
  and must be cleared manually);
- the daily trade count is used up;
- consecutive losses trigger a cool-down;
- a position is already open, or NAV is below the floor.

## Paper and live

`paper` is the default. It runs the entire pipeline and fills orders itself
against **real** OANDA quotes: entries pay the live spread, stops and targets
are checked against real M1 bars, and when one bar contains both the stop and
the target the stop is taken. The record it produces is honest rather than
flattering.

Sending real orders requires **both**:

```
AGENT_MODE=live
EXECUTION_CONFIRMED=true
```

so no single stray environment variable can start trading real money. Paper
mode still needs OANDA credentials — it simulates the money, not the market.

## Running it with OANDA

```bash
# 1. Credentials — a free OANDA practice account is enough
cp backend/.env.example backend/.env
#    set BROKER=oanda and fill in OANDA_API_KEY and OANDA_ACCOUNT_ID

# 2. Everything at once
docker compose up --build
```

Or run the two halves directly:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload           # http://localhost:8000/docs

cd ../frontend
npm install
npm run dev                             # http://localhost:3000
```

The agent boots stopped. Press **Start agent** in the console, or set
`AGENT_AUTOSTART=true`.

## Running it with MetaTrader 5 (MultiBank)

MetaQuotes publishes its Python package for **Windows only** — there is no
Linux or macOS build — and it drives a terminal running on the same machine.
So with `BROKER=mt5` the backend has to run on Windows next to MetaTrader 5.
Docker Compose is therefore an OANDA-only path; for MT5, run the backend
directly. Anything with a persistent desktop works, including the Windows VPS
most brokers offer.

```powershell
# On the Windows machine, with MetaTrader 5 installed and logged in:
cd backend
pip install -r requirements.txt -r requirements-mt5.txt
copy .env.example .env
```

Then set in `backend\.env`:

```
BROKER=mt5
MT5_LOGIN=<your MultiBank account number>
MT5_PASSWORD=<your password>
MT5_SERVER=<exactly as shown in the terminal, e.g. MultiBankGroup-Live>
```

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The frontend can stay wherever you like — point its `BACKEND_URL` at the
Windows machine.

**What the adapter handles for you**

- **Lots versus ounces.** The agent sizes in troy ounces; MT5 wants lots. The
  contract size, volume step, minimum and maximum are read from your symbol and
  the conversion always rounds *down*, so a rounded size never risks more than
  intended.
- **The symbol name.** MultiBank and others suffix their symbols. The terminal's
  Market Watch is searched for gold; pin `MT5_SYMBOL` if you want a specific one.
- **Server time.** MT5 stamps candles in the *broker's* timezone but encodes them
  as if they were UTC. MultiBank servers run UTC+2/+3, so taking them at face
  value would shift every London and New York session window by hours. The
  offset is measured from a live tick and removed.
- **Filling modes.** Sending FOK to a symbol that only accepts IOC is a common
  cause of rejected MT5 orders. The mode is read from the symbol and matched.
- **Minimum stop distance.** Servers reject stops placed too close to price;
  that is checked before the order is sent, and reported in plain words.
- **Your manual trades.** Every order carries `MT5_MAGIC`. Positions without it
  are never read, modified or closed — trade by hand in the same account safely.

**Check these two before going anywhere near live money**

1. **The server offset.** Start the backend and read the log line
   `MT5 server clock detected at UTC+3.0h`. If it instead warns that the market
   looked closed, set `MT5_SERVER_UTC_OFFSET_HOURS` yourself. A wrong value
   silently trades the wrong hours.
2. **The symbol and contract.** The log prints
   `XAUUSD contract: 1 lot = 100 oz, step 0.01 lots (1 oz), 2 digits`. Confirm
   that matches your MultiBank contract specification.

Run it against a **MultiBank demo account** first. The adapter is covered by
tests against a simulated terminal, but no test can substitute for watching it
place one real order on your own server.

## The console

| Page | What it shows |
| --- | --- |
| Console | Live price and spread, account and day limits, the open position, the full gate-by-gate result of the last evaluation, the decision log |
| Trades | Every trade taken, with its R multiple and P&L, plus win rate, profit factor and expectancy |
| Backtest | The same strategy, risk and management code replayed over real OANDA history |
| Rules | The limits currently in force and the upcoming release blackout |

## API

```
GET  /health                     service, mode, whether the broker is configured
GET  /agent/status               everything: account, quote, day book, position, last cycle
POST /agent/start | /agent/stop  begin or end trading
POST /agent/cycle?force=true     evaluate now without opening anything
POST /agent/flatten              close all gold positions
POST /agent/reset-halt           clear a drawdown halt
GET  /agent/decisions            the audit trail, taken or not
GET  /agent/config               the limits in force
GET  /market/price | /candles | /session | /calendar
GET  /trades | /trades/open | /trades/performance
POST /backtest/run               replay the rules over history
```

## Backtesting

The backtest imports the live `GoldStrategy`, `RiskManager` and management
rules rather than reimplementing them, so what it measures is what the agent
would have done. It truncates every higher timeframe to candles that had
already closed at each step, so there is no look-ahead, and it resolves
ambiguous bars against the position.

It is a measurement of the rules against history, not a prediction. Live
results are worse: real spreads move, fills slip, and news gaps through stops.

## Tests

```bash
cd backend && python -m pytest        # 127 tests, no network, no terminal
cd frontend && npm run build          # type-checks and builds
```

The suite covers the indicator maths, every gate the strategy can fail, the
sizing arithmetic and each risk limit, the stop-management invariants, the
simulator's pessimistic fills, the agent loop end to end against a scripted
market, the HTTP surface, and the MT5 adapter against a fake terminal —
lot conversion, server-time correction, filling modes, stop distances and
magic-number isolation.

The MT5 tests use a stand-in for the MetaTrader5 package, so they run on any
platform. They prove the conversions, not that your broker behaves as
expected; only a real terminal can show that.

## Risk

This software places orders. Gold moves quickly, leverage magnifies it, and a
run of losses is a normal outcome of any strategy. Run it in paper mode long
enough to see how it behaves before considering anything else, use a practice
account after that, and never allocate money you cannot afford to lose. The
limits above reduce the damage from a bad run; they cannot prevent one.
