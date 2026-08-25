# Data Dictionary

## `city_pairs` (basket)
| Column | Type | Notes |
|---|---|---|
| origin, destination | str(3) | IATA airport codes |
| label | str | e.g. `DEL-BOM` |
| dgca_weight | float | Basket weight (illustrative, see `scraper/config.py`) |

## `carriers`
code (e.g. `6E`), name, carrier_type (`LCC` \| `FSC`)

## `sources`
name (e.g. `makemytrip`), source_type (`airline` \| `ota`), base_url

## `raw_observations` (immutable, one row per quote)
| Column | Notes |
|---|---|
| scraped_at / observation_date | when the quote was captured |
| source_id, route_id, carrier_id | FKs |
| flight_number, fare_class | as quoted |
| departure_date | the flight date being priced |
| advance_window_days | T+1 / T+7 / T+15 / T+30 / T+45 |
| base_fare | fare excluding taxes/fees |
| taxes | statutory taxes (GST etc.) |
| udf | User Development Fee / PSF (airport-levied) |
| convenience_fee | OTA booking fee (0 for direct-airline sources) |
| total_fare | base_fare + taxes + udf + convenience_fee |
| availability_status | `available` \| `sold_out` \| `cancelled` \| `unknown` |
| data_source_type | `live` \| `synthetic_fallback` -- **always check this before treating a row as a real market observation** |
| raw_payload | original scraped text, for audit |

## `clean_fares` (daily aggregate, output of `pipeline/clean.py`)
One row per (observation_date, route, carrier, advance_window_days):
median_base_fare, median_taxes, median_total_fare, min/max_total_fare,
n_obs, n_excluded_outliers (MAD-based), n_sold_out.

## `index_values`
frequency (`daily`\|`weekly`\|`monthly`), period_date, apix_value (base
period = 100), base_period_date, route_breakdown (JSON: route -> price
relative that day).

## `validation_results`
period_month, apix_value_rebased, cpi_airfare_value (from `cpi_1054.xlsx`),
pct_diff. See `docs/VALIDATION.md` for methodology.
