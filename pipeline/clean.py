"""Data-cleaning pipeline: turns a day's RawObservation rows into CleanFare
aggregates -- removing outliers, excluding sold-out/cancelled flights, and
handling groups with too little data to trust.
"""
import statistics
from datetime import date

from sqlalchemy import and_
from sqlalchemy.orm import Session

from db.models import AvailabilityStatus, CleanFare, RawObservation

MAD_K = 3.5  # outlier threshold, in scaled median-absolute-deviations
MAD_SCALE = 1.4826  # scales MAD to be ~comparable to std-dev under normality
MIN_GROUP_SIZE_FOR_OUTLIER_FILTER = 4


def _mad_inlier_mask(values: list[float]) -> list[bool]:
    """True for values within MAD_K scaled-MADs of the median. If the group is
    too small to filter statistically, or has zero spread, everything passes."""
    if len(values) < MIN_GROUP_SIZE_FOR_OUTLIER_FILTER:
        return [True] * len(values)
    med = statistics.median(values)
    mad = statistics.median(abs(v - med) for v in values)
    if mad == 0:
        return [True] * len(values)
    threshold = MAD_K * mad * MAD_SCALE
    return [abs(v - med) <= threshold for v in values]


def clean_day(session: Session, observation_date: date) -> int:
    """Aggregates RawObservation -> CleanFare for one observation_date.
    Returns the number of CleanFare rows written."""
    rows = (
        session.query(RawObservation)
        .filter(RawObservation.observation_date == observation_date)
        .all()
    )

    groups: dict[tuple, list[RawObservation]] = {}
    sold_out_counts: dict[tuple, int] = {}
    for row in rows:
        key = (row.route_id, row.carrier_id, row.advance_window_days)
        if row.availability_status in (AvailabilityStatus.SOLD_OUT, AvailabilityStatus.CANCELLED):
            sold_out_counts[key] = sold_out_counts.get(key, 0) + 1
            continue
        if row.total_fare is None:
            continue
        groups.setdefault(key, []).append(row)

    written = 0
    for key, group_rows in groups.items():
        route_id, carrier_id, window = key
        total_fares = [r.total_fare for r in group_rows]
        mask = _mad_inlier_mask(total_fares)
        inliers = [r for r, keep in zip(group_rows, mask) if keep]
        n_excluded = len(group_rows) - len(inliers)
        if not inliers:
            continue

        clean = CleanFare(
            observation_date=observation_date,
            route_id=route_id,
            carrier_id=carrier_id,
            advance_window_days=window,
            median_base_fare=statistics.median(r.base_fare for r in inliers if r.base_fare is not None),
            median_taxes=statistics.median(r.taxes for r in inliers if r.taxes is not None),
            median_total_fare=statistics.median(r.total_fare for r in inliers),
            min_total_fare=min(r.total_fare for r in inliers),
            max_total_fare=max(r.total_fare for r in inliers),
            n_obs=len(inliers),
            n_excluded_outliers=n_excluded,
            n_sold_out=sold_out_counts.get(key, 0),
        )

        existing = (
            session.query(CleanFare)
            .filter(
                and_(
                    CleanFare.observation_date == observation_date,
                    CleanFare.route_id == route_id,
                    CleanFare.carrier_id == carrier_id,
                    CleanFare.advance_window_days == window,
                )
            )
            .one_or_none()
        )
        if existing is not None:
            for attr in (
                "median_base_fare", "median_taxes", "median_total_fare",
                "min_total_fare", "max_total_fare", "n_obs", "n_excluded_outliers", "n_sold_out",
            ):
                setattr(existing, attr, getattr(clean, attr))
        else:
            session.add(clean)
        written += 1

    session.commit()
    return written


def clean_date_range(session: Session, start: date, end: date) -> int:
    from datetime import timedelta

    total = 0
    current = start
    while current <= end:
        total += clean_day(session, current)
        current += timedelta(days=1)
    return total
