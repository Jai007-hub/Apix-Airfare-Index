from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import CityPair

router = APIRouter(prefix="/api/v1/routes", tags=["routes"])


@router.get("")
def list_routes(db: Session = Depends(get_db)):
    rows = db.query(CityPair).filter_by(is_active=True).order_by(CityPair.dgca_weight.desc()).all()
    return [
        {"label": r.label, "origin": r.origin, "destination": r.destination, "dgca_weight": round(r.dgca_weight, 4)}
        for r in rows
    ]
