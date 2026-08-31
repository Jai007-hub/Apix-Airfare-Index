"""Consumer-facing summary for a single route.

The dashboard proper answers an analyst's question -- how is the index
moving, does it track CPI. This answers a traveller's: what does this route
cost, when should I book, and which airline is cheapest. Same cleaned data,
different question, so it lives behind its own endpoint rather than making
the phone download the analyst payload and boil it down in the browser.

The problem statement names "cheapest advance-booking window per route" as a
traveller-facing insight, and the lead-time data already computed for the
elasticity curve answers it directly.
"""
import statistics
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import Carrier, CityPair, CleanFare

TREND_WINDOW_DAYS = 30


def _latest_observation_date(session: Session) -> date | None:
    return session.query(func.max(CleanFare.observation_date)).scalar()


def traveller_summary(session: Session, route_label: str) -> dict:
    route = session.query(CityPair).filter_by(label=route_label).one_or_none()
    if route is None:
        return {"error": f"Unknown route '{route_label}'."}

    latest = _latest_observation_date(session)
    if latest is None:
        return {"error": "No fare data available yet."}

    # A traveller cares about current prices, not the whole history. One
    # recent week smooths out day-to-day noise without going stale.
    recent_start = latest - timedelta(days=6)
    recent = (
        session.query(CleanFare)
        .filter(
            CleanFare.route_id == route.id,
            CleanFare.observation_date >= recent_start,
            CleanFare.observation_date <= latest,
        )
        .all()
    )
    if not recent:
        return {"error": f"No recent fares for {route_label}."}

    # Fare by booking window -- the "when should I book" answer.
    by_window: dict[int, list[float]] = {}
    for row in recent:
        by_window.setdefault(row.advance_window_days, []).append(row.median_total_fare)
    windows = [
        {"window_days": w, "fare": round(statistics.mean(v))}
        for w, v in sorted(by_window.items())
    ]

    cheapest = min(windows, key=lambda w: w["fare"])
    dearest = max(windows, key=lambda w: w["fare"])
    saving = dearest["fare"] - cheapest["fare"]

    # Cheapest airline on this route, at the cheapest booking window -- the
    # comparison only means something if the booking window is held constant.
    carrier_names = {c.id: (c.code, c.name) for c in session.query(Carrier).all()}
    by_carrier: dict[int, list[float]] = {}
    for row in recent:
        if row.carrier_id and row.advance_window_days == cheapest["window_days"]:
            by_carrier.setdefault(row.carrier_id, []).append(row.median_total_fare)
    carriers = sorted(
        (
            {
                "code": carrier_names[cid][0],
                "name": carrier_names[cid][1],
                "fare": round(statistics.mean(v)),
            }
            for cid, v in by_carrier.items()
            if cid in carrier_names
        ),
        key=lambda c: c["fare"],
    )

    # Direction of travel: this month against the one before.
    def _mean_over(start: date, end: date) -> float | None:
        rows = (
            session.query(CleanFare.median_total_fare)
            .filter(
                CleanFare.route_id == route.id,
                CleanFare.observation_date >= start,
                CleanFare.observation_date <= end,
            )
            .all()
        )
        return statistics.mean(r[0] for r in rows) if rows else None

    this_period = _mean_over(latest - timedelta(days=TREND_WINDOW_DAYS - 1), latest)
    prior_period = _mean_over(
        latest - timedelta(days=2 * TREND_WINDOW_DAYS - 1),
        latest - timedelta(days=TREND_WINDOW_DAYS),
    )
    trend_pct = (
        round((this_period - prior_period) / prior_period * 100, 1)
        if this_period and prior_period
        else None
    )

    return {
        "route": route.label,
        "origin": route.origin,
        "destination": route.destination,
        "as_of": latest,
        # What a typical booking costs, across the windows people actually use.
        "typical_fare": round(statistics.median(w["fare"] for w in windows)),
        "cheapest_window": cheapest,
        "dearest_window": dearest,
        "max_saving": saving,
        "max_saving_pct": round(saving / dearest["fare"] * 100, 1) if dearest["fare"] else 0.0,
        "windows": windows,
        "carriers": carriers,
        "trend_pct": trend_pct,
        "trend_direction": ("up" if trend_pct > 0 else "down") if trend_pct else "flat",
    }
