"""Seed and look up the reference/dimension tables (CityPair, Carrier, Source)
from scraper/config.py. Idempotent -- safe to call on every run."""
from sqlalchemy.orm import Session

from db.models import Carrier, CityPair, Source
from scraper import config


class DimensionLookup:
    def __init__(self, route_ids: dict[str, int], carrier_ids: dict[str, int], source_ids: dict[str, int]):
        self.route_ids = route_ids
        self.carrier_ids = carrier_ids
        self.source_ids = source_ids


def ensure_dimensions(session: Session) -> DimensionLookup:
    route_ids: dict[str, int] = {}
    for r in config.ROUTES:
        row = session.query(CityPair).filter_by(label=r.label).one_or_none()
        if row is None:
            row = CityPair(origin=r.origin, destination=r.destination, label=r.label, dgca_weight=r.dgca_weight)
            session.add(row)
            session.flush()
        else:
            row.dgca_weight = r.dgca_weight
        route_ids[r.label] = row.id

    carrier_ids: dict[str, int] = {}
    for c in config.CARRIERS:
        row = session.query(Carrier).filter_by(code=c.code).one_or_none()
        if row is None:
            row = Carrier(code=c.code, name=c.name, carrier_type=c.carrier_type)
            session.add(row)
            session.flush()
        carrier_ids[c.code] = row.id

    source_ids: dict[str, int] = {}
    for s in config.SOURCES:
        row = session.query(Source).filter_by(name=s.name).one_or_none()
        if row is None:
            row = Source(name=s.name, source_type=s.source_type, base_url=s.base_url)
            session.add(row)
            session.flush()
        source_ids[s.name] = row.id

    session.commit()
    return DimensionLookup(route_ids, carrier_ids, source_ids)
