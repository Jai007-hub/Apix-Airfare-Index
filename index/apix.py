"""APIx index construction.

Methodology (documented in docs/VALIDATION.md):
  1. For each route and day, take the average of that day's CleanFare
     median_total_fare across all carriers and advance-purchase windows --
     a single representative daily fare per route.
  2. Each route's *base period* is the earliest day it has data; its daily
     price relative = today's average / base-period average.
  3. APIx(day) = 100 * sum_over_routes( basket_weight * price_relative ),
     i.e. a fixed-basket (Laspeyres-style) weighted average of route price
     relatives, mirroring how CPI sub-indices are aggregated.
  4. Routes missing data on a given day are dropped from that day's
     computation and the remaining weights are renormalized to sum to 1, so
     a single scraping gap doesn't produce a missing index value.
  5. Weekly/monthly indices are the mean of the daily index values falling
     in that ISO week / calendar month.
"""
import json
import statistics
from datetime import date, timedelta

from sqlalchemy.orm import Session

from db.models import CityPair, CleanFare, IndexValue
from index.weights import get_active_weights


def route_daily_average(session: Session, observation_date: date) -> dict[str, float]:
    rows = session.query(CleanFare).filter_by(observation_date=observation_date).all()
    if not rows:
        return {}
    by_route: dict[int, list[float]] = {}
    for r in rows:
        by_route.setdefault(r.route_id, []).append(r.median_total_fare)

    route_id_to_label = {r.id: r.label for r in session.query(CityPair).all()}
    return {
        route_id_to_label[route_id]: statistics.mean(fares)
        for route_id, fares in by_route.items()
        if route_id in route_id_to_label
    }


def compute_base_period_averages(session: Session, start: date, end: date) -> dict[str, tuple[date, float]]:
    """For each route, the (date, avg_fare) of the earliest day in [start, end]
    that route has CleanFare data."""
    bases: dict[str, tuple[date, float]] = {}
    current = start
    while current <= end:
        day_avgs = route_daily_average(session, current)
        for label, avg_fare in day_avgs.items():
            if label not in bases:
                bases[label] = (current, avg_fare)
        current += timedelta(days=1)
    return bases


def compute_daily_index(
    day_avgs: dict[str, float],
    weights: dict[str, float],
    base_averages: dict[str, tuple[date, float]],
) -> tuple[float, dict[str, float]] | None:
    """Returns (index_value, {route_label: relative}) or None if no route has data."""
    contributions: dict[str, float] = {}
    weight_sum = 0.0
    for label, weight in weights.items():
        if label not in day_avgs or label not in base_averages:
            continue
        base_date, base_avg = base_averages[label]
        if base_avg == 0:
            continue
        relative = day_avgs[label] / base_avg
        contributions[label] = relative
        weight_sum += weight

    if weight_sum == 0:
        return None

    index_value = 100.0 * sum(weights[label] * rel for label, rel in contributions.items()) / weight_sum
    return index_value, contributions


def build_daily_index_series(session: Session, start: date, end: date) -> list[dict]:
    weights = get_active_weights(session)
    base_averages = compute_base_period_averages(session, start, end)

    series = []
    current = start
    while current <= end:
        day_avgs = route_daily_average(session, current)
        result = compute_daily_index(day_avgs, weights, base_averages)
        if result is not None:
            index_value, breakdown = result
            series.append({"period_date": current, "apix_value": index_value, "route_breakdown": breakdown})
        current += timedelta(days=1)

    return series


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())  # Monday


def month_start(d: date) -> date:
    return d.replace(day=1)


def aggregate_series(daily_series: list[dict], period_fn) -> list[dict]:
    buckets: dict[date, list[float]] = {}
    for entry in daily_series:
        key = period_fn(entry["period_date"])
        buckets.setdefault(key, []).append(entry["apix_value"])
    return [
        {"period_date": period, "apix_value": statistics.mean(values)}
        for period, values in sorted(buckets.items())
    ]


def persist_index_values(session: Session, frequency: str, series: list[dict], base_period_date: date) -> int:
    written = 0
    for entry in series:
        existing = (
            session.query(IndexValue)
            .filter_by(frequency=frequency, period_date=entry["period_date"])
            .one_or_none()
        )
        breakdown_json = json.dumps(entry.get("route_breakdown", {}))
        if existing is not None:
            existing.apix_value = entry["apix_value"]
            existing.base_period_date = base_period_date
            existing.route_breakdown = breakdown_json
        else:
            session.add(
                IndexValue(
                    frequency=frequency,
                    period_date=entry["period_date"],
                    apix_value=entry["apix_value"],
                    base_period_date=base_period_date,
                    route_breakdown=breakdown_json,
                )
            )
        written += 1
    session.commit()
    return written


def build_and_persist_all(session: Session, start: date, end: date) -> dict[str, int]:
    daily = build_daily_index_series(session, start, end)
    if not daily:
        return {"daily": 0, "weekly": 0, "monthly": 0}
    weekly = aggregate_series(daily, week_start)
    monthly = aggregate_series(daily, month_start)

    base_period_date = start
    counts = {
        "daily": persist_index_values(session, "daily", daily, base_period_date),
        "weekly": persist_index_values(session, "weekly", weekly, base_period_date),
        "monthly": persist_index_values(session, "monthly", monthly, base_period_date),
    }
    return counts
