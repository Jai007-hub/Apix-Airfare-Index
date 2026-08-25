from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from index.elasticity import lead_time_curve

router = APIRouter(prefix="/api/v1/elasticity", tags=["elasticity"])


@router.get("")
def get_elasticity(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
):
    end = end or date.today()
    start = start or (end - timedelta(days=60))
    return lead_time_curve(db, start, end)
