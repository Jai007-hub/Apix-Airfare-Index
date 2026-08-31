from datetime import date

from db.models import IndexValue
from validation.backtest import directional_agreement, run_backtest


def _seed_monthly_index(db_session, months, base=date(2025, 1, 1)):
    for (year, month), value in months.items():
        db_session.add(
            IndexValue(
                frequency="monthly",
                period_date=date(year, month, 1),
                apix_value=value,
                base_period_date=base,
            )
        )
    db_session.commit()


def test_days_covered_spans_whole_months_not_just_month_starts(db_session, tmp_path):
    """The requirement is written in days but CPI only publishes monthly, so the
    window has to be measured to the END of the last compared month."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CPI Data"
    ws.append(
        ["base_year", "series", "year", "month", "state", "sector", "division", "group",
         "class", "sub_class", "item", "code", "index", "inflation", "imputation"]
    )
    # Three consecutive months of All-India CPI: Jan, Feb, Mar 2025.
    for month_name_, idx in [("January", 100.0), ("February", 102.0), ("March", 104.0)]:
        ws.append(
            ["2024", "Current", "2025", month_name_, "All India", "Combined", "Transport",
             "grp", "cls", "sub", "Airfare", "07", idx, 0.0, "N"]
        )
    xlsx = tmp_path / "cpi.xlsx"
    wb.save(xlsx)

    _seed_monthly_index(
        db_session, {(2025, 1): 100.0, (2025, 2): 101.0, (2025, 3): 103.0}
    )

    result = run_backtest(db_session, str(xlsx))

    assert result["n_months_compared"] == 3
    assert result["window_start"] == date(2025, 1, 1)
    # Must run to 31 March, not 1 March -- otherwise the day count is short by
    # nearly a month and understates the coverage.
    assert result["window_end"] == date(2025, 3, 31)
    assert result["days_covered"] == 31 + 28 + 31  # Jan + Feb + Mar 2025


def test_days_covered_handles_a_december_end_month(db_session, tmp_path):
    """December has to roll into the next year when finding the month end."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CPI Data"
    ws.append(["c"] * 15)
    for month_name_, idx in [("November", 100.0), ("December", 101.0)]:
        ws.append(
            ["2024", "Current", "2025", month_name_, "All India", "Combined", "Transport",
             "grp", "cls", "sub", "Airfare", "07", idx, 0.0, "N"]
        )
    xlsx = tmp_path / "cpi.xlsx"
    wb.save(xlsx)

    _seed_monthly_index(db_session, {(2025, 11): 100.0, (2025, 12): 102.0})

    result = run_backtest(db_session, str(xlsx))

    assert result["window_end"] == date(2025, 12, 31)
    assert result["days_covered"] == 30 + 31  # Nov + Dec


def test_window_comfortably_exceeds_the_30_day_requirement(db_session, tmp_path):
    """Two adjacent months already clear the problem statement's 30-day floor."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CPI Data"
    ws.append(["c"] * 15)
    for month_name_, idx in [("June", 120.0), ("July", 121.0)]:
        ws.append(
            ["2024", "Current", "2026", month_name_, "All India", "Combined", "Transport",
             "grp", "cls", "sub", "Airfare", "07", idx, 0.0, "N"]
        )
    xlsx = tmp_path / "cpi.xlsx"
    wb.save(xlsx)

    _seed_monthly_index(db_session, {(2026, 6): 118.0, (2026, 7): 119.0})

    assert run_backtest(db_session, str(xlsx))["days_covered"] >= 30


# -- directional agreement ----------------------------------------------------
# Pearson r on a short series swings on one noisy month; "did both move the
# same way" is the blunter check shown alongside it.


def test_series_that_always_move_together_agree_completely():
    apix = [100.0, 105.0, 103.0, 108.0]
    cpi = [200.0, 210.0, 190.0, 220.0]  # same ups and downs, different scale
    assert directional_agreement(apix, cpi) == {"matches": 3, "comparisons": 3, "pct": 100.0}


def test_series_that_always_move_oppositely_agree_never():
    apix = [100.0, 105.0, 103.0, 108.0]
    cpi = [200.0, 190.0, 210.0, 190.0]
    assert directional_agreement(apix, cpi) == {"matches": 0, "comparisons": 3, "pct": 0.0}


def test_denominator_is_moves_not_months():
    """Four months give three month-on-month moves -- reporting "out of 4"
    would overstate the sample."""
    result = directional_agreement([1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0])
    assert result["comparisons"] == 3


def test_mixed_directions_are_counted_not_rounded_away():
    #        up/up      down/up     up/up
    apix = [100.0, 110.0, 105.0, 115.0]
    cpi = [100.0, 110.0, 120.0, 130.0]
    assert directional_agreement(apix, cpi) == {"matches": 2, "comparisons": 3, "pct": 66.7}


def test_a_flat_month_only_agrees_with_another_flat_month():
    assert directional_agreement([100.0, 100.0], [100.0, 100.0])["matches"] == 1
    assert directional_agreement([100.0, 100.0], [100.0, 101.0])["matches"] == 0


def test_too_few_points_reports_nothing_rather_than_a_misleading_zero():
    assert directional_agreement([100.0], [100.0]) is None
    assert directional_agreement([], []) is None
    # Mismatched lengths would silently truncate; refuse instead.
    assert directional_agreement([100.0, 101.0], [100.0]) is None
