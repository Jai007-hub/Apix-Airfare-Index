from datetime import date

from db.models import Carrier, CarrierType, CityPair, CleanFare
from index.elasticity import lead_time_curve
from scraper.config import ADVANCE_WINDOWS


def test_lead_time_curve_fills_missing_windows_with_none(db_session):
    route = CityPair(origin="DEL", destination="BOM", label="DEL-BOM", dgca_weight=0.22)
    carrier = Carrier(code="6E", name="IndiGo", carrier_type=CarrierType.LCC)
    db_session.add_all([route, carrier])
    db_session.commit()

    obs_date = date(2026, 7, 1)
    db_session.add(
        CleanFare(
            observation_date=obs_date, route_id=route.id, carrier_id=carrier.id, advance_window_days=1,
            median_base_fare=9000, median_taxes=450, median_total_fare=10000, min_total_fare=9500,
            max_total_fare=10500, n_obs=5, n_excluded_outliers=0, n_sold_out=0,
        )
    )
    db_session.add(
        CleanFare(
            observation_date=obs_date, route_id=route.id, carrier_id=carrier.id, advance_window_days=45,
            median_base_fare=4000, median_taxes=200, median_total_fare=4500, min_total_fare=4300,
            max_total_fare=4700, n_obs=5, n_excluded_outliers=0, n_sold_out=0,
        )
    )
    db_session.commit()

    curve = lead_time_curve(db_session, obs_date, obs_date)
    windows_present = [c["advance_window_days"] for c in curve["DEL-BOM"]]
    assert windows_present == sorted(ADVANCE_WINDOWS)

    by_window = {c["advance_window_days"]: c["avg_fare"] for c in curve["DEL-BOM"]}
    assert by_window[1] == 10000
    assert by_window[45] == 4500
    assert by_window[7] is None  # no data for this window
