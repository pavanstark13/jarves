"""
TradeAnalyst — deep AI-powered trade intelligence using Google Gemini.

Computes rich statistics from raw trade records, then sends structured
data + prompts to Gemini for actionable pattern insights.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

import httpx
import numpy as np

from app.config import settings

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MODEL = "gemini-1.5-flash"


class TradeAnalyst:
    def __init__(self) -> None:
        self._key = settings.GOOGLE_API_KEY or ""
        self._url = f"{GEMINI_BASE}/{MODEL}:generateContent?key={self._key}"

    def _generate(self, prompt: str, max_tokens: int = 2048) -> str:
        if not self._key:
            return "GOOGLE_API_KEY not configured. Add it to your .env to enable AI insights."
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3},
        }
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(self._url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return f"Gemini response error: {data}"

    # ── stats helpers ─────────────────────────────────────────────────────────

    def _compute_stats(self, trades: list) -> dict[str, Any]:
        """Compute comprehensive statistics from trade list."""
        if not trades:
            return {}

        total   = len(trades)
        wins    = [t for t in trades if t.result == "WIN"]
        losses  = [t for t in trades if t.result == "LOSS"]
        bes     = [t for t in trades if t.result == "BE"]

        win_rate     = len(wins) / total * 100 if total else 0
        gross_profit = sum(t.pnl for t in wins)
        gross_loss   = abs(sum(t.pnl for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        r_multiples = [t.r_multiple for t in trades if t.r_multiple != 0]
        avg_win_r   = float(np.mean([t.r_multiple for t in wins]))  if wins   else 0
        avg_loss_r  = float(np.mean([t.r_multiple for t in losses])) if losses else 0
        expectancy  = (win_rate/100 * avg_win_r) - ((1 - win_rate/100) * abs(avg_loss_r))

        # Per symbol
        by_symbol: dict[str, list] = defaultdict(list)
        for t in trades:
            by_symbol[t.symbol].append(t)

        symbol_stats = {}
        for sym, sym_trades in by_symbol.items():
            sym_wins = [t for t in sym_trades if t.result == "WIN"]
            sym_losses = [t for t in sym_trades if t.result == "LOSS"]
            sym_pnl = sum(t.pnl for t in sym_trades)
            symbol_stats[sym] = {
                "trades": len(sym_trades),
                "wins": len(sym_wins),
                "losses": len(sym_losses),
                "win_rate": round(len(sym_wins) / len(sym_trades) * 100, 1) if sym_trades else 0,
                "total_pnl": round(sym_pnl, 2),
                "avg_r": round(float(np.mean([t.r_multiple for t in sym_trades])), 3),
                "best_trade": round(max((t.pnl for t in sym_trades), default=0), 2),
                "worst_trade": round(min((t.pnl for t in sym_trades), default=0), 2),
            }

        # Per session
        by_session: dict[str, list] = defaultdict(list)
        for t in trades:
            sess = t.session.upper() if t.session else "UNKNOWN"
            by_session[sess].append(t)

        session_stats = {}
        for sess, s_trades in by_session.items():
            s_wins = [t for t in s_trades if t.result == "WIN"]
            session_stats[sess] = {
                "trades": len(s_trades),
                "wins": len(s_wins),
                "win_rate": round(len(s_wins) / len(s_trades) * 100, 1) if s_trades else 0,
                "total_pnl": round(sum(t.pnl for t in s_trades), 2),
                "avg_r": round(float(np.mean([t.r_multiple for t in s_trades])), 3),
            }

        # Per direction
        longs  = [t for t in trades if t.direction in ("LONG", "BUY")]
        shorts = [t for t in trades if t.direction in ("SHORT", "SELL")]
        long_wins  = [t for t in longs  if t.result == "WIN"]
        short_wins = [t for t in shorts if t.result == "WIN"]

        direction_stats = {
            "LONG": {
                "trades": len(longs), "wins": len(long_wins),
                "win_rate": round(len(long_wins)/len(longs)*100, 1) if longs else 0,
                "total_pnl": round(sum(t.pnl for t in longs), 2),
            },
            "SHORT": {
                "trades": len(shorts), "wins": len(short_wins),
                "win_rate": round(len(short_wins)/len(shorts)*100, 1) if shorts else 0,
                "total_pnl": round(sum(t.pnl for t in shorts), 2),
            },
        }

        # Per exit reason
        by_exit: dict[str, list] = defaultdict(list)
        for t in trades:
            by_exit[t.exit_reason or "UNKNOWN"].append(t)

        exit_stats = {
            reason: {
                "count": len(grp),
                "avg_r": round(float(np.mean([t.r_multiple for t in grp])), 3),
                "total_pnl": round(sum(t.pnl for t in grp), 2),
            }
            for reason, grp in by_exit.items()
        }

        # Setup quality buckets
        high_q  = [t for t in trades if t.setup_quality >= 80]
        mid_q   = [t for t in trades if 60 <= t.setup_quality < 80]
        low_q   = [t for t in trades if 0 < t.setup_quality < 60]

        quality_stats = {}
        for label, grp in [("HIGH_80+", high_q), ("MID_60-80", mid_q), ("LOW_<60", low_q)]:
            if grp:
                g_wins = [t for t in grp if t.result == "WIN"]
                quality_stats[label] = {
                    "trades": len(grp),
                    "win_rate": round(len(g_wins)/len(grp)*100, 1),
                    "avg_r": round(float(np.mean([t.r_multiple for t in grp])), 3),
                    "total_pnl": round(sum(t.pnl for t in grp), 2),
                }

        # Consecutive losses (max streak)
        results_seq = [t.result for t in trades]
        max_loss_streak = _max_streak(results_seq, "LOSS")
        max_win_streak  = _max_streak(results_seq, "WIN")

        return {
            "total_trades":    total,
            "wins":            len(wins),
            "losses":          len(losses),
            "breakevens":      len(bes),
            "win_rate":        round(win_rate, 2),
            "profit_factor":   round(profit_factor, 3),
            "expectancy_r":    round(expectancy, 3),
            "gross_profit":    round(gross_profit, 2),
            "gross_loss":      round(gross_loss, 2),
            "net_pnl":         round(gross_profit - gross_loss, 2),
            "avg_win_r":       round(avg_win_r, 3),
            "avg_loss_r":      round(avg_loss_r, 3),
            "max_loss_streak": max_loss_streak,
            "max_win_streak":  max_win_streak,
            "by_symbol":       symbol_stats,
            "by_session":      session_stats,
            "by_direction":    direction_stats,
            "by_exit_reason":  exit_stats,
            "by_setup_quality": quality_stats,
        }

    # ── public methods ────────────────────────────────────────────────────────

    def full_analysis(self, trades: list, account_balance: float) -> dict[str, Any]:
        stats = self._compute_stats(trades)

        prompt = f"""You are a professional quantitative trading analyst with expertise in Smart Money Concepts (SMC) and prop firm trading.

Analyze the following trading data comprehensively. The trader uses a multi-timeframe SMC strategy on 8 forex/gold/crypto pairs with OANDA paper trading.

=== ACCOUNT: ${account_balance:,.0f} ===

=== OVERALL STATS ===
{json.dumps({k: v for k, v in stats.items() if not isinstance(v, dict)}, indent=2)}

=== PERFORMANCE BY SYMBOL ===
{json.dumps(stats.get('by_symbol', {}), indent=2)}

=== PERFORMANCE BY SESSION ===
{json.dumps(stats.get('by_session', {}), indent=2)}

=== PERFORMANCE BY DIRECTION (LONG vs SHORT) ===
{json.dumps(stats.get('by_direction', {}), indent=2)}

=== PERFORMANCE BY SETUP QUALITY ===
{json.dumps(stats.get('by_setup_quality', {}), indent=2)}

=== EXIT REASON ANALYSIS ===
{json.dumps(stats.get('by_exit_reason', {}), indent=2)}

Provide a DETAILED analysis covering ALL of these sections. Use headers and bullet points:

## 1. OVERALL PERFORMANCE VERDICT
(Is this strategy profitable? What is the edge? Grade: A/B/C/D/F)

## 2. WINNING PATTERNS
(What conditions consistently produce wins? Specific pairs, sessions, setups, R multiples)

## 3. LOSING PATTERNS  
(What is causing losses? Specific pairs, sessions, setups to avoid. Be brutally honest.)

## 4. BEST PAIRS TO TRADE
(Rank pairs by profitability and win rate. Explain WHY each pair works or doesn't)

## 5. SESSION ANALYSIS
(Which sessions are profitable? Which destroy the account? Exact UTC hours to trade)

## 6. LONG vs SHORT BIAS
(Is the trader better at longs or shorts? Why? What does this reveal about market bias?)

## 7. SETUP QUALITY CORRELATION
(Does higher setup quality = higher win rate? At what threshold should trades be taken?)

## 8. SILENT PERIODS — WHEN TO STAY OUT
(List specific conditions where the trader should NOT trade. Be specific.)

## 9. RISK MANAGEMENT FINDINGS
(Max loss streak implications, position sizing advice, R/R observations)

## 10. PERSONALIZED EDGE SUMMARY
(In 3 sentences: what is this trader's specific edge and how to maximize it)"""

        ai_text = self._generate(prompt, max_tokens=3000)

        return {
            "stats": stats,
            "ai_analysis": ai_text,
            "generated_at": _now(),
        }

    def generate_strategy(self, trades: list, account_balance: float) -> dict[str, Any]:
        stats = self._compute_stats(trades)

        # Find best performing symbol and session
        best_sym = max(stats["by_symbol"].items(), key=lambda x: x[1]["total_pnl"], default=("N/A", {}))[0] if stats.get("by_symbol") else "N/A"
        best_sess = max(stats["by_session"].items(), key=lambda x: x[1]["total_pnl"], default=("N/A", {}))[0] if stats.get("by_session") else "N/A"
        best_dir = max(stats["by_direction"].items(), key=lambda x: x[1]["total_pnl"], default=("LONG", {}))[0] if stats.get("by_direction") else "LONG"

        prompt = f"""You are a quantitative trading strategist. Based on this trader's actual performance data, design a PERSONALIZED trading strategy they should follow going forward.

Key findings from their data:
- Win Rate: {stats.get('win_rate', 0):.1f}% | Profit Factor: {stats.get('profit_factor', 0):.2f}
- Best symbol: {best_sym} | Best session: {best_sess} | Best direction: {best_dir}
- Avg Win R: {stats.get('avg_win_r', 0):.2f} | Avg Loss R: {stats.get('avg_loss_r', 0):.2f}
- Max consecutive losses: {stats.get('max_loss_streak', 0)}

By Symbol:
{json.dumps(stats.get('by_symbol', {}), indent=2)}

By Session:
{json.dumps(stats.get('by_session', {}), indent=2)}

By Direction:
{json.dumps(stats.get('by_direction', {}), indent=2)}

Design a COMPLETE PERSONALIZED STRATEGY using this exact format:

## STRATEGY NAME
(Give it a name based on the trader's edge)

## CORE PHILOSOPHY
(1-2 sentences on what this strategy exploits)

## APPROVED INSTRUMENTS
(List ONLY the pairs where this trader has positive expectancy, with reason)

## BANNED INSTRUMENTS  
(List pairs to stop trading completely, with reason)

## APPROVED SESSIONS (UTC)
(Exact time windows when this trader should trade)

## BANNED SESSIONS
(Sessions to avoid completely)

## DIRECTION BIAS RULES
(Long only? Short only? Both? Under what market conditions?)

## ENTRY CHECKLIST (ordered by importance)
1. [Filter 1]
2. [Filter 2]
... (list 6-8 specific filters based on what's working)

## MINIMUM SETUP QUALITY THRESHOLD
(What score should trigger skipping a trade?)

## POSITION SIZING RULES
(Based on their max loss streak and account size of ${account_balance:,.0f})

## DAILY/WEEKLY LIMITS
(Max trades per day, max loss per day, max win target)

## THE ONE RULE TO NEVER BREAK
(The single most important rule based on their biggest losing pattern)

## EXPECTED MONTHLY PERFORMANCE
(Realistic expectation based on their data — trades/month, expected R, expected $ at 1% risk)"""

        ai_strategy = self._generate(prompt, max_tokens=2500)

        return {
            "stats_summary": {
                "win_rate": stats.get("win_rate"),
                "profit_factor": stats.get("profit_factor"),
                "best_symbol": best_sym,
                "best_session": best_sess,
                "best_direction": best_dir,
            },
            "personalized_strategy": ai_strategy,
            "generated_at": _now(),
        }

    def pair_deep_dive(self, symbol: str, trades: list, account_balance: float) -> dict[str, Any]:
        stats = self._compute_stats(trades)

        prompt = f"""Perform a deep analysis of {symbol} trading performance.

Stats:
{json.dumps(stats, indent=2)}

Provide:
## {symbol} PERFORMANCE VERDICT
## WHAT WORKS ON {symbol}
## WHAT FAILS ON {symbol}
## OPTIMAL SESSION FOR {symbol}
## BEST DIRECTION (LONG/SHORT) FOR {symbol}
## SETUP QUALITY FINDINGS
## SPECIFIC ENTRY RULES FOR {symbol}
## SPECIFIC EXIT RULES FOR {symbol}
## RISK RECOMMENDATION (lot size, SL placement, TP targets)
## VERDICT: Continue trading {symbol}? Yes/No/Reduce size — with clear reasoning"""

        ai_text = self._generate(prompt, max_tokens=1500)
        return {"symbol": symbol, "stats": stats, "ai_analysis": ai_text, "generated_at": _now()}

    def identify_silent_periods(self, trades: list) -> dict[str, Any]:
        stats = self._compute_stats(trades)

        # Find losing sessions and symbols
        losing_sessions = [
            s for s, d in stats.get("by_session", {}).items()
            if d.get("total_pnl", 0) < 0 or d.get("win_rate", 100) < 40
        ]
        losing_symbols = [
            s for s, d in stats.get("by_symbol", {}).items()
            if d.get("total_pnl", 0) < 0
        ]
        losing_direction = min(
            stats.get("by_direction", {}).items(),
            key=lambda x: x[1].get("total_pnl", 0),
            default=("NONE", {})
        )[0] if stats.get("by_direction") else "NONE"

        prompt = f"""Based on this trading data, identify ALL conditions where this trader should STOP TRADING immediately.

Stats:
Total Trades: {stats.get('total_trades', 0)} | Win Rate: {stats.get('win_rate', 0):.1f}%
Losing sessions: {losing_sessions}
Losing symbols: {losing_symbols}
Weaker direction: {losing_direction}
Max consecutive losses: {stats.get('max_loss_streak', 0)}

By Session: {json.dumps(stats.get('by_session', {}), indent=2)}
By Symbol: {json.dumps(stats.get('by_symbol', {}), indent=2)}
By Direction: {json.dumps(stats.get('by_direction', {}), indent=2)}
By Setup Quality: {json.dumps(stats.get('by_setup_quality', {}), indent=2)}

Provide a SILENCE PROTOCOL with these exact sections:

## RED FLAG CONDITIONS — STOP TRADING IMMEDIATELY
(List every specific situation that reliably leads to losses)

## DANGEROUS SESSIONS — NEVER TRADE DURING
(With UTC times and reason from the data)

## PAIRS TO ELIMINATE
(Which pairs are destroying P&L? With proof from the stats)

## SETUP CONDITIONS TO SKIP
(Low quality setups, specific patterns that fail)

## NEWS & MACRO EVENTS TO SIT OUT
(Types of events where the trader should step back)

## DAILY LOSS LIMIT PROTOCOL
(After X losses in a day, stop. Based on max loss streak data)

## WEEKLY RESET RULES
(When and how to reset after a losing week)

## THE SILENCE MANTRA
(One powerful sentence the trader should repeat before placing a trade they're unsure about)"""

        ai_text = self._generate(prompt, max_tokens=2000)

        return {
            "losing_sessions": losing_sessions,
            "losing_symbols": losing_symbols,
            "stats_summary": {
                "max_loss_streak": stats.get("max_loss_streak"),
                "by_session": stats.get("by_session"),
                "by_symbol": stats.get("by_symbol"),
            },
            "silence_protocol": ai_text,
            "generated_at": _now(),
        }


# ── helpers ───────────────────────────────────────────────────────────────────

def _max_streak(results: list[str], target: str) -> int:
    max_s = cur = 0
    for r in results:
        cur = cur + 1 if r == target else 0
        max_s = max(max_s, cur)
    return max_s


def _now() -> str:
    import datetime
    return datetime.datetime.utcnow().isoformat()
