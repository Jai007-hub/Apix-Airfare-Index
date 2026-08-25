from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from index.heatmap import sector_heatmap

router = APIRouter(prefix="/api/v1/heatmap", tags=["heatmap"])


@router.get("")
def get_heatmap(
    start: date | None = None,
    end: date | None = None,
    frequency: str = Query("weekly", pattern="^(daily|weekly|monthly)$"),
    db: Session = Depends(get_db),
):
    end = end or date.today()
    start = start or (end - timedelta(days=60))
    return sector_heatmap(db, start, end, frequency)
