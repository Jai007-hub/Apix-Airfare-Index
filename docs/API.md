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
| `GET /api/v1/validation` | -- | APIx vs CPI comparison: `{n_months_compared, mape_pct, pearson_correlation, points}` |
| `GET /api/v1/traveller/{route_label}` | -- (route in path, e.g. `DEL-BOM`) | Consumer-facing route summary: `{typical_fare, cheapest_window, dearest_window, max_saving, max_saving_pct, windows, carriers, trend_pct, trend_direction}` |

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
- **`trend_pct`** -- mean fare over the last 30 days against the 30 before it.

All figures average the most recent 7 days of observations to smooth
day-to-day noise. Route labels are case-insensitive. Returns `404` for an
unknown route, and also for a route that has stopped reporting -- quoting a
months-old fare as if it were current would be worse than returning nothing.
