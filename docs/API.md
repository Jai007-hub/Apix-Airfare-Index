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

`/api/v1/index` and `/api/v1/validation` return `404` if the corresponding
tables are empty -- run `python -m scripts.seed_demo_data` first.
