from datetime import date

from index.apix import compute_daily_index, month_start, week_start


def test_compute_daily_index_matches_base_period():
    weights = {"A": 0.6, "B": 0.4}
    base_averages = {"A": (date(2026, 1, 1), 100.0), "B": (date(2026, 1, 1), 200.0)}
    day_avgs = {"A": 100.0, "B": 200.0}
    value, contributions = compute_daily_index(day_avgs, weights, base_averages)
    assert value == 100.0
    assert contributions == {"A": 1.0, "B": 1.0}


def test_compute_daily_index_weighted_change():
    weights = {"A": 0.6, "B": 0.4}
    base_averages = {"A": (date(2026, 1, 1), 100.0), "B": (date(2026, 1, 1), 200.0)}
    day_avgs = {"A": 110.0, "B": 220.0}  # both routes up 10%
    value, _ = compute_daily_index(day_avgs, weights, base_averages)
    assert round(value, 2) == 110.0


def test_compute_daily_index_missing_route_renormalizes_weights():
    weights = {"A": 0.6, "B": 0.4}
    base_averages = {"A": (date(2026, 1, 1), 100.0), "B": (date(2026, 1, 1), 200.0)}
    day_avgs = {"A": 150.0}  # route B has no data today
    value, contributions = compute_daily_index(day_avgs, weights, base_averages)
    assert "B" not in contributions
    assert round(value, 6) == 150.0  # only A contributes, renormalized weight = 1.0


def test_compute_daily_index_no_data_returns_none():
    assert compute_daily_index({}, {"A": 1.0}, {"A": (date(2026, 1, 1), 100.0)}) is None


def test_week_start_is_monday():
    assert week_start(date(2026, 7, 3)).weekday() == 0  # Friday -> preceding Monday
    assert week_start(date(2026, 7, 1)) <= date(2026, 7, 1)


def test_month_start():
    assert month_start(date(2026, 7, 17)) == date(2026, 7, 1)
