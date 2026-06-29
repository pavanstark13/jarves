"""
AIOrchestrator — LLM orchestration using Google Gemini REST API.

Free tier: 15 RPM, 1M tokens/day on gemini-1.5-flash — no credit card needed.
Get API key: https://aistudio.google.com/app/apikey

Uses httpx directly (no google-generativeai SDK needed).
"""

import json
from typing import Any

import httpx

from app.config import settings
from app.schemas.analysis import AnalysisResult
from app.schemas.risk import RiskCheckResult

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MODEL = "gemini-1.5-flash"


class AIOrchestrator:
    def __init__(self) -> None:
        if not settings.GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY is not set. "
                "Get a free key at https://aistudio.google.com/app/apikey "
                "and add GOOGLE_API_KEY= to your .env file."
            )
        self._key = settings.GOOGLE_API_KEY
        self._url = f"{GEMINI_BASE}/{MODEL}:generateContent?key={self._key}"

    def _generate(self, prompt: str, max_tokens: int = 1024) -> str:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.4},
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(self._url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Gemini unexpected response: {data}") from e

    def explain_trade(
        self, analysis_result: AnalysisResult, risk_result: RiskCheckResult
    ) -> str:
        """Explain why a trade qualifies or was rejected in plain English."""
        engine_summary = "\n".join(
            f"  - {e.engine_name}: {e.signal} (confidence {e.confidence:.0%})"
            for e in analysis_result.engines
        )
        trade_status = (
            f"APPROVED — size: {risk_result.position_size} lots, "
            f"risk: {risk_result.risk_pct_used}%, R/R: {risk_result.risk_reward}"
            if risk_result.approved
            else f"REJECTED — {risk_result.rejection_reason}"
        )
        prompt = f"""You are a professional trading analyst for a systematic SMC trading system.
Explain the following trade decision concisely (3-5 sentences) to a trader.
Focus on WHY, write in flowing prose, no bullet points.

Symbol: {analysis_result.symbol} | Timeframe: {analysis_result.timeframe}
Setup Quality: {analysis_result.setup_quality:.1f}/100 | Signal: {analysis_result.overall_signal}
Aligned: {', '.join(analysis_result.aligned_signals) or 'None'}
Conflicting: {', '.join(analysis_result.conflicting_signals) or 'None'}

Engines:
{engine_summary}

Risk Decision: {trade_status}
Passed: {', '.join(risk_result.checks_passed)}
Failed: {', '.join(risk_result.checks_failed)}"""
        return self._generate(prompt)

    def summarize_news(self, news_items: list[dict[str, Any]]) -> str:
        """Produce a brief market news summary."""
        if not news_items:
            return "No news items provided."
        headlines = "\n".join(
            f"- [{item.get('source', '?')}] {item.get('title', '')} ({item.get('sentiment', 'neutral')})"
            for item in news_items[:20]
        )
        prompt = f"""You are a concise financial news analyst.
Summarize these headlines in 3-4 sentences. State the dominant sentiment and main macro themes.
Write for a trader making real-time decisions.

Headlines:
{headlines}"""
        return self._generate(prompt, max_tokens=512)

    def generate_journal_insight(self, trades_history: list[dict[str, Any]]) -> str:
        """Analyse trade history and surface pattern insights."""
        if not trades_history:
            return "No trade history available for analysis."
        rows = [
            {k: t.get(k) for k in ("symbol", "direction", "session", "setup_quality", "result", "r_multiple", "pnl")}
            for t in trades_history[-50:]
        ]
        prompt = f"""You are a quantitative trading performance analyst.
Give 4-6 numbered, data-driven insights from this trade journal.
Cover: winning/losing patterns, session performance, setup quality correlation, edges and weaknesses.
End with one concrete improvement recommendation.

Trade History ({len(rows)} trades):
{json.dumps(rows, indent=2)}"""
        return self._generate(prompt)
