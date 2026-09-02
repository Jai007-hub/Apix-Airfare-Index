import statistics
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import ValidationResult
from validation.backtest import deviation_profile, directional_agreement, error_metrics

router = APIRouter(prefix="/api/v1/validation", tags=["validation"])


@router.get("")
def get_validation(
    start: date | None = Query(None, description="First month to include (any day in it)."),
    end: date | None = Query(None, description="Last month to include (any day in it)."),
    db: Session = Depends(get_db),
):
    """APIx against the official CPI airfare sub-index.

    `start`/`end` narrow the comparison window. The stored APIx values keep
    the rebasing computed over the *whole* series rather than being re-anchored
    to the window: re-anchoring would force the window's first month to
    exactly 0% error by construction, which would make a short window look
    flawless for arithmetic reasons rather than accuracy ones.
    """
    q = db.query(ValidationResult)
    if start is not None:
        q = q.filter(ValidationResult.period_month >= date(start.year, start.month, 1))
    if end is not None:
        q = q.filter(ValidationResult.period_month <= date(end.year, end.month, 1))
    rows = q.order_by(ValidationResult.period_month).all()
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
    extent = db.query(
        func.min(ValidationResult.period_month), func.max(ValidationResult.period_month)
    ).one()
    full_start, full_last = extent
    full_end = (
        (
            date(full_last.year + 1, 1, 1)
            if full_last.month == 12
            else date(full_last.year, full_last.month + 1, 1)
        )
        - timedelta(days=1)
        if full_last
        else None
    )

    window_start = rows[0].period_month
    last = rows[-1].period_month
    next_month = (
        date(last.year + 1, 1, 1) if last.month == 12 else date(last.year, last.month + 1, 1)
    )
    window_end = next_month - timedelta(days=1)

    return {
        "n_months_compared": len(points),
        # The full extent on record, so the picker can bound itself and the
        # page can say when it is showing a slice rather than everything.
        "available_start": full_start,
        "available_end": full_end,
        "days_covered": (window_end - window_start).days + 1,
        "window_start": window_start,
        "window_end": window_end,
        "mape_pct": round(mape, 3),
        "pearson_correlation": round(correlation, 4) if correlation is not None else None,
        "directional_agreement": directional_agreement(
            [p["apix_value_rebased"] for p in points],
            [p["cpi_airfare_value"] for p in points],
        ),
        "deviation_profile": deviation_profile(points),
        "error_metrics": error_metrics(
            [p["apix_value_rebased"] for p in points],
            [p["cpi_airfare_value"] for p in points],
        ),
        "points": points,
    }
