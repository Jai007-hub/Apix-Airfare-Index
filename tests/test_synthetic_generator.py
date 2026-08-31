from datetime import date

import pytest

from scraper import config
from scraper.synthetic.generator import SyntheticFareGenerator


def test_generate_for_day_covers_full_grid():
    gen = SyntheticFareGenerator(seed=1)
    records = gen.generate_for_day(date(2026, 7, 1))

    expected_carrier_slots_per_route_window = sum(
        1 if s.source_type == "airline" else len(config.CARRIERS) for s in config.SOURCES
    )
    expected_total = len(config.ROUTES) * len(config.ADVANCE_WINDOWS) * expected_carrier_slots_per_route_window
    assert len(records) == expected_total


def test_records_have_consistent_schema():
    gen = SyntheticFareGenerator(seed=1)
    records = gen.generate_for_day(date(2026, 7, 1))

    valid_routes = {r.label for r in config.ROUTES}
    valid_windows = set(config.ADVANCE_WINDOWS)

    for r in records:
        assert r.route_label in valid_routes
        assert r.advance_window_days in valid_windows
        assert r.data_source_type == "synthetic_fallback"
        assert r.availability_status in ("available", "sold_out")
        if r.availability_status == "sold_out":
            assert r.total_fare is None
        else:
            assert r.total_fare > 0
            assert r.base_fare > 0
            assert r.taxes >= 0
            assert round(r.base_fare + r.taxes + r.udf + r.convenience_fee, 2) == round(r.total_fare, 2)


def test_lead_time_curve_is_downward_sloping_on_average():
    """T+1 fares should, on average across routes/carriers, be higher than T+45 --
    the core stylized fact the whole index construction depends on."""
    gen = SyntheticFareGenerator(seed=7)
    records = gen.generate_range(date(2026, 7, 1), date(2026, 7, 7))

    t1 = [r.total_fare for r in records if r.advance_window_days == 1 and r.total_fare]
    t45 = [r.total_fare for r in records if r.advance_window_days == 45 and r.total_fare]
    assert sum(t1) / len(t1) > sum(t45) / len(t45)


def test_deterministic_given_same_seed():
    gen_a = SyntheticFareGenerator(seed=99)
    gen_b = SyntheticFareGenerator(seed=99)
    a = gen_a.generate_for_day(date(2026, 7, 1))
    b = gen_b.generate_for_day(date(2026, 7, 1))
    assert [r.total_fare for r in a] == [r.total_fare for r in b]


def test_demand_shock_is_stable_across_processes():
    """Regression guard: demand_shock was seeded with the builtin hash(), which
    Python salts per process -- so a "seeded" generator silently produced a
    different dataset on every run. These are golden values; if the shock
    seeding goes back to anything process-dependent, they stop matching.

    (The test above cannot catch it: both generators run inside one process
    and therefore share the same hash salt.)
    """
    import random

    from scraper.synthetic import calibration

    cases = {
        ("2025-01-01", "DEL-BOM"): 1.0636734205323273,
        ("2026-07-31", "MAA-BLR"): 1.0391736237224438,
    }
    for (iso, route), expected in cases.items():
        got = calibration.demand_shock(date.fromisoformat(iso), route, random.Random(0))
        assert got == pytest.approx(expected, abs=1e-12), (
            f"demand_shock({iso}, {route}) = {got!r}; if this changed deliberately, "
            "update the golden values -- if not, the seeding is process-dependent again."
        )


def test_demand_shock_does_not_disturb_the_caller_rng():
    """It reseeds the shared RNG internally, so it must restore the caller's
    stream -- otherwise every draw after it would shift."""
    import random

    from scraper.synthetic import calibration

    rng = random.Random(7)
    rng.random()  # advance the stream
    state_before = rng.getstate()
    calibration.demand_shock(date(2025, 5, 5), "DEL-BLR", rng)
    assert rng.getstate() == state_before
