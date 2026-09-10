"""Indicator maths — the numbers everything else is decided from."""

from __future__ import annotations

import numpy as np

from app.core import indicators as ind


def test_ema_tracks_a_constant_series_exactly():
    assert ind.ema([100.0] * 50, 20)[-1] == 100.0


def test_ema_lags_behind_a_rising_series():
    rising = [100.0 + i for i in range(50)]
    assert ind.ema(rising, 20)[-1] < rising[-1]


def test_rsi_is_100_when_every_bar_rises_and_0_when_every_bar_falls():
    assert ind.rsi([100.0 + i for i in range(40)], 14) == 100.0
    assert ind.rsi([100.0 - i for i in range(40)], 14) == 0.0


def test_rsi_of_a_flat_market_is_neutral():
    assert ind.rsi([100.0] * 40, 14) == 50.0


def test_rsi_needs_history_and_falls_back_to_neutral():
    assert ind.rsi([100.0, 101.0], 14) == 50.0


def test_atr_of_constant_range_bars_equals_that_range():
    closes = [100.0] * 40
    highs = [101.0] * 40
    lows = [99.0] * 40
    assert ind.atr(highs, lows, closes, 14) == 2.0


def test_atr_includes_gaps_through_the_previous_close():
    closes = [100.0, 100.0, 120.0]
    highs = [101.0, 101.0, 121.0]
    lows = [99.0, 99.0, 119.0]
    # The third bar gapped 20 above the prior close, so true range exceeds 2.
    assert ind.atr(highs, lows, closes, 2) > 2.0


def test_swing_high_is_the_strict_peak_of_its_neighbourhood():
    highs = [1.0, 2.0, 5.0, 2.5, 1.5, 1.0, 0.5]
    assert ind.swing_highs(highs, 2, 2) == [2]


def test_swing_detection_ignores_a_tied_extreme():
    # Two neighbouring bars at the same high are not a swing.
    assert ind.swing_highs([1.0, 5.0, 5.0, 2.0, 1.0], 2, 2) == []


def test_swing_structure_reads_an_uptrend_as_higher_highs_and_lows():
    highs, lows = [], []
    for cycle in range(4):
        base = cycle * 10.0
        highs += [base + 1, base + 3, base + 8, base + 4, base + 2]
        lows += [base, base + 1, base + 5, base + 2, base + 1]
    ok, shape = ind.swing_structure(highs, lows, "LONG", lookback=40)
    assert ok
    assert "higher high" in shape


def test_swing_structure_rejects_the_wrong_direction():
    highs, lows = [], []
    for cycle in range(4):
        base = cycle * 10.0
        highs += [base + 1, base + 3, base + 8, base + 4, base + 2]
        lows += [base, base + 1, base + 5, base + 2, base + 1]
    ok, _ = ind.swing_structure(highs, lows, "SHORT", lookback=40)
    assert not ok


def test_break_of_structure_requires_the_close_to_come_after_the_swing():
    # Price spikes to 10, falls back, and never trades above it again: the
    # earlier closes must not count as a break of that later swing.
    highs = [5, 6, 10, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 4, 5]
    lows = [h - 2 for h in highs]
    closes = [h - 1 for h in highs]
    assert not ind.broke_structure(highs, lows, closes, "LONG", lookback=20)


def test_break_of_structure_detects_a_close_above_a_confirmed_swing():
    highs = [5, 6, 8, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 9, 10, 11, 12, 13, 14, 15, 16]
    lows = [h - 2 for h in highs]
    closes = [h - 0.5 for h in highs]
    assert ind.broke_structure(highs, lows, closes, "LONG", lookback=20)


def test_touched_level_sees_a_dip_to_the_average():
    highs = [10.0] * 10
    lows = [9.0] * 9 + [7.0]
    average = [8.0] * 10
    assert ind.touched_level(highs, lows, average, "LONG", bars=5)
    assert not ind.touched_level(highs, [9.0] * 10, average, "LONG", bars=5)


def test_fair_value_gap_is_a_three_bar_imbalance():
    highs = [10.0, 12.0, 16.0]
    lows = [8.0, 9.0, 14.0]
    gaps = ind.fair_value_gaps(highs, lows, "LONG", lookback=10)
    assert gaps == [(10.0, 14.0)]


def test_indicators_return_plain_python_floats():
    closes = [100.0 + i * 0.5 for i in range(40)]
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    assert isinstance(ind.rsi(closes), float) and not isinstance(ind.rsi(closes), np.generic)
    assert isinstance(ind.atr(highs, lows, closes), float)
