from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Source

router = APIRouter(prefix="/api/v1/sources", tags=["sources"])


@router.get("")
def list_sources(db: Session = Depends(get_db)):
    """The portals APIx scrapes, split into airline sites and OTA aggregators.

    Drives the heatmap's filters, so the dropdowns can never offer a portal
    the database has no fares for.
    """
    return [
        {
            "name": s.name,
            "source_type": s.source_type.value,
            "base_url": s.base_url,
        }
        for s in sorted(db.query(Source).all(), key=lambda s: (s.source_type.value, s.name))
    ]
