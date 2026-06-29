"""
AIOrchestrator — LLM orchestration using Anthropic Claude.

Provides three high-level methods:
  - explain_trade(analysis_result, risk_result) -> str
  - summarize_news(news_items) -> str
  - generate_journal_insight(trades_history) -> str

Model: claude-sonnet-4-6
API key loaded from ANTHROPIC_API_KEY environment variable.
"""

import json
from typing import Any

import anthropic

from app.config import settings
from app.schemas.analysis import AnalysisResult
from app.schemas.risk import RiskCheckResult

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024


class AIOrchestrator:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def explain_trade(
        self, analysis_result: AnalysisResult, risk_result: RiskCheckResult
    ) -> str:
        """Explain why a trade qualifies or was rejected in plain English."""
        engine_summary = [
            f"  • {e.engine_name}: {e.signal} (confidence {e.confidence:.0%})"
            for e in analysis_result.engines
        ]
        engine_text = "\n".join(engine_summary)

        if risk_result.approved:
            trade_status = (
                f"APPROVED — Position size: {risk_result.position_size} lots, "
                f"Risk: {risk_result.risk_pct_used}% (${risk_result.risk_amount}), "
                f"R/R: {risk_result.risk_reward}"
            )
        else:
            trade_status = f"REJECTED — Reason: {risk_result.rejection_reason}"

        prompt = f"""You are a professional trading analyst assistant for a systematic trading system.
Explain the following trade decision concisely (3-5 sentences) to a trader:

Symbol: {analysis_result.symbol} | Timeframe: {analysis_result.timeframe}
Setup Quality: {analysis_result.setup_quality:.1f}/100
Overall Signal: {analysis_result.overall_signal}
Aligned Engines: {', '.join(analysis_result.aligned_signals) or 'None'}
Conflicting Engines: {', '.join(analysis_result.conflicting_signals) or 'None'}

Engine Breakdown:
{engine_text}

Risk Decision: {trade_status}
Checks passed: {', '.join(risk_result.checks_passed)}
Checks failed: {', '.join(risk_result.checks_failed)}

Explain the decision in a professional but clear way. Focus on WHY.
Do not include headers or bullet points — write in flowing prose."""

        message = self._client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text  # type: ignore[index]

    def summarize_news(self, news_items: list[dict[str, Any]]) -> str:
        """Produce a brief market news summary from raw news items."""
        if not news_items:
            return "No news items provided."

        headlines = "\n".join(
            f"- [{item.get('source', 'Unknown')}] {item.get('title', '')} "
            f"(sentiment: {item.get('sentiment', 'neutral')})"
            for item in news_items[:20]  # cap at 20
        )

        prompt = f"""You are a concise financial news analyst.
Summarize the following market news headlines in 3-4 sentences.
Highlight the dominant sentiment (bullish/bearish/neutral) and any major macro themes.

Headlines:
{headlines}

Provide a brief, factual summary suitable for a trader making real-time decisions."""

        message = self._client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text  # type: ignore[index]

    def generate_journal_insight(self, trades_history: list[dict[str, Any]]) -> str:
        """Analyse trade history and surface pattern insights."""
        if not trades_history:
            return "No trade history available for analysis."

        # Build a compact summary table
        rows = []
        for t in trades_history[-50:]:  # limit to last 50 trades
            rows.append({
                "symbol": t.get("symbol"),
                "direction": t.get("direction"),
                "session": t.get("session"),
                "setup_quality": t.get("setup_quality"),
                "result": t.get("result"),
                "r_multiple": t.get("r_multiple"),
                "pnl": t.get("pnl"),
            })

        trades_json = json.dumps(rows, indent=2)

        prompt = f"""You are a quantitative trading performance analyst.
Analyse the following trade journal data and provide 4-6 actionable insights.
Focus on: winning patterns, losing patterns, session performance, setup quality correlation,
and any clear edges or weaknesses.

Trade History (last {len(rows)} trades):
{trades_json}

Provide numbered insights. Be specific and data-driven.
End with one concrete recommendation to improve performance."""

        message = self._client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text  # type: ignore[index]
