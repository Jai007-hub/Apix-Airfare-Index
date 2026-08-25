# Validation (requirement #10)

## Methodology

`validation/backtest.py` compares the computed monthly APIx against the
real MoSPI CPI airfare sub-index in `cpi_1054.xlsx` ("Passenger transport by
air, domestic", base year 2024 = 100, one row per state/UT per month, plus a
genuine **"All India"** row). DGCA does not publish a ready-made fare
*index*, and the CPI airfare sub-index is exactly the series APIx is meant
to augment, so it's the right ground truth here.

1. Take the CPI file's `index` value for the `state == "All India"` row for
   each (year, month) -- the true national series, not a state average.
2. Our monthly `IndexValue` series is on its own base (the seed window's
   first day = 100). Since the two indices use different base periods, we
   rebase ours by a single scale factor so it matches the CPI level in the
   first month the two series overlap. This makes the comparison about
   *trend*, not absolute level -- the honest thing an index with an
   independent base period can be validated on.
3. Report MAPE (mean absolute % difference) and Pearson correlation across
   all overlapping months.

## Running it

```
python -m scripts.seed_demo_data              # backfills Feb-Jul 2026 by default, then runs the backtest
python -m scripts.seed_demo_data --start 2026-02-01 --end 2026-07-31 --cpi-xlsx cpi_1054.xlsx
```

Or standalone: `validation.backtest.run_backtest(session, "cpi_1054.xlsx")`.

## Results (default seed window, 6 months, satisfies the ">=30 days" requirement several times over)

Compared against the real `state == "All India"` row for each month:

| Month | APIx (rebased) | CPI airfare index (All India) | Diff % |
|---|---|---|---|
| 2026-02 | 122.43 | 122.43 | 0.00% |
| 2026-03 | 125.79 | 123.55 | +1.82% |
| 2026-04 | 133.24 | 123.27 | +8.09% |
| 2026-05 | 132.02 | 127.62 | +3.45% |
| 2026-06 | 125.08 | 126.09 | -0.81% |
| 2026-07 | 114.77 | 125.46 | -8.52% |

**MAPE = 3.78%, Pearson r = 0.09** (n=6 months).

## Reading these numbers honestly

The demo dataset behind this table is the **calibrated synthetic
generator** (`scraper/synthetic/`), not live-scraped prices -- see
`docs/ARCHITECTURE.md` for why. Its stylized facts (lead-time curve,
seasonality, day-of-week effects) were chosen from general aviation-pricing
knowledge, not fit to `cpi_1054.xlsx`. A near-zero correlation against an
independently-generated CPI series is therefore the expected result of two
*unrelated* time series sharing only a rebased starting point -- it is not a
claim about how accurately APIx would track real fares. (MAPE stays low
regardless, since the rebasing anchors both series to the same starting
level and neither drifts far over 6 months -- MAPE alone is a weak signal
here; correlation is the more honest one, and it correctly reads as "not
meaningfully related" for synthetic vs. real data.)

What this backtest *does* validate:
- The full pipeline (generate/scrape -> clean -> index -> rebase -> compare)
  runs end to end and produces a well-formed, reproducible comparison.
- The rebasing and MAPE/correlation math are correct (see
  `tests/test_index.py` for the unit-level checks).
- The APIx methodology itself (DGCA-weighted relatives, base-period=100) is
  the same one CPI-style indices use, so once real scraped fares feed this
  same pipeline, this is the exact report that would demonstrate tracking
  accuracy against official CPI.

Re-running with `--mode live` data (once spiders are hardened against
current site markup, per `docs/ETHICAL_SCRAPING.md`) would turn this from a
pipeline-correctness demonstration into a real accuracy validation.
