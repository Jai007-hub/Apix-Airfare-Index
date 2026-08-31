from datetime import date, timedelta

from db.models import Carrier, CarrierType, CityPair, CleanFare
from index.traveller import traveller_summary

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
