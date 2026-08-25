from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Carrier, CityPair, CleanFare

router = APIRouter(prefix="/api/v1/fares", tags=["fares"])


@router.get("")
def get_fares(
    route: str | None = Query(None, description="Route label, e.g. DEL-BOM"),
    carrier: str | None = Query(None, description="Carrier code, e.g. 6E"),
    advance_window_days: int | None = None,
    start: date | None = None,
    end: date | None = None,
    limit: int = Query(1000, le=5000),
    db: Session = Depends(get_db),
):
    q = db.query(CleanFare, CityPair, Carrier).join(CityPair, CleanFare.route_id == CityPair.id).outerjoin(
        Carrier, CleanFare.carrier_id == Carrier.id
    )
    if route:
        q = q.filter(CityPair.label == route)
    if carrier:
        q = q.filter(Carrier.code == carrier)
    if advance_window_days:
        q = q.filter(CleanFare.advance_window_days == advance_window_days)
    if start:
        q = q.filter(CleanFare.observation_date >= start)
    if end:
        q = q.filter(CleanFare.observation_date <= end)

    rows = q.order_by(CleanFare.observation_date).limit(limit).all()
    return [
        {
            "observation_date": clean.observation_date,
            "route_label": route_row.label,
            "carrier_code": carrier_row.code if carrier_row else None,
            "advance_window_days": clean.advance_window_days,
            "median_base_fare": round(clean.median_base_fare, 2),
            "median_taxes": round(clean.median_taxes, 2),
            "median_total_fare": round(clean.median_total_fare, 2),
            "n_obs": clean.n_obs,
            "n_excluded_outliers": clean.n_excluded_outliers,
            "n_sold_out": clean.n_sold_out,
        }
        for clean, route_row, carrier_row in rows
    ]
