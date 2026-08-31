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
| `GET /api/v1/heatmap` | `start`, `end`, `frequency` (weekly\|monthly) | `{periods, routes, matrix}` -- route x period avg fare |
| `GET /api/v1/elasticity` | `start`, `end` | `{route_label: [{advance_window_days, avg_fare}]}` |
| `GET /api/v1/validation` | -- | APIx vs CPI comparison: `{n_months_compared, mape_pct, pearson_correlation, directional_agreement, deviation_profile, points}` |
| `GET /api/v1/traveller` | -- | Every tracked sector at its best current fare, cheapest first: `[{route, origin, destination, best_fare}]` |
| `GET /api/v1/traveller/{route_label}` | -- (route in path, e.g. `DEL-BOM`) | Consumer-facing route summary: `{typical_fare, cheapest_window, dearest_window, max_saving, max_saving_pct, windows, fare_breakdown, carriers, months, trend_pct, trend_direction}` |

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
- **`carriers`** -- ranked *at the cheapest window only*. Comparing one
  airline's T+45 fare against another's T+1 would rank booking timing, not
  airlines, so the window is held constant.
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
