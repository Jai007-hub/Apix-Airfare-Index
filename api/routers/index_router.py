from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import IndexValue
from index.explain import explain_index_value

router = APIRouter(prefix="/api/v1/index", tags=["index"])


@router.get("")
def get_index(
    frequency: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(IndexValue).filter(IndexValue.frequency == frequency)
    if start:
        q = q.filter(IndexValue.period_date >= start)
    if end:
        q = q.filter(IndexValue.period_date <= end)
    rows = q.order_by(IndexValue.period_date).all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No '{frequency}' index values found for the given range")
    return [{"period_date": r.period_date, "apix_value": round(r.apix_value, 3)} for r in rows]


@router.get("/explain")
def explain_index(
    period_date: date = Query(..., description="The daily index date to decompose, YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """Full audit trail for one daily APIx value: which routes contributed, how
    many index points each added, which were excluded and why, and whether the
    underlying fare quotes were live-scraped or synthetic."""
    result = explain_index_value(db, period_date)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
