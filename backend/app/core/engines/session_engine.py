"""
SessionEngine — Returns current forex session based on UTC time.

Sessions (UTC):
  Sydney:   22:00 – 07:00
  Tokyo:    00:00 – 09:00  (Asia)
  London:   07:00 – 16:00
  New York: 13:00 – 22:00
  Overlap:  13:00 – 16:00  (London/NY overlap — highest liquidity)
  Kill Zones (high-probability windows):
    London Kill Zone:    07:00 – 09:00
    NY Kill Zone (AM):   13:00 – 15:00
    NY Kill Zone (Lunch): 17:00 – 18:00  (low liquidity — avoid)
"""

import datetime
from typing import Any

from app.core.engines.base import BaseEngine, EngineResult

# Session UTC ranges (hour, minute)
SESSIONS = {
    "LONDON": (7, 0, 16, 0),
    "NEW_YORK": (13, 0, 22, 0),
    "OVERLAP": (13, 0, 16, 0),
    "ASIA": (0, 0, 9, 0),
    "SYDNEY": (22, 0, 24, 0),  # spans midnight — handled specially
    "LONDON_KILL_ZONE": (7, 0, 9, 0),
    "NY_KILL_ZONE": (13, 0, 15, 0),
    "LUNCH_LOW_LIQUIDITY": (17, 0, 18, 0),
}

# Confidence multipliers for each session
SESSION_SCORES = {
    "OVERLAP": 1.0,
    "LONDON_KILL_ZONE": 0.95,
    "NY_KILL_ZONE": 0.9,
    "LONDON": 0.8,
    "NEW_YORK": 0.8,
    "ASIA": 0.55,
    "SYDNEY": 0.4,
    "LUNCH_LOW_LIQUIDITY": 0.2,
    "OFF_HOURS": 0.1,
}


def _in_session(now: datetime.datetime, start_h: int, start_m: int, end_h: int, end_m: int) -> bool:
    start = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
    return start <= now < end


class SessionEngine(BaseEngine):
    name = "SessionEngine"
    default_weight = 0.8

    def analyze(self, bars: list[dict], **kwargs) -> EngineResult:
        # Accept an optional `current_time` kwarg (UTC datetime) for testing
        now_utc: datetime.datetime = kwargs.get("current_time", datetime.datetime.utcnow())

        active_sessions = self._get_active_sessions(now_utc)
        primary = self._primary_session(active_sessions)
        score = SESSION_SCORES.get(primary, 0.1)

        is_kill_zone = "LONDON_KILL_ZONE" in active_sessions or "NY_KILL_ZONE" in active_sessions
        is_low_liquidity = "LUNCH_LOW_LIQUIDITY" in active_sessions

        if is_low_liquidity:
            signal = "LOW_LIQUIDITY"
            confidence = 0.15
        elif is_kill_zone:
            signal = "KILL_ZONE"
            confidence = 0.95
        elif primary == "OVERLAP":
            signal = "HIGH_LIQUIDITY"
            confidence = 0.9
        elif primary in ("LONDON", "NEW_YORK"):
            signal = "ACTIVE_SESSION"
            confidence = 0.7
        elif primary in ("ASIA", "SYDNEY"):
            signal = "LOW_ACTIVITY"
            confidence = 0.4
        else:
            signal = "OFF_HOURS"
            confidence = 0.1

        details: dict[str, Any] = {
            "utc_time": now_utc.isoformat(),
            "active_sessions": active_sessions,
            "primary_session": primary,
            "is_kill_zone": is_kill_zone,
            "is_low_liquidity": is_low_liquidity,
            "session_score": score,
        }

        return EngineResult(
            engine_name=self.name,
            signal=signal,
            confidence=round(confidence, 4),
            details=details,
            weight=self.default_weight,
        )

    def _get_active_sessions(self, now: datetime.datetime) -> list[str]:
        active = []
        hour = now.hour
        minute = now.minute

        def check(name: str, sh: int, sm: int, eh: int, em: int) -> None:
            if eh == 24:
                # crosses midnight: 22:00 – 24:00
                start = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
                if now >= start:
                    active.append(name)
            elif _in_session(now, sh, sm, eh, em):
                active.append(name)

        for name, (sh, sm, eh, em) in SESSIONS.items():
            check(name, sh, sm, eh, em)

        if not active:
            active.append("OFF_HOURS")
        return active

    def _primary_session(self, active: list[str]) -> str:
        priority = [
            "LUNCH_LOW_LIQUIDITY",
            "NY_KILL_ZONE",
            "LONDON_KILL_ZONE",
            "OVERLAP",
            "NEW_YORK",
            "LONDON",
            "ASIA",
            "SYDNEY",
            "OFF_HOURS",
        ]
        for p in priority:
            if p in active:
                return p
        return "OFF_HOURS"
