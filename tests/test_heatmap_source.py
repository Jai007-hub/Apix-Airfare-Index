from datetime import date, datetime

from db.models import (
    AvailabilityStatus,
    Carrier,
    CarrierType,
    CityPair,
    DataSourceType,
    RawObservation,
    Source,
    SourceType,
)
from index.heatmap import sector_heatmap

DAY = date(2026, 7, 15)


def _seed(db_session):
    route = CityPair(origin="DEL", destination="BOM", label="DEL-BOM", dgca_weight=0.22)
    carrier = Carrier(code="6E", name="IndiGo", carrier_type=CarrierType.LCC)
    airline_site = Source(
        name="indigo", source_type=SourceType.AIRLINE, base_url="https://www.goindigo.in"
    )
    ota = Source(
        name="makemytrip", source_type=SourceType.OTA, base_url="https://www.makemytrip.com"
    )
    db_session.add_all([route, carrier, airline_site, ota])
    db_session.commit()
    return route, carrier, airline_site, ota


# The dedupe grain includes flight_number, so each quote needs its own.
def _obs(route, carrier, source, total, flight="6E-100", status=AvailabilityStatus.AVAILABLE, day=DAY):
    return RawObservation(
        scraped_at=datetime.combine(day, datetime.min.time()),
        observation_date=day,
        source_id=source.id,
        route_id=route.id,
        carrier_id=carrier.id,
        flight_number=flight,
        departure_date=day,
        advance_window_days=15,
        fare_class="Economy",
        base_fare=total * 0.95 if total else None,
        taxes=total * 0.05 if total else None,
        udf=0,
        convenience_fee=0,
        total_fare=total,
        availability_status=status,
        data_source_type=DataSourceType.SYNTHETIC_FALLBACK,
    )


def test_filtering_by_portal_shows_only_that_portal_s_fares(db_session):
    """The whole point of the filter: an OTA's markup is invisible while every
    portal is averaged together."""
    route, carrier, airline_site, ota = _seed(db_session)
    db_session.add_all(
        [
            _obs(route, carrier, airline_site, 5000, flight="6E-100"),
            _obs(route, carrier, airline_site, 5200, flight="6E-200"),
            _obs(route, carrier, ota, 6000, flight="6E-100"),
            _obs(route, carrier, ota, 6400, flight="6E-200"),
        ]
    )
    db_session.commit()

    airline_view = sector_heatmap(db_session, DAY, DAY, "daily", source="indigo")
    ota_view = sector_heatmap(db_session, DAY, DAY, "daily", source="makemytrip")

    assert airline_view["matrix"]["DEL-BOM"]["2026-07-15"] == 5100
    assert ota_view["matrix"]["DEL-BOM"]["2026-07-15"] == 6200


def test_sold_out_quotes_do_not_drag_the_average(db_session):
    """A sold-out listing carries no price anyone can pay, so counting it
    would report a fare that was never purchasable."""
    route, carrier, airline_site, _ = _seed(db_session)
    db_session.add_all(
        [
            _obs(route, carrier, airline_site, 5000, flight="6E-100"),
            _obs(
                route,
                carrier,
                airline_site,
                99999,
                flight="6E-200",
                status=AvailabilityStatus.SOLD_OUT,
            ),
        ]
    )
    db_session.commit()

    view = sector_heatmap(db_session, DAY, DAY, "daily", source="indigo")

    assert view["matrix"]["DEL-BOM"]["2026-07-15"] == 5000


def test_the_response_says_which_portal_it_is_for(db_session):
    """Without this the caller cannot tell a filtered matrix from an
    unfiltered one, and would caption it wrongly."""
    _seed(db_session)

    assert sector_heatmap(db_session, DAY, DAY, "daily")["source"] is None
    assert sector_heatmap(db_session, DAY, DAY, "daily", source="indigo")["source"] == "indigo"


def test_a_portal_with_no_fares_yields_an_empty_matrix_not_an_error(db_session):
    """A portal we track but that returned nothing in this window is a real
    state -- blocked by anti-bot measures, say -- and should render as an
    empty grid rather than blowing up."""
    route, carrier, airline_site, _ = _seed(db_session)
    db_session.add(_obs(route, carrier, airline_site, 5000))
    db_session.commit()

    view = sector_heatmap(db_session, DAY, DAY, "daily", source="makemytrip")

    assert view["routes"] == []
    assert view["matrix"] == {}
