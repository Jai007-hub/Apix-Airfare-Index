"""Sector (route) x period average-fare matrix, for the dashboard heatmap."""
import statistics
from datetime import date, timedelta

from sqlalchemy.orm import Session

from index.apix import month_start, route_daily_average, week_start


def sector_heatmap(session: Session, start: date, end: date, frequency: str = "weekly") -> dict:
    """Returns {"periods": [date, ...], "routes": [label, ...], "matrix": {route: {period_iso: avg_fare}}}."""
    if frequency == "daily":
        period_fn = lambda d: d  # noqa: E731 -- one column per day, no bucketing
    elif frequency == "weekly":
        period_fn = week_start
    else:
        period_fn = month_start

    per_period_route_fares: dict[date, dict[str, list[float]]] = {}
    current = start
    while current <= end:
        day_avgs = route_daily_average(session, current)
        period = period_fn(current)
        bucket = per_period_route_fares.setdefault(period, {})
        for label, fare in day_avgs.items():
            bucket.setdefault(label, []).append(fare)
        current += timedelta(days=1)

    routes = sorted({label for bucket in per_period_route_fares.values() for label in bucket})
    periods = sorted(per_period_route_fares.keys())

    matrix: dict[str, dict[str, float]] = {label: {} for label in routes}
    for period in periods:
        for label in routes:
            fares = per_period_route_fares[period].get(label)
            if fares:
                matrix[label][period.isoformat()] = round(statistics.mean(fares), 2)

    return {
        "periods": [p.isoformat() for p in periods],
        "routes": routes,
        "matrix": matrix,
    }
