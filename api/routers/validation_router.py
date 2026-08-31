import statistics
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import ValidationResult
from validation.backtest import directional_agreement

router = APIRouter(prefix="/api/v1/validation", tags=["validation"])


@router.get("")
def get_validation(db: Session = Depends(get_db)):
    rows = db.query(ValidationResult).order_by(ValidationResult.period_month).all()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No validation results yet -- run `python -m scripts.seed_demo_data` or "
            "validation/backtest.py to compare APIx against cpi_1054.xlsx",
        )

    points = [
        {
            "year": r.period_month.year,
            "month": r.period_month.month,
            "apix_value_rebased": round(r.apix_value_rebased, 3),
            "cpi_airfare_value": round(r.cpi_airfare_value, 3),
            "pct_diff": round(r.pct_diff, 3),
        }
        for r in rows
    ]
    mape = statistics.mean(abs(p["pct_diff"]) for p in points)
    correlation = None
    if len(points) >= 2:
        try:
            correlation = statistics.correlation(
                [p["apix_value_rebased"] for p in points], [p["cpi_airfare_value"] for p in points]
            )
        except statistics.StatisticsError:
            correlation = None

    # CPI publishes monthly, so comparison points are monthly -- but the
    # requirement is phrased in days, so report the span the window covers too.
    window_start = rows[0].period_month
    last = rows[-1].period_month
    next_month = (
        date(last.year + 1, 1, 1) if last.month == 12 else date(last.year, last.month + 1, 1)
    )
    window_end = next_month - timedelta(days=1)

    return {
        "n_months_compared": len(points),
        "days_covered": (window_end - window_start).days + 1,
        "window_start": window_start,
        "window_end": window_end,
        "mape_pct": round(mape, 3),
        "pearson_correlation": round(correlation, 4) if correlation is not None else None,
        "directional_agreement": directional_agreement(
            [p["apix_value_rebased"] for p in points],
            [p["cpi_airfare_value"] for p in points],
        ),
        "points": points,
    }
