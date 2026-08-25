"""Basket weights for index construction, sourced from CityPair.dgca_weight
(see scraper/config.py for the underlying DGCA-traffic-share figures)."""
from sqlalchemy.orm import Session

from db.models import CityPair


def get_active_weights(session: Session) -> dict[str, float]:
    """Returns {route_label: normalized_weight} for active routes, summing to 1.0."""
    routes = session.query(CityPair).filter_by(is_active=True).all()
    total = sum(r.dgca_weight for r in routes)
    if total == 0:
        return {}
    return {r.label: r.dgca_weight / total for r in routes}
