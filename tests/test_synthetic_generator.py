from datetime import date

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
