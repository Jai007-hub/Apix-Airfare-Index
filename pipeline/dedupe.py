"""Upsert a single raw observation, keyed on the natural identity
(source, route, carrier, flight, fare_class, observation_date, departure_date).
Used by the live Scrapy item pipeline, where the same cell can legitimately be
re-scraped (e.g. a retried request) and must not create a duplicate row.
"""
from sqlalchemy.orm import Session

from db.models import RawObservation


def upsert_raw_observation(session: Session, fields: dict) -> RawObservation:
    existing = (
        session.query(RawObservation)
        .filter_by(
            source_id=fields["source_id"],
            route_id=fields["route_id"],
            carrier_id=fields.get("carrier_id"),
            flight_number=fields.get("flight_number"),
            fare_class=fields.get("fare_class"),
            observation_date=fields["observation_date"],
            departure_date=fields["departure_date"],
        )
        .one_or_none()
    )
    if existing is not None:
        for key, value in fields.items():
            setattr(existing, key, value)
        row = existing
    else:
        row = RawObservation(**fields)
        session.add(row)
    session.commit()
    return row
