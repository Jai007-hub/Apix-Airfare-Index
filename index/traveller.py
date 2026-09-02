"""Consumer-facing summaries.

The dashboard proper answers an analyst's question -- how is the index
moving, does it track CPI. This answers a traveller's: what does this route
cost, when should I book, which airline is cheapest, and what am I actually
paying for. Same cleaned data, different question, so it lives behind its own
endpoint rather than making the phone download the analyst payload and boil
it down in the browser.

The problem statement names "cheapest advance-booking window per route" as a
traveller-facing insight, and the lead-time data already computed for the
elasticity curve answers it directly.
"""
import calendar
import statistics
from datetime import date, timedelta

from sqlalchemy import Integer, func
from sqlalchemy.orm import Session

from db.models import Carrier, CityPair, CleanFare

TREND_WINDOW_DAYS = 30
# One recent week smooths day-to-day noise without going stale.
RECENT_WINDOW_DAYS = 7


def _latest_observation_date(session: Session) -> date | None:
    return session.query(func.max(CleanFare.observation_date)).scalar()


def traveller_summary(session: Session, route_label: str) -> dict:
    route = session.query(CityPair).filter_by(label=route_label).one_or_none()
    if route is None:
        return {"error": f"Unknown route '{route_label}'."}

    latest = _latest_observation_date(session)
    if latest is None:
        return {"error": "No fare data available yet."}

    recent_start = latest - timedelta(days=RECENT_WINDOW_DAYS - 1)
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

    # Fare by booking window -- the "when should I book" answer. Sold-out rate
    # rides along because it is the other half of the same decision: leaving it
    # late costs more *and* more often leaves nothing left to buy.
    by_window: dict[int, list[CleanFare]] = {}
    for row in recent:
        by_window.setdefault(row.advance_window_days, []).append(row)

    windows = []
    for w, rows in sorted(by_window.items()):
        quotes = sum(r.n_obs for r in rows)
        sold_out = sum(r.n_sold_out for r in rows)
        windows.append(
            {
                "window_days": w,
                "fare": round(statistics.mean(r.median_total_fare for r in rows)),
                "low": round(min(r.min_total_fare for r in rows)),
                "high": round(max(r.max_total_fare for r in rows)),
                "sold_out_pct": round(sold_out / quotes * 100, 1) if quotes else 0.0,
            }
        )

    cheapest = min(windows, key=lambda w: w["fare"])
    dearest = max(windows, key=lambda w: w["fare"])
    saving = dearest["fare"] - cheapest["fare"]

    # What the cheapest fare is actually made of. Each cleaned row's components
    # come from a single quote, so averaging them component-wise over the same
    # rows gives a split that still sums to the fare shown above.
    at_cheapest = by_window[cheapest["window_days"]]
    breakdown = {
        "base_fare": round(statistics.mean(r.median_base_fare for r in at_cheapest)),
        "taxes": round(statistics.mean(r.median_taxes for r in at_cheapest)),
        "udf": round(statistics.mean(r.median_udf for r in at_cheapest)),
        "convenience_fee": round(
            statistics.mean(r.median_convenience_fee for r in at_cheapest)
        ),
    }
    # Rounding four lines independently can leave the split a rupee or two off
    # the fare printed above it. A breakdown that doesn't add up reads as a
    # bug to anyone who checks, so the largest line absorbs the residual.
    breakdown["base_fare"] += cheapest["fare"] - sum(breakdown.values())

    # Airline ranking per booking window. Ranking across mixed windows would
    # compare booking timing rather than carriers, so each list holds its
    # window constant and the caller picks which window to look at.
    carrier_names = {c.id: (c.code, c.name) for c in session.query(Carrier).all()}

    def _rank_carriers(rows_: list[CleanFare]) -> list[dict]:
        by_carrier: dict[int, list[float]] = {}
        for row in rows_:
            if row.carrier_id:
                by_carrier.setdefault(row.carrier_id, []).append(row.median_total_fare)
        return sorted(
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

    carriers_by_window = {w: _rank_carriers(rows) for w, rows in sorted(by_window.items())}
    carriers = carriers_by_window[cheapest["window_days"]]

    # Direction of travel: this month against the one before.
    def _mean_over(start: date, end: date) -> float | None:
        return (
            session.query(func.avg(CleanFare.median_total_fare))
            .filter(
                CleanFare.route_id == route.id,
                CleanFare.observation_date >= start,
                CleanFare.observation_date <= end,
            )
            .scalar()
        )

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
        "fare_breakdown": breakdown,
        "carriers": carriers,
        "carriers_by_window": carriers_by_window,
        "months": monthly_seasonality(session, route.id),
        "trend_pct": trend_pct,
        "trend_direction": ("up" if trend_pct > 0 else "down") if trend_pct else "flat",
    }


def monthly_seasonality(session: Session, route_id: int) -> list[dict]:
    """Average fare per calendar month, pooled across every year on record --
    the "when is it cheap to fly this route" answer.

    Pooling by calendar month rather than by (year, month) is what makes this
    a seasonal statement rather than a history: someone planning October wants
    every October we have, not merely the most recent one.
    """
    rows = (
        session.query(
            func.cast(func.strftime("%m", CleanFare.observation_date), Integer),
            func.avg(CleanFare.median_total_fare),
        )
        .filter(CleanFare.route_id == route_id)
        .group_by(func.strftime("%m", CleanFare.observation_date))
        .all()
    )
    return [
        {"month": int(m), "name": calendar.month_abbr[int(m)], "fare": round(avg)}
        for m, avg in sorted(rows, key=lambda r: int(r[0]))
    ]


def route_leaderboard(session: Session) -> list[dict]:
    """Every tracked sector at its best current fare, cheapest first -- the
    "where can I go cheaply" strip.

    One grouped query rather than ten full summaries, because this renders
    above the fold on a phone.
    """
    latest = _latest_observation_date(session)
    if latest is None:
        return []
    recent_start = latest - timedelta(days=RECENT_WINDOW_DAYS - 1)

    per_window = (
        session.query(
            CleanFare.route_id,
            func.avg(CleanFare.median_total_fare).label("fare"),
        )
        .filter(
            CleanFare.observation_date >= recent_start,
            CleanFare.observation_date <= latest,
        )
        .group_by(CleanFare.route_id, CleanFare.advance_window_days)
        .all()
    )

    # The cheapest booking window is the one a traveller would actually pick,
    # so a sector is listed at its best price, not its average one.
    best: dict[int, float] = {}
    for route_id, fare in per_window:
        if route_id not in best or fare < best[route_id]:
            best[route_id] = fare

    routes = {r.id: r for r in session.query(CityPair).filter_by(is_active=True).all()}
    return sorted(
        (
            {
                "route": routes[rid].label,
                "origin": routes[rid].origin,
                "destination": routes[rid].destination,
                "best_fare": round(fare),
            }
            for rid, fare in best.items()
            if rid in routes
        ),
        key=lambda r: r["best_fare"],
    )
