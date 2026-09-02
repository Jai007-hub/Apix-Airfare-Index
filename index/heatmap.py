"""Sector (route) x period average-fare matrix, for the dashboard heatmap."""
import statistics
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import AvailabilityStatus, CityPair, RawObservation, Source
from index.apix import month_start, route_daily_average, week_start


def _source_daily_averages(
    session: Session, start: date, end: date, source_name: str
) -> dict[date, dict[str, float]]:
    """Average fare per route per day, as seen on one booking portal.

    The cleaned table deliberately has no source column: cleaning collapses
    every portal quoting the same flight into one cell, so that a flight
    listed on six sites is not counted six times in the index. Filtering by
    portal therefore has to go back to the raw observations.

    Sold-out and cancelled rows are excluded, matching what cleaning does, so
    this stays within a couple of percent of the unfiltered view rather than
    jumping when a filter is applied. It does skip the MAD outlier pass,
    which is why the two are close but not identical.
    """
    rows = (
        session.query(
            CityPair.label,
            RawObservation.observation_date,
            func.avg(RawObservation.total_fare),
        )
        .join(CityPair, RawObservation.route_id == CityPair.id)
        .join(Source, RawObservation.source_id == Source.id)
        .filter(
            Source.name == source_name,
            RawObservation.observation_date >= start,
            RawObservation.observation_date <= end,
            RawObservation.availability_status == AvailabilityStatus.AVAILABLE,
            RawObservation.total_fare.isnot(None),
        )
        .group_by(CityPair.label, RawObservation.observation_date)
        .all()
    )

    out: dict[date, dict[str, float]] = {}
    for label, day, avg in rows:
        out.setdefault(day, {})[label] = avg
    return out


def sector_heatmap(
    session: Session,
    start: date,
    end: date,
    frequency: str = "weekly",
    source: str | None = None,
) -> dict:
    """Returns {"periods": [...], "routes": [...], "matrix": {route: {period_iso: avg_fare}}}.

    `source` optionally narrows the matrix to a single airline site or OTA
    portal by name (see /api/v1/sources); omitted, it averages across all of
    them via the cleaned table.
    """
    if frequency == "daily":
        period_fn = lambda d: d  # noqa: E731 -- one column per day, no bucketing
    elif frequency == "weekly":
        period_fn = week_start
    else:
        period_fn = month_start

    # One grouped query for a single portal, versus a scan per day for the
    # cleaned view -- worth the branch, since the filtered path would
    # otherwise be the slowest thing on the page.
    by_source = _source_daily_averages(session, start, end, source) if source else None

    per_period_route_fares: dict[date, dict[str, list[float]]] = {}
    current = start
    while current <= end:
        day_avgs = by_source.get(current, {}) if by_source is not None else route_daily_average(
            session, current
        )
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
        "source": source,
    }
