"""Lead-time (advance-purchase) elasticity: how average fare changes with
days-before-departure, per route, over a date range."""
import statistics
from datetime import date

from sqlalchemy.orm import Session

from db.models import CityPair, CleanFare
from scraper.config import ADVANCE_WINDOWS


def lead_time_curve(session: Session, start: date, end: date) -> dict[str, list[dict]]:
    """Returns {route_label: [{advance_window_days, avg_fare}, ...]} sorted by window."""
    routes = {r.id: r.label for r in session.query(CityPair).all()}
    rows = (
        session.query(CleanFare)
        .filter(CleanFare.observation_date >= start, CleanFare.observation_date <= end)
        .all()
    )

    buckets: dict[tuple[str, int], list[float]] = {}
    for row in rows:
        label = routes.get(row.route_id)
        if label is None:
            continue
        buckets.setdefault((label, row.advance_window_days), []).append(row.median_total_fare)

    result: dict[str, list[dict]] = {}
    for (label, window), fares in buckets.items():
        result.setdefault(label, []).append({"advance_window_days": window, "avg_fare": statistics.mean(fares)})

    for label in result:
        result[label].sort(key=lambda x: x["advance_window_days"])

    # Ensure every known window is represented (as null) for a stable chart x-axis.
    for label, curve in result.items():
        present = {c["advance_window_days"] for c in curve}
        for w in ADVANCE_WINDOWS:
            if w not in present:
                curve.append({"advance_window_days": w, "avg_fare": None})
        curve.sort(key=lambda x: x["advance_window_days"])

    return result
