"""Validation (requirement #10): compare the computed monthly APIx against the
official MoSPI CPI airfare sub-index ("Passenger transport by air, domestic",
cpi_1054.xlsx) as the real-world ground truth. DGCA does not publish a ready-
made fare index, and the CPI airfare sub-index is exactly the series APIx is
meant to augment, so it's the right comparator here.

Methodology:
  1. cpi_1054.xlsx has one row per (state, year, month) with an `index` value
     (base year 2024 = 100), including a genuine "All India" row per month --
     that's the one we use directly as the national series.
  2. Our monthly IndexValue series is on its own base (period_date == the
     seed window's start date == 100). Because the two indices use different
     base periods, we rebase ours by a single scale factor so it matches the
     CPI index level in the first month the two series overlap -- this makes
     the comparison about *trend*, not absolute level, which is the honest
     thing an index with a different base period can be validated on.
  3. Report MAPE (mean absolute % difference) and Pearson correlation across
     all overlapping months as the headline validation numbers.
"""
import statistics
from calendar import month_name
from datetime import date, timedelta

import openpyxl
from sqlalchemy.orm import Session

from db.models import IndexValue, ValidationResult

_MONTH_NUMBER = {name: i for i, name in enumerate(month_name) if name}



def directional_agreement(apix: list[float], cpi: list[float]) -> dict | None:
    """How often APIx and CPI moved the same way from one month to the next.

    Pearson r on a short series is fragile -- one noisy month can swing it a
    long way. "Did both series rise, or both fall" is a blunter question that
    no single month can dominate, so it is a useful sanity check to read
    alongside the correlation rather than instead of it.

    n months give n-1 moves, so the denominator is one less than the number of
    comparison points.
    """
    if len(apix) < 2 or len(apix) != len(cpi):
        return None

    matches = 0
    for i in range(1, len(apix)):
        a = apix[i] - apix[i - 1]
        c = cpi[i] - cpi[i - 1]
        # Both up, both down, or both exactly flat.
        if (a > 0 and c > 0) or (a < 0 and c < 0) or (a == 0 and c == 0):
            matches += 1

    comparisons = len(apix) - 1
    return {
        "matches": matches,
        "comparisons": comparisons,
        "pct": round(matches / comparisons * 100, 1),
    }

def load_cpi_all_india_series(xlsx_path: str) -> list[dict]:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb["CPI Data"]
    rows = list(ws.iter_rows(min_row=2, values_only=True))

    series_by_month: dict[tuple[int, int], float] = {}
    for row in rows:
        year, month_str, state, index_value = int(row[2]), row[3], row[4], float(row[12])
        if state != "All India":
            continue
        series_by_month[(year, _MONTH_NUMBER[month_str])] = index_value

    series = [{"year": y, "month": m, "cpi_index": v} for (y, m), v in series_by_month.items()]
    series.sort(key=lambda x: (x["year"], x["month"]))
    return series


def run_backtest(session: Session, xlsx_path: str) -> dict:
    cpi_series = load_cpi_all_india_series(xlsx_path)
    if not cpi_series:
        return {"error": f"No 'All India' rows found in {xlsx_path} -- check the state column values."}

    monthly_rows = (
        session.query(IndexValue)
        .filter_by(frequency="monthly")
        .order_by(IndexValue.period_date)
        .all()
    )
    apix_by_month = {(r.period_date.year, r.period_date.month): r.apix_value for r in monthly_rows}

    overlap = [c for c in cpi_series if (c["year"], c["month"]) in apix_by_month]
    if not overlap:
        return {
            "error": "No overlapping year/month between computed monthly APIx and cpi_1054.xlsx. "
            "Seed a date range that covers the CPI file's months.",
            "cpi_months_available": [(c["year"], c["month"]) for c in cpi_series],
            "apix_months_available": sorted(apix_by_month.keys()),
        }

    first = overlap[0]
    apix_first_raw = apix_by_month[(first["year"], first["month"])]
    scale = first["cpi_index"] / apix_first_raw if apix_first_raw else 1.0

    results = []
    for c in overlap:
        apix_raw = apix_by_month[(c["year"], c["month"])]
        apix_rebased = apix_raw * scale
        pct_diff = 100.0 * (apix_rebased - c["cpi_index"]) / c["cpi_index"]
        results.append(
            {
                "year": c["year"],
                "month": c["month"],
                "apix_rebased": round(apix_rebased, 3),
                "cpi_index": round(c["cpi_index"], 3),
                "pct_diff": round(pct_diff, 3),
            }
        )

    mape = statistics.mean(abs(r["pct_diff"]) for r in results)
    correlation = None
    if len(results) >= 2:
        apix_vals = [r["apix_rebased"] for r in results]
        cpi_vals = [r["cpi_index"] for r in results]
        try:
            correlation = statistics.correlation(apix_vals, cpi_vals)
        except statistics.StatisticsError:
            correlation = None

    for r in results:
        period_month = date(r["year"], r["month"], 1)
        existing = session.query(ValidationResult).filter_by(period_month=period_month).one_or_none()
        if existing is not None:
            existing.apix_value_rebased = r["apix_rebased"]
            existing.cpi_airfare_value = r["cpi_index"]
            existing.pct_diff = r["pct_diff"]
        else:
            session.add(
                ValidationResult(
                    period_month=period_month,
                    apix_value_rebased=r["apix_rebased"],
                    cpi_airfare_value=r["cpi_index"],
                    pct_diff=r["pct_diff"],
                )
            )
    session.commit()

    # The requirement is stated in days, but CPI is only published monthly, so
    # the comparison points are monthly while the window they span is measured
    # in days -- report both rather than leaving "6" to look like 6 days.
    window_start = date(results[0]["year"], results[0]["month"], 1)
    last_month_start = date(results[-1]["year"], results[-1]["month"], 1)
    window_end = (
        date(last_month_start.year + 1, 1, 1)
        if last_month_start.month == 12
        else date(last_month_start.year, last_month_start.month + 1, 1)
    ) - timedelta(days=1)

    return {
        "n_months_compared": len(results),
        "days_covered": (window_end - window_start).days + 1,
        "window_start": window_start,
        "window_end": window_end,
        "rebase_scale_factor": round(scale, 6),
        "mape_pct": round(mape, 3),
        "pearson_correlation": round(correlation, 4) if correlation is not None else None,
        "directional_agreement": directional_agreement(
            [r["apix_rebased"] for r in results], [r["cpi_index"] for r in results]
        ),
        "results": results,
    }
