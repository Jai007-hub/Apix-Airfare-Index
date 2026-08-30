from datetime import date

from db.models import Carrier, CarrierType, CityPair, CleanFare, IndexValue
from index.explain import explain_index_value

BASE_DATE = date(2026, 7, 1)
QUERY_DATE = date(2026, 7, 2)


def _clean_fare(route_id, carrier_id, obs_date, total, **kwargs):
    return CleanFare(
        observation_date=obs_date,
        route_id=route_id,
        carrier_id=carrier_id,
        advance_window_days=7,
        median_base_fare=total * 0.8,
        median_taxes=total * 0.05,
        median_total_fare=total,
        min_total_fare=total * 0.95,
        max_total_fare=total * 1.05,
        n_obs=kwargs.get("n_obs", 5),
        n_excluded_outliers=kwargs.get("n_excluded_outliers", 0),
        n_sold_out=kwargs.get("n_sold_out", 0),
    )


def _seed_two_routes(db_session):
    a = CityPair(origin="DEL", destination="BOM", label="DEL-BOM", dgca_weight=0.6)
    b = CityPair(origin="DEL", destination="BLR", label="DEL-BLR", dgca_weight=0.4)
    carrier = Carrier(code="6E", name="IndiGo", carrier_type=CarrierType.LCC)
    db_session.add_all([a, b, carrier])
    db_session.commit()
    return a, b, carrier


def test_contributions_sum_to_the_index_value(db_session):
    """The whole point of the audit trail: the per-route points must reconcile
    exactly back to the headline number."""
    a, b, carrier = _seed_two_routes(db_session)

    # Base period, then a day where A is +10% and B is -5%.
    db_session.add_all(
        [
            _clean_fare(a.id, carrier.id, BASE_DATE, 5000),
            _clean_fare(b.id, carrier.id, BASE_DATE, 4000),
            _clean_fare(a.id, carrier.id, QUERY_DATE, 5500),
            _clean_fare(b.id, carrier.id, QUERY_DATE, 3800),
        ]
    )
    # 100 * (0.6*1.10 + 0.4*0.95) = 104.0
    db_session.add(
        IndexValue(
            frequency="daily",
            period_date=QUERY_DATE,
            apix_value=104.0,
            base_period_date=BASE_DATE,
        )
    )
    db_session.commit()

    result = explain_index_value(db_session, QUERY_DATE)

    assert result["routes_included"] == 2
    assert result["weight_coverage"] == 1.0

    total_points = sum(r["contribution_points"] for r in result["routes"])
    assert round(total_points, 2) == result["apix_value"]

    by_route = {r["route"]: r for r in result["routes"]}
    assert by_route["DEL-BOM"]["price_relative"] == 1.1
    assert by_route["DEL-BOM"]["pct_change_vs_base"] == 10.0
    assert by_route["DEL-BLR"]["pct_change_vs_base"] == -5.0
    # Routes are ranked by how much they moved the index.
    assert result["routes"][0]["route"] == "DEL-BOM"


def test_missing_route_is_reported_as_excluded_and_weights_renormalise(db_session):
    a, b, carrier = _seed_two_routes(db_session)

    # Route B has a base observation but no data on the query date.
    db_session.add_all(
        [
            _clean_fare(a.id, carrier.id, BASE_DATE, 5000),
            _clean_fare(b.id, carrier.id, BASE_DATE, 4000),
            _clean_fare(a.id, carrier.id, QUERY_DATE, 5500),
        ]
    )
    db_session.add(
        IndexValue(
            frequency="daily", period_date=QUERY_DATE, apix_value=110.0, base_period_date=BASE_DATE
        )
    )
    db_session.commit()

    result = explain_index_value(db_session, QUERY_DATE)

    assert result["routes_included"] == 1
    assert result["weight_coverage"] == 0.6  # only route A's raw weight is covered
    # The surviving route absorbs the full basket after renormalisation.
    assert result["routes"][0]["weight_normalised"] == 1.0
    assert len(result["excluded_routes"]) == 1
    assert result["excluded_routes"][0]["route"] == "DEL-BLR"
    assert "no cleaned fare data" in result["excluded_routes"][0]["reason"]


def test_cleaning_stats_are_surfaced(db_session):
    a, _b, carrier = _seed_two_routes(db_session)
    db_session.add_all(
        [
            _clean_fare(a.id, carrier.id, BASE_DATE, 5000),
            _clean_fare(
                a.id, carrier.id, QUERY_DATE, 5500, n_obs=12, n_excluded_outliers=3, n_sold_out=2
            ),
        ]
    )
    db_session.add(
        IndexValue(
            frequency="daily", period_date=QUERY_DATE, apix_value=110.0, base_period_date=BASE_DATE
        )
    )
    db_session.commit()

    route = explain_index_value(db_session, QUERY_DATE)["routes"][0]
    assert route["n_obs"] == 12
    assert route["n_outliers_excluded"] == 3
    assert route["n_sold_out"] == 2
    assert route["carriers"] == ["6E"]


def test_unknown_date_returns_error(db_session):
    _seed_two_routes(db_session)
    result = explain_index_value(db_session, date(2099, 1, 1))
    assert "error" in result
