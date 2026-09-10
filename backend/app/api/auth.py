"""
API access control.

The agent's API can start trading, close positions and read the account. On
localhost that is fine unprotected. The moment it is reachable from anywhere
else — a tunnel, a VPS, a hosted console — an open endpoint means anyone who
finds the URL can start or flatten a live position.

So: set API_TOKEN and every route except /health requires it. Live trading
without one is refused outright, because that is the case where an exposed
endpoint costs real money.
"""

from __future__ import annotations

import logging
import secrets

from fastapi import Header, HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)


def token_configured() -> bool:
    return bool(settings.API_TOKEN.strip())


async def require_token(
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None),
) -> None:
    """
    Accept the token as `Authorization: Bearer <token>` or `X-API-Token`.

    With no API_TOKEN configured the API is open — intended only for a backend
    bound to localhost. main.py refuses to start in live mode in that state.
    """
    if not token_configured():
        return

    expected = settings.API_TOKEN.strip()
    presented = ""
    if authorization and authorization.lower().startswith("bearer "):
        presented = authorization[7:].strip()
    elif x_api_token:
        presented = x_api_token.strip()

    # compare_digest keeps the check constant-time.
    if not presented or not secrets.compare_digest(presented, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def check_startup_safety() -> None:
    """Refuse the dangerous combination; warn about the merely risky one."""
    if settings.is_live and not token_configured():
        raise RuntimeError(
            "Refusing to start: AGENT_MODE=live with no API_TOKEN. The API can "
            "open and close real positions, so it must not be reachable "
            "unauthenticated. Set API_TOKEN in backend/.env to a long random "
            "string (python -c \"import secrets; print(secrets.token_urlsafe(32))\") "
            "and give the console the same value."
        )
    if not token_configured():
        logger.warning(
            "API_TOKEN is not set — every endpoint is open, including the ones "
            "that start trading and close positions. Safe only while the "
            "backend is reachable from this machine alone. Set API_TOKEN "
            "before exposing it through a tunnel, a VPS or a hosted console."
        )
