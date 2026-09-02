from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Source
from index.heatmap import sector_heatmap

router = APIRouter(prefix="/api/v1/heatmap", tags=["heatmap"])


@router.get("")
def get_heatmap(
    start: date | None = None,
    end: date | None = None,
    frequency: str = Query("weekly", pattern="^(daily|weekly|monthly)$"),
    source: str | None = Query(
        None,
        description="Narrow to one booking portal by name, e.g. 'makemytrip' or "
        "'indigo'. Omitted, the matrix averages across every portal.",
    ),
    db: Session = Depends(get_db),
):
    end = end or date.today()
    start = start or (end - timedelta(days=60))

    # An unknown name would silently return an empty matrix, which reads as
    # "no fares on this route" rather than "you asked for a portal we do not
    # track" -- so say which it is.
    if source is not None:
        known = {s.name for s in db.query(Source).all()}
        if source not in known:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown source '{source}'. Known sources: {sorted(known)}",
            )

    return sector_heatmap(db, start, end, frequency, source)
