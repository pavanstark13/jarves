"""The trading clock and the release blackout."""

from __future__ import annotations

import datetime as dt

from app.core.market import session as session_clock
from app.core.market.calendar import EconomicCalendar, is_high_impact


def at(iso: str) -> dt.datetime:
    return dt.datetime.fromisoformat(iso).replace(tzinfo=dt.timezone.utc)


def test_london_morning_is_tradeable():
    state = session_clock.evaluate(at("2026-03-10T08:30"))
    assert state.can_open
    assert state.session == "LONDON"


def test_the_overlap_is_tradeable():
    state = session_clock.evaluate(at("2026-03-10T14:00"))
    assert state.can_open
    assert state.session == "LONDON_NEWYORK_OVERLAP"


def test_the_gap_between_windows_is_not_tradeable():
    assert not session_clock.evaluate(at("2026-03-10T11:30")).can_open


def test_the_asian_session_is_not_tradeable():
    state = session_clock.evaluate(at("2026-03-10T02:00"))
    assert not state.can_open
    assert state.session == "ASIA"


def test_the_rollover_window_is_blocked():
    state = session_clock.evaluate(at("2026-03-10T21:00"))
    assert state.is_rollover
    assert not state.can_open


def test_the_weekend_is_closed():
    assert session_clock.evaluate(at("2026-03-14T14:00")).is_weekend      # Saturday
    assert session_clock.evaluate(at("2026-03-15T20:00")).is_weekend      # Sunday, pre-open
    assert not session_clock.evaluate(at("2026-03-15T23:00")).is_weekend  # Sunday, after open


def test_the_friday_close_is_avoided():
    assert not session_clock.evaluate(at("2026-03-13T16:30")).can_open


def test_high_impact_releases_are_recognised_by_name():
    assert is_high_impact("US CPI m/m")
    assert is_high_impact("Non-Farm Employment Change")
    assert is_high_impact("FOMC Statement")
    assert not is_high_impact("Wholesale Inventories")


async def test_the_release_clock_blocks_before_and_after_a_publication():
    calendar = EconomicCalendar(api_key="")
    assert (await calendar.blackout(at("2026-03-10T12:10"))).active   # 20 min before
    assert (await calendar.blackout(at("2026-03-10T12:40"))).active   # 10 min after
    assert not (await calendar.blackout(at("2026-03-10T15:30"))).active


async def test_the_fallback_source_is_named_so_it_is_never_mistaken_for_a_feed():
    assert EconomicCalendar(api_key="").source == "us-release-clock"
    assert EconomicCalendar(api_key="abc").source == "fcsapi"
