from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from index.traveller import route_leaderboard, traveller_summary

router = APIRouter(prefix="/api/v1/traveller", tags=["traveller"])


@router.get("")
def get_route_leaderboard(db: Session = Depends(get_db)):
    """Every tracked sector at its best current fare, cheapest first."""
    return route_leaderboard(db)


@router.get("/{route_label}")
def get_traveller_summary(
    route_label: str,
    carrier: str | None = Query(
        None,
        description="Airline code (6E, AI, SG, QP, IX). Narrows the fares, the "
        "booking-window table and the fare split to that airline. Omitted, they "
        "are means across all airlines.",
    ),
    db: Session = Depends(get_db),
):
    """Consumer-facing view of one route: what it typically costs, the cheapest
    booking window and what that saves, how the fare splits, which airline is
    cheapest, when in the year it is cheap to fly, and whether fares are rising
    or falling. Everything the phone view needs in one call."""
    result = traveller_summary(db, route_label.upper(), carrier.upper() if carrier else None)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
