# API

FastAPI app in `api/main.py`. Run: `uvicorn api.main:app --reload`.
Interactive OpenAPI docs at `/docs` once running.

All endpoints are `GET`, CORS-open (`allow_origins=["*"]`) so NSO/RBI or any
downstream consumer can call them directly from a browser or server.

| Endpoint | Query params | Returns |
|---|---|---|
| `GET /api/v1/health` | -- | `{"status": "ok"}` |
| `GET /api/v1/index` | `frequency` (daily\|weekly\|monthly, default daily), `start`, `end` | `[{period_date, apix_value}]` |
| `GET /api/v1/routes` | -- | Basket: `[{label, origin, destination, dgca_weight}]` |
| `GET /api/v1/fares` | `route`, `carrier`, `advance_window_days`, `start`, `end`, `limit` | Clean daily fare cells: origin, destination, carrier, advance-purchase window, fare class, and the full fare split (base / taxes / UDF / convenience fee / total) |
| `GET /api/v1/heatmap` | `start`, `end`, `frequency` (daily\|weekly\|monthly), `source` | `{periods, routes, matrix, source}` -- route x period avg fare, optionally for one booking portal |
| `GET /api/v1/sources` | -- | The portals scraped: `[{name, source_type (airline\|ota), base_url}]` |
| `GET /api/v1/elasticity` | `start`, `end` | `{route_label: [{advance_window_days, avg_fare}]}` |
| `GET /api/v1/validation` | `start`, `end` | APIx vs CPI comparison: `{n_months_compared, mape_pct, pearson_correlation, directional_agreement, deviation_profile, points}` |
| `GET /api/v1/traveller` | -- | Every tracked sector at its best current fare, cheapest first: `[{route, origin, destination, best_fare}]` |
| `GET /api/v1/traveller/{route_label}` | `carrier` (optional airline code) | Consumer-facing route summary: `{typical_fare, cheapest_window, dearest_window, max_saving, max_saving_pct, windows, fare_breakdown, carriers, months, trend_pct, trend_direction}` |

`/api/v1/index` and `/api/v1/validation` return `404` if the corresponding
tables are empty -- run `python -m scripts.seed_demo_data` first.

## `/api/v1/traveller/{route_label}`

The other endpoints answer an analyst's question -- how is the index moving,
does it track CPI. This one answers a passenger's: what does this route cost,
when should I book, which airline is cheapest. It powers the phone view.

It reads the same `clean_fares` table as the index, so the two can never
disagree; it just aggregates differently:

- **`typical_fare`** -- median across the five advance-purchase windows, so a
  single 1-day-out spike can't set the headline number.
- **`cheapest_window` / `max_saving`** -- the lead-time curve reduced to the
  one actionable fact, "book this far ahead and save this much".
- **`carriers_by_window`** -- the airline ranking at every booking window,
  keyed by window days. Each list holds its window constant: comparing one
  airline's T+45 fare against another's T+1 would rank booking timing, not
  airlines. Who is cheapest genuinely changes with the window, which is why
  all five are returned rather than one.
- **`carriers`** -- shorthand for `carriers_by_window` at the cheapest
  window, so a caller wanting just the headline answer needs no lookup.
- **`fare_breakdown`** -- the cheapest fare split into base fare, taxes, UDF
  and convenience fee. The four lines are forced to sum to the fare exactly:
  rounding them independently can leave the split a rupee out, and a breakdown
  that doesn't add up reads as a bug.
- **`windows[].sold_out_pct`** -- share of searches at that window that came
  back with no seats. Booking late costs more *and* more often leaves nothing
  to buy; this is the half a fare table doesn't show.
- **`months`** -- average fare per calendar month, pooled across every year on
  record. Pooling (rather than keying on year-month) is what makes it a
  seasonal statement: someone planning October wants every October we have.
- **`trend_pct`** -- mean fare over the last 30 days against the 30 before it.

All figures average the most recent 7 days of observations to smooth
day-to-day noise. Route labels are case-insensitive. Returns `404` for an
unknown route, and also for a route that has stopped reporting -- quoting a
months-old fare as if it were current would be worse than returning nothing.

## `directional_agreement` on `/api/v1/validation`

`{matches, comparisons, pct}` -- how often APIx and CPI moved the same way
from one month to the next.

Pearson r on a short series is fragile: one noisy month can swing it a long
way, which makes a single correlation figure easy to over-read. "Did both
series rise, or both fall" is a blunter question that no single month can
dominate, so it is reported alongside r rather than instead of it.

`comparisons` is one less than `n_months_compared` -- n months give n-1
month-on-month moves. Returns `null` below two points. A month where either
series is exactly flat only counts as agreement if both are.

## `deviation_profile` on `/api/v1/validation`

`{median_abs_pct, best_month, worst_month, within_5pct, n,
excludes_rebase_anchor}` -- the distribution behind the MAPE headline.

A mean hides its own shape: the same MAPE can come from every month being
mediocre or from most months being close and one being terrible. The median
and the extremes say which.

**The first overlapping month is excluded.** Rebasing scales APIx to match CPI
exactly there, so its deviation is `0.000%` by construction. Reporting that as
the closest month would present an arithmetic identity as a result, so `n` is
one less than `n_months_compared`. Note that `mape_pct` itself is still
computed over *all* months including that anchor, which flatters it slightly
at small sample sizes.

## `source` on `/api/v1/heatmap`

Narrows the matrix to one booking portal by name (`indigo`, `makemytrip`, ...
see `/api/v1/sources`). Omitted, it averages across all eleven.

**This one reads the raw observations, not the cleaned table.** `clean_fares`
has no source column by design: cleaning collapses every portal quoting the
same flight into one cell, so a flight listed on six sites is not counted six
times in the index. Filtering by portal therefore has to go back to
`raw_observations`.

Sold-out and cancelled rows are excluded, matching what cleaning does, which
keeps the filtered view within ~3% of the unfiltered one rather than jumping
when a filter is applied. It does skip the MAD outlier pass, which is why the
two are close but not identical.

An unknown portal name returns `404` rather than an empty matrix -- an empty
grid reads as "no fares on these routes" when the real answer is "that portal
is not tracked".

## `start` / `end` on `/api/v1/validation`

Narrow the back-test to a window (any day within the first and last month to
include). Omitted, the whole record is compared. The response always carries
`available_start` / `available_end` describing the **full** extent, so a
caller can bound a date picker without it ratcheting shut as the window
narrows.

**The window does not re-anchor the rebasing.** APIx values keep the scale
factor computed over the whole series. Re-anchoring to the window would force
its first month to exactly 0.000% error by construction, so any short window
would look flawless for arithmetic reasons rather than accuracy ones -- a
30-day window would report 0% MAPE and mean nothing.

Windows shorter than three months degrade the metrics, and the API says so by
omitting rather than faking them: `pearson_correlation` and
`directional_agreement` are `null` below two points. At exactly two points a
correlation is arithmetically +/-1 and carries no information, which the
dashboard warns about rather than the API suppressing.

## `carrier` on `/api/v1/traveller/{route}`

Narrows `windows`, `fare_breakdown`, `cheapest_window`, `max_saving` and
`trend_pct` to one airline (`6E`, `AI`, `SG`, `QP`, `IX`).

Without it every one of those is a **mean across airlines** -- a real number,
but nobody's actual price. A reader comparing the window table against the
airline ranking below it then sees two figures that cannot be reconciled: on
DEL-BOM the T+45 row reads 4,624 while SpiceJet, the cheapest airline at that
window, reads 4,289. Naming an airline makes all three agree.

`carriers_by_window` is deliberately **not** narrowed -- its whole job is to
show what the alternatives cost, so it always covers every airline. The
response echoes `carrier_code` / `carrier_name` so a caller can label its
figures correctly, and `null` there means the blended view.

An unknown airline, or one that does not fly the route, returns `404` rather
than silently falling back to the blended numbers -- which the reader would
then believe were that airline's.

## `breakdown_by_window` and how the fare figures reconcile

Three numbers on the traveller view describe the same thing and must agree
exactly, because a reader can and does check them:

1. `windows[w].fare` -- the figure for a booking window
2. `sum(breakdown_by_window[w].values())` -- its four-part split
3. the mean of `carriers_by_window[w]` fares -- the airlines listed beneath

Two deliberate choices make that hold.

**The window fare is the mean of the *rounded* per-airline fares**, not the
rounded mean of every row. The airline table prints those rounded values, so
anyone averaging what is on screen must land on the window figure; a plain
mean can differ by a rupee.

**Each window carries its own split**, absorbing its rounding residual into
the largest line. `fare_breakdown` remains as shorthand for the cheapest
window's split.

With `carrier` set, all three collapse to that airline's own fare, so the
comparison is between one airline's numbers rather than an average nobody
charges.
