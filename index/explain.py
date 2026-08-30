"""Audit trail for a single index value.

The index is a weighted average of per-route price relatives, so any daily
APIx number can be fully decomposed back into the routes that produced it.
This module rebuilds that decomposition on demand -- which routes were
included, what each contributed in index points, which were dropped and why,
and whether the underlying fares were live-scraped or synthetic.

That auditability is the point: a statistical agency evaluating this series
needs to be able to ask "why is this number what it is" and get an exact
answer, not a chart.
"""
from datetime import date

from sqlalchemy.orm import Session

from db.models import Carrier, CityPair, CleanFare, DataSourceType, IndexValue, RawObservation
from index.apix import compute_base_period_averages, route_daily_average
from index.weights import get_active_weights


def explain_index_value(session: Session, period_date: date) -> dict:
    """Decomposes the daily APIx for `period_date` into per-route contributions."""
    index_row = (
        session.query(IndexValue)
        .filter_by(frequency="daily", period_date=period_date)
        .one_or_none()
    )
    if index_row is None:
        return {"error": f"No daily index value computed for {period_date.isoformat()}."}

    base_start = index_row.base_period_date
    weights = get_active_weights(session)
    day_avgs = route_daily_average(session, period_date)
    base_averages = compute_base_period_averages(session, base_start, period_date)

    # Only routes with data both today and at the base period take part; the
    # rest are dropped and the surviving weights renormalised (index/apix.py).
    included = [
        label
        for label in weights
        if label in day_avgs and label in base_averages and base_averages[label][1] != 0
    ]
    weight_sum = sum(weights[label] for label in included)

    label_to_id = {r.label: r.id for r in session.query(CityPair).all()}
    carrier_by_id = {c.id: c.code for c in session.query(Carrier).all()}

    # Per-route cleaning stats for the day, so the panel can show how many raw
    # quotes stood behind each route and how many were filtered out.
    clean_rows = session.query(CleanFare).filter_by(observation_date=period_date).all()
    stats: dict[int, dict] = {}
    for row in clean_rows:
        s = stats.setdefault(
            row.route_id, {"n_obs": 0, "n_outliers": 0, "n_sold_out": 0, "carriers": set()}
        )
        s["n_obs"] += row.n_obs
        s["n_outliers"] += row.n_excluded_outliers
        s["n_sold_out"] += row.n_sold_out
        if row.carrier_id in carrier_by_id:
            s["carriers"].add(carrier_by_id[row.carrier_id])

    # Provenance: were the raw quotes behind this day live-scraped or synthetic?
    provenance_rows = (
        session.query(RawObservation.route_id, RawObservation.data_source_type)
        .filter(RawObservation.observation_date == period_date)
        .all()
    )
    provenance: dict[int, dict[str, int]] = {}
    for route_id, source_type in provenance_rows:
        key = "live" if source_type == DataSourceType.LIVE else "synthetic"
        provenance.setdefault(route_id, {"live": 0, "synthetic": 0})[key] += 1

    routes = []
    for label in included:
        route_id = label_to_id.get(label)
        base_date, base_avg = base_averages[label]
        today_avg = day_avgs[label]
        relative = today_avg / base_avg
        weight_raw = weights[label]
        weight_norm = weight_raw / weight_sum if weight_sum else 0.0
        st = stats.get(route_id, {})
        prov = provenance.get(route_id, {"live": 0, "synthetic": 0})

        routes.append(
            {
                "route": label,
                "weight": round(weight_raw, 4),
                "weight_normalised": round(weight_norm, 4),
                "base_date": base_date,
                "base_fare": round(base_avg, 2),
                "current_fare": round(today_avg, 2),
                "price_relative": round(relative, 4),
                "pct_change_vs_base": round((relative - 1) * 100, 2),
                # What this route added to the headline number, in index points.
                "contribution_points": round(100.0 * weight_norm * relative, 3),
                "n_obs": st.get("n_obs", 0),
                "n_outliers_excluded": st.get("n_outliers", 0),
                "n_sold_out": st.get("n_sold_out", 0),
                "carriers": sorted(st.get("carriers", set())),
                "live_observations": prov["live"],
                "synthetic_observations": prov["synthetic"],
            }
        )

    routes.sort(key=lambda r: r["contribution_points"], reverse=True)

    excluded = [
        {
            "route": label,
            "weight": round(weights[label], 4),
            "reason": (
                "no cleaned fare data for this date"
                if label not in day_avgs
                else "no base-period observation to index against"
            ),
        }
        for label in weights
        if label not in included
    ]

    total_live = sum(r["live_observations"] for r in routes)
    total_synthetic = sum(r["synthetic_observations"] for r in routes)
    total_obs = total_live + total_synthetic

    return {
        "period_date": period_date,
        "frequency": "daily",
        "apix_value": round(index_row.apix_value, 3),
        "base_period_date": base_start,
        "routes_included": len(routes),
        "routes_total": len(weights),
        "weight_coverage": round(weight_sum, 4),
        "routes": routes,
        "excluded_routes": excluded,
        "provenance": {
            "live_observations": total_live,
            "synthetic_observations": total_synthetic,
            "pct_live": round(100.0 * total_live / total_obs, 1) if total_obs else 0.0,
        },
    }
