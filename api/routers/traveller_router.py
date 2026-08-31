from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from index.traveller import traveller_summary

router = APIRouter(prefix="/api/v1/traveller", tags=["traveller"])


@router.get("/{route_label}")
def get_traveller_summary(route_label: str, db: Session = Depends(get_db)):
    """Consumer-facing view of one route: what it typically costs, the cheapest
    booking window and what that saves, the cheapest carrier, and whether fares
    are rising or falling. Everything the phone view needs in one call."""
    result = traveller_summary(db, route_label.upper())
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
