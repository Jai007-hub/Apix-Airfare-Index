"""Stylized facts used to calibrate the synthetic fare generator.

These are documented, tunable functions -- not scraped values -- standing in
for the real market dynamics described in the problem statement: fares climb
sharply as departure approaches, spike further on weekends/festive season,
and differ by carrier type and booking channel. Replace with fitted
parameters once enough live-scraped history exists.
"""
import zlib
from datetime import date

# Reference one-way economy fare (INR) per route at a relaxed T+45 booking window.
ROUTE_BASE_FARE = {
    "DEL-BOM": 4500,
    "DEL-BLR": 5500,
    "BOM-BLR": 3800,
    "DEL-CCU": 5200,
    "BLR-HYD": 3200,
    "MAA-DEL": 5800,
    "DEL-HYD": 4600,
    "BOM-CCU": 5000,
    "BLR-CCU": 5600,
    "MAA-BLR": 2800,
}

CARRIER_TYPE_MULTIPLIER = {"LCC": 0.85, "FSC": 1.25}

# Airports levying a User Development Fee (UDF)/PSF on top of statutory taxes.
UDF_AIRPORTS = {"DEL": 550, "BOM": 480, "HYD": 430, "BLR": 400, "MAA": 260, "CCU": 220}

# OTA convenience/booking fee (INR); direct airline sources charge none.
OTA_CONVENIENCE_FEE = {
    "makemytrip": 300,
    "yatra": 250,
    "easemytrip": 149,
    "cleartrip": 199,
    "ixigo": 179,
    "goibibo": 249,
}

GST_RATE = 0.05  # simplified statutory tax rate on base fare for economy domestic


def lead_time_multiplier(advance_window_days: int, rng) -> float:
    """Fare multiplier as a function of days-before-departure. Near-term bookings
    (T+1) are both higher on average AND far more volatile (200-400% intraday-style
    swings), reflecting last-minute demand/yield-management pricing."""
    curve = {45: 0.75, 30: 0.85, 15: 1.05, 7: 1.35, 1: 2.20}
    base = curve.get(advance_window_days, 1.0)
    if advance_window_days <= 1:
        # occasional near-sold-out spike: up to ~4x base fare
        if rng.random() < 0.12:
            return base * rng.uniform(1.5, 1.9)
        return base * rng.uniform(0.85, 1.25)
    if advance_window_days <= 7:
        return base * rng.uniform(0.9, 1.15)
    return base * rng.uniform(0.92, 1.08)


def day_of_week_multiplier(departure_date: date) -> float:
    # Friday/Sunday (weekend travel) command a premium; midweek is cheapest.
    weekday = departure_date.weekday()  # Mon=0 ... Sun=6
    return {0: 1.0, 1: 0.95, 2: 0.95, 3: 1.0, 4: 1.15, 5: 1.05, 6: 1.12}[weekday]


def season_multiplier(departure_date: date) -> float:
    # Festive (Oct-Dec) and summer-vacation (Apr-Jun) peaks; monsoon trough.
    month = departure_date.month
    if month in (10, 11, 12):
        return 1.20
    if month in (4, 5, 6):
        return 1.10
    if month in (7, 8):
        return 0.92
    return 1.0


def demand_shock(observation_date: date, route_label: str, rng) -> float:
    """A small route/day-specific random walk component so consecutive days
    aren't perfectly smooth (mirrors real yield-management noise).

    Seeded with crc32 rather than the builtin hash(): Python salts string
    hashing per process, so hash() would hand this function a different value
    on every run and the "seeded, reproducible" generator would silently
    produce a different dataset each time it was seeded.
    """
    key = f"{observation_date.isoformat()}|{route_label}".encode()
    local_rng_state = rng.getstate()
    rng.seed(zlib.crc32(key))
    shock = rng.uniform(0.94, 1.08)
    rng.setstate(local_rng_state)
    return shock


def base_fare_for(route_label: str, carrier_type: str, advance_window_days: int,
                   departure_date: date, observation_date: date, rng) -> float:
    base = ROUTE_BASE_FARE[route_label]
    fare = (
        base
        * CARRIER_TYPE_MULTIPLIER[carrier_type]
        * lead_time_multiplier(advance_window_days, rng)
        * day_of_week_multiplier(departure_date)
        * season_multiplier(departure_date)
        * demand_shock(observation_date, route_label, rng)
    )
    return round(fare, 2)


def taxes_for(base_fare: float) -> float:
    return round(base_fare * GST_RATE, 2)


def udf_for(origin: str, destination: str) -> float:
    return float(UDF_AIRPORTS.get(origin, 0) + UDF_AIRPORTS.get(destination, 0))


def convenience_fee_for(source_name: str) -> float:
    return float(OTA_CONVENIENCE_FEE.get(source_name, 0))


def sold_out_probability(advance_window_days: int) -> float:
    # Sold-out is more likely to be observed close to departure.
    return {1: 0.06, 7: 0.03, 15: 0.015, 30: 0.005, 45: 0.002}.get(advance_window_days, 0.01)
