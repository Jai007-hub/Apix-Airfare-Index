from datetime import date, datetime

from db.models import AvailabilityStatus, Carrier, CarrierType, CityPair, DataSourceType, RawObservation, Source, SourceType
from pipeline.clean import _mad_inlier_mask, clean_day


def test_mad_inlier_mask_flags_extreme_outlier():
    values = [5000, 5100, 4950, 5050, 25000]  # last one is a clear outlier
    mask = _mad_inlier_mask(values)
    assert mask == [True, True, True, True, False]


def test_mad_inlier_mask_small_group_keeps_everything():
    assert _mad_inlier_mask([100, 999999]) == [True, True]


def _seed_dims(session):
    route = CityPair(origin="DEL", destination="BOM", label="DEL-BOM", dgca_weight=0.22)
    carrier = Carrier(code="6E", name="IndiGo", carrier_type=CarrierType.LCC)
    source = Source(name="indigo", source_type=SourceType.AIRLINE, base_url="https://x")
    session.add_all([route, carrier, source])
    session.commit()
    return route, carrier, source


def _raw(route, carrier, source, obs_date, total_fare, status=AvailabilityStatus.AVAILABLE, window=1, flight_number="6E101"):
    return RawObservation(
        scraped_at=datetime.combine(obs_date, datetime.min.time()),
        observation_date=obs_date,
        source_id=source.id,
        route_id=route.id,
        carrier_id=carrier.id,
        flight_number=flight_number,
        departure_date=obs_date,
        advance_window_days=window,
        fare_class="Economy",
        base_fare=total_fare * 0.95 if total_fare else None,
        taxes=total_fare * 0.05 if total_fare else None,
        udf=0,
        convenience_fee=0,
        total_fare=total_fare,
        availability_status=status,
        data_source_type=DataSourceType.SYNTHETIC_FALLBACK,
    )


def test_clean_day_excludes_outliers_and_sold_out(db_session):
    route, carrier, source = _seed_dims(db_session)
    obs_date = date(2026, 7, 1)
    fares = [5000, 5100, 4950, 5050, 25000]  # one outlier
    for i, f in enumerate(fares):
        db_session.add(_raw(route, carrier, source, obs_date, f, flight_number=f"6E10{i}"))
    db_session.add(_raw(route, carrier, source, obs_date, None, status=AvailabilityStatus.SOLD_OUT, flight_number="6E999"))
    db_session.commit()

    n_written = clean_day(db_session, obs_date)
    assert n_written == 1

    from db.models import CleanFare

    clean = db_session.query(CleanFare).one()
    assert clean.n_obs == 4  # 5 available minus 1 outlier
    assert clean.n_excluded_outliers == 1
    assert clean.n_sold_out == 1
    assert 4900 < clean.median_total_fare < 5100


def test_clean_day_skips_empty_groups(db_session):
    _seed_dims(db_session)
    n_written = clean_day(db_session, date(2026, 7, 1))
    assert n_written == 0


def test_all_four_fare_components_survive_cleaning(db_session):
    """The problem statement requires base fare separated from taxes, UDF and
    convenience charges. They were previously split on the raw observation but
    dropped at the cleaning stage, so the API and index -- which both read
    CleanFare -- could never see UDF or the convenience fee."""
    route, carrier, source = _seed_dims(db_session)
    obs_date = date(2026, 7, 1)

    # Deliberately heterogeneous convenience fees, as different sources really
    # do charge: taking an independent median per component would pull them
    # from different quotes and they would stop adding up.
    quotes = [
        {"base": 4000, "tax": 200, "udf": 1030, "conv": 0},
        {"base": 4500, "tax": 225, "udf": 1030, "conv": 300},
        {"base": 5000, "tax": 250, "udf": 1030, "conv": 149},
    ]
    for i, q in enumerate(quotes):
        total = q["base"] + q["tax"] + q["udf"] + q["conv"]
        row = _raw(route, carrier, source, obs_date, total, flight_number=f"6E20{i}")
        row.base_fare, row.taxes = q["base"], q["tax"]
        row.udf, row.convenience_fee = q["udf"], q["conv"]
        db_session.add(row)
    db_session.commit()

    clean_day(db_session, obs_date)

    from db.models import CleanFare

    clean = db_session.query(CleanFare).one()
    # The four components must reconcile exactly to the total -- they all come
    # from the one quote sitting at the median total fare.
    assert round(
        clean.median_base_fare
        + clean.median_taxes
        + clean.median_udf
        + clean.median_convenience_fee,
        2,
    ) == clean.median_total_fare
    # And that total is a real observed quote, not a blend.
    assert clean.median_total_fare in {q["base"] + q["tax"] + q["udf"] + q["conv"] for q in quotes}


def test_fare_classes_are_not_averaged_together(db_session):
    """Economy and Flexi Economy are different products on the same flight;
    collapsing them into one median would invent a fare nobody can buy."""
    route, carrier, source = _seed_dims(db_session)
    obs_date = date(2026, 7, 1)

    economy = _raw(route, carrier, source, obs_date, 5000, flight_number="6E301")
    flexi = _raw(route, carrier, source, obs_date, 9000, flight_number="6E302")
    flexi.fare_class = "Flexi Economy"
    db_session.add_all([economy, flexi])
    db_session.commit()

    clean_day(db_session, obs_date)

    from db.models import CleanFare

    rows = {c.fare_class: c for c in db_session.query(CleanFare).all()}
    assert set(rows) == {"Economy", "Flexi Economy"}
    assert rows["Economy"].median_total_fare == 5000
    assert rows["Flexi Economy"].median_total_fare == 9000


def test_cancelled_flights_are_excluded_like_sold_out(db_session):
    """Cancelled is a distinct state from sold-out but must equally never
    contribute a price -- it is counted, not averaged."""
    route, carrier, source = _seed_dims(db_session)
    obs_date = date(2026, 7, 1)

    db_session.add(_raw(route, carrier, source, obs_date, 5000, flight_number="6E401"))
    db_session.add(
        _raw(
            route, carrier, source, obs_date, None,
            status=AvailabilityStatus.CANCELLED, flight_number="6E402",
        )
    )
    db_session.commit()

    clean_day(db_session, obs_date)

    from db.models import CleanFare

    clean = db_session.query(CleanFare).one()
    assert clean.n_obs == 1
    assert clean.n_sold_out == 1  # counts unavailable flights of either reason
    assert clean.median_total_fare == 5000
