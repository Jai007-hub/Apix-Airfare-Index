import pytest

from datetime import date, timedelta

from db.models import Carrier, CarrierType, CityPair, CleanFare
from index.traveller import route_leaderboard, traveller_summary

TODAY = date(2026, 7, 31)


def _seed(db_session):
    route = CityPair(origin="DEL", destination="BOM", label="DEL-BOM", dgca_weight=0.22)
    indigo = Carrier(code="6E", name="IndiGo", carrier_type=CarrierType.LCC)
    air_india = Carrier(code="AI", name="Air India", carrier_type=CarrierType.FSC)
    db_session.add_all([route, indigo, air_india])
    db_session.commit()
    return route, indigo, air_india


def _fare(route, carrier, obs_date, window, total):
    return CleanFare(
        observation_date=obs_date,
        route_id=route.id,
        carrier_id=carrier.id,
        advance_window_days=window,
        fare_class="Economy",
        median_base_fare=total * 0.8,
        median_taxes=total * 0.05,
        median_udf=total * 0.1,
        median_convenience_fee=total * 0.05,
        median_total_fare=total,
        min_total_fare=total,
        max_total_fare=total,
        n_obs=5,
        n_excluded_outliers=0,
        n_sold_out=0,
    )


def test_identifies_cheapest_booking_window_and_the_saving(db_session):
    """The traveller-facing headline: book early, save this much."""
    route, indigo, _ = _seed(db_session)
    # Classic lead-time curve: last-minute dear, booked-ahead cheap.
    for window, fare in [(1, 12000), (7, 8000), (15, 6000), (30, 5000), (45, 4500)]:
        db_session.add(_fare(route, indigo, TODAY, window, fare))
    db_session.commit()

    s = traveller_summary(db_session, "DEL-BOM")

    assert s["cheapest_window"]["window_days"] == 45
    assert s["cheapest_window"]["fare"] == 4500
    assert s["dearest_window"]["window_days"] == 1
    assert s["max_saving"] == 7500
    assert s["max_saving_pct"] == 62.5


def test_carriers_are_compared_at_one_booking_window(db_session):
    """Comparing an airline's T+45 price against another's T+1 would be
    meaningless, so the ranking holds the window fixed."""
    route, indigo, air_india = _seed(db_session)
    db_session.add_all(
        [
            _fare(route, indigo, TODAY, 45, 4000),
            _fare(route, air_india, TODAY, 45, 6000),
            # Air India looks cheap here, but at a different window entirely.
            _fare(route, air_india, TODAY, 1, 1000),
            _fare(route, indigo, TODAY, 1, 12000),
        ]
    )
    db_session.commit()

    s = traveller_summary(db_session, "DEL-BOM")

    assert s["cheapest_window"]["window_days"] == 45
    assert [c["code"] for c in s["carriers"]] == ["6E", "AI"]
    assert s["carriers"][0]["fare"] == 4000

    # Each window ranks independently, so the reader can switch between them
    # without ever seeing carriers from two windows mixed together.
    assert [c["code"] for c in s["carriers_by_window"][45]] == ["6E", "AI"]
    assert [c["code"] for c in s["carriers_by_window"][1]] == ["AI", "6E"]
    # The default list is just the cheapest window's, not a separate answer.
    assert s["carriers"] == s["carriers_by_window"][45]


def test_trend_compares_this_month_against_the_previous_one(db_session):
    route, indigo, _ = _seed(db_session)
    # Prior 30-day block cheap, recent 30-day block dearer -> fares rising.
    for offset in range(30, 60):
        db_session.add(_fare(route, indigo, TODAY - timedelta(days=offset), 15, 5000))
    for offset in range(0, 30):
        db_session.add(_fare(route, indigo, TODAY - timedelta(days=offset), 15, 6000))
    db_session.commit()

    s = traveller_summary(db_session, "DEL-BOM")

    assert s["trend_direction"] == "up"
    assert s["trend_pct"] == 20.0


def test_unknown_route_is_reported_not_guessed(db_session):
    _seed(db_session)
    assert "error" in traveller_summary(db_session, "XXX-YYY")


def test_route_that_went_stale_is_reported_not_priced_from_old_data(db_session):
    """If collection for one route stops while others keep reporting, that
    route must say it has no recent fares -- quoting a traveller a price from
    months ago would be worse than saying nothing."""
    route, indigo, _ = _seed(db_session)
    other = CityPair(origin="BLR", destination="HYD", label="BLR-HYD", dgca_weight=0.08)
    db_session.add(other)
    db_session.commit()

    # The other route is current, so "latest" is today...
    db_session.add(_fare(other, indigo, TODAY, 15, 5000))
    # ...but DEL-BOM last reported six months ago.
    db_session.add(_fare(route, indigo, TODAY - timedelta(days=180), 15, 5000))
    db_session.commit()

    assert "error" in traveller_summary(db_session, "DEL-BOM")
    assert "error" not in traveller_summary(db_session, "BLR-HYD")


@pytest.mark.parametrize("totals", [(4009, 4010, 4011), (4029, 4030, 4031)])
def test_fare_breakdown_adds_up_to_the_fare_shown(db_session, totals):
    """A split that doesn't reconcile with the headline number reads as a bug
    to anyone who checks it, and rounding four lines independently can leave
    it a rupee out.

    Both parameter sets are chosen to actually break that way -- one rounds a
    rupee short, the other a rupee over -- so this fails if the residual is
    left unabsorbed. Spread over the recent week because the cleaned grain is
    unique per (date, route, carrier, window).
    """
    route, indigo, _ = _seed(db_session)
    for offset, total in enumerate(totals):
        db_session.add(_fare(route, indigo, TODAY - timedelta(days=offset), 45, total))
    db_session.commit()

    s = traveller_summary(db_session, "DEL-BOM")

    assert sum(s["fare_breakdown"].values()) == s["cheapest_window"]["fare"]


def test_sold_out_rate_is_reported_per_booking_window(db_session):
    """Leaving it late costs more *and* more often leaves nothing to buy --
    the second half is the part a traveller can't see on a fare table."""
    route, indigo, _ = _seed(db_session)
    late = _fare(route, indigo, TODAY, 1, 12000)
    late.n_obs, late.n_sold_out = 10, 4
    early = _fare(route, indigo, TODAY, 45, 4000)
    early.n_obs, early.n_sold_out = 10, 0
    db_session.add_all([late, early])
    db_session.commit()

    s = traveller_summary(db_session, "DEL-BOM")
    by_window = {w["window_days"]: w for w in s["windows"]}

    assert by_window[1]["sold_out_pct"] == 40.0
    assert by_window[45]["sold_out_pct"] == 0.0


def test_seasonality_pools_the_same_month_across_years(db_session):
    """Someone planning a January trip wants every January on record, not
    just the most recent one."""
    route, indigo, _ = _seed(db_session)
    db_session.add(_fare(route, indigo, date(2025, 1, 15), 15, 4000))
    db_session.add(_fare(route, indigo, date(2026, 1, 15), 15, 6000))
    db_session.add(_fare(route, indigo, date(2025, 6, 15), 15, 9000))
    db_session.add(_fare(route, indigo, TODAY, 15, 5000))
    db_session.commit()

    months = {m["name"]: m["fare"] for m in traveller_summary(db_session, "DEL-BOM")["months"]}

    assert months["Jan"] == 5000  # both Januaries pooled, not just 2026
    assert months["Jun"] == 9000


def test_leaderboard_ranks_sectors_by_their_cheapest_window(db_session):
    """A sector is listed at the price a traveller would actually pay, which
    means its best window -- not the average across all of them."""
    route, indigo, _ = _seed(db_session)
    other = CityPair(origin="BLR", destination="HYD", label="BLR-HYD", dgca_weight=0.08)
    db_session.add(other)
    db_session.commit()

    # DEL-BOM averages higher but bottoms out lower than BLR-HYD.
    db_session.add_all(
        [
            _fare(route, indigo, TODAY, 1, 20000),
            _fare(route, indigo, TODAY, 45, 3000),
            _fare(other, indigo, TODAY, 1, 5000),
            _fare(other, indigo, TODAY, 45, 4000),
        ]
    )
    db_session.commit()

    board = route_leaderboard(db_session)

    assert [r["route"] for r in board] == ["DEL-BOM", "BLR-HYD"]
    assert board[0]["best_fare"] == 3000
