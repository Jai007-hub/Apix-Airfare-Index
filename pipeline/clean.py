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
        # Fare class is part of the grain: Economy and Flexi Economy on the
        # same flight are different products, so they must not be averaged
        # into a single median.
        key = (row.route_id, row.carrier_id, row.advance_window_days, row.fare_class)
        if row.availability_status in (AvailabilityStatus.SOLD_OUT, AvailabilityStatus.CANCELLED):
            sold_out_counts[key] = sold_out_counts.get(key, 0) + 1
            continue
        if row.total_fare is None:
            continue
        groups.setdefault(key, []).append(row)

    def _representative(rows_: list[RawObservation]) -> RawObservation:
        """The quote sitting at the median total fare.

        Every fare component is taken from this one real quote rather than
        each being an independent median. Independent medians come from
        different rows and therefore do not add up: on a group of seven
        quotes with convenience fees [0, 149, 179, 199, 249, 250, 300], the
        median fee is 199 while the median *total* belongs to the quote
        charging 300 -- so base + taxes + UDF + fee missed the reported total
        by 101 rupees. Sourcing the whole split from one observed quote makes
        the components reconcile exactly and keeps every published figure a
        price somebody was actually offered, which is how price statistics
        are normally constructed.

        With an even count this picks the lower of the two central quotes, so
        the result is always a real observation rather than a blend of two.
        """
        ordered = sorted(rows_, key=lambda r: r.total_fare)
        return ordered[(len(ordered) - 1) // 2]

    written = 0
    for key, group_rows in groups.items():
        route_id, carrier_id, window, fare_class = key
        total_fares = [r.total_fare for r in group_rows]
        mask = _mad_inlier_mask(total_fares)
        inliers = [r for r, keep in zip(group_rows, mask) if keep]
        n_excluded = len(group_rows) - len(inliers)
        if not inliers:
            continue

        rep = _representative(inliers)

        clean = CleanFare(
            observation_date=observation_date,
            route_id=route_id,
            carrier_id=carrier_id,
            advance_window_days=window,
            fare_class=fare_class,
            median_base_fare=rep.base_fare if rep.base_fare is not None else 0.0,
            median_taxes=rep.taxes if rep.taxes is not None else 0.0,
            median_udf=rep.udf if rep.udf is not None else 0.0,
            median_convenience_fee=rep.convenience_fee if rep.convenience_fee is not None else 0.0,
            median_total_fare=rep.total_fare,
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
                    CleanFare.fare_class == fare_class,
                )
            )
            .one_or_none()
        )
        if existing is not None:
            for attr in (
                "median_base_fare", "median_taxes", "median_udf",
                "median_convenience_fee", "median_total_fare",
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
