"""Single source of truth for the city-pair basket, carriers, sources and
advance-purchase windows. Shared by the synthetic generator, the live
spiders, the scheduler and the seed script so nothing drifts out of sync.

DGCA_WEIGHT values are illustrative placeholders approximating relative
traffic share on these trunk routes (DEL-BOM being India's busiest domestic
sector, etc.). Swap in the official DGCA "Domestic Airline Traffic Report"
city-pair table for a production deployment -- the shape (label -> weight,
summing to 1.0) is all that downstream code depends on.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RouteDef:
    origin: str
    destination: str
    label: str
    dgca_weight: float


@dataclass(frozen=True)
class CarrierDef:
    code: str
    name: str
    carrier_type: str  # "LCC" | "FSC"


@dataclass(frozen=True)
class SourceDef:
    name: str
    source_type: str  # "airline" | "ota"
    base_url: str


# City-pair basket, weighted by (illustrative) DGCA domestic traffic share. Sums to 1.0.
ROUTES = [
    RouteDef("DEL", "BOM", "DEL-BOM", 0.22),
    RouteDef("DEL", "BLR", "DEL-BLR", 0.14),
    RouteDef("BOM", "BLR", "BOM-BLR", 0.12),
    RouteDef("DEL", "CCU", "DEL-CCU", 0.10),
    RouteDef("BLR", "HYD", "BLR-HYD", 0.08),
    RouteDef("MAA", "DEL", "MAA-DEL", 0.09),
    RouteDef("DEL", "HYD", "DEL-HYD", 0.09),
    RouteDef("BOM", "CCU", "BOM-CCU", 0.06),
    RouteDef("BLR", "CCU", "BLR-CCU", 0.05),
    RouteDef("MAA", "BLR", "MAA-BLR", 0.05),
]

CARRIERS = [
    CarrierDef("6E", "IndiGo", "LCC"),
    CarrierDef("AI", "Air India", "FSC"),
    CarrierDef("IX", "Air India Express", "LCC"),
    CarrierDef("QP", "Akasa Air", "LCC"),
    CarrierDef("SG", "SpiceJet", "LCC"),
]

SOURCES = [
    SourceDef("indigo", "airline", "https://www.goindigo.in"),
    SourceDef("air_india", "airline", "https://www.airindia.com"),
    SourceDef("air_india_express", "airline", "https://www.airindiaexpress.com"),
    SourceDef("akasa_air", "airline", "https://www.akasaair.com"),
    SourceDef("spicejet", "airline", "https://www.spicejet.com"),
    SourceDef("makemytrip", "ota", "https://www.makemytrip.com"),
    SourceDef("yatra", "ota", "https://www.yatra.com"),
    SourceDef("easemytrip", "ota", "https://www.easemytrip.com"),
    SourceDef("cleartrip", "ota", "https://www.cleartrip.com"),
    SourceDef("ixigo", "ota", "https://www.ixigo.com"),
    SourceDef("goibibo", "ota", "https://www.goibibo.com"),
]

# Advance-purchase windows in days-before-departure.
ADVANCE_WINDOWS = [1, 7, 15, 30, 45]

FARE_CLASSES = ["Economy", "Flexi Economy"]

# An airline's own site only ever sells its own flights; map source name -> carrier code.
AIRLINE_SOURCE_TO_CARRIER_CODE = {
    "indigo": "6E",
    "air_india": "AI",
    "air_india_express": "IX",
    "akasa_air": "QP",
    "spicejet": "SG",
}


def carrier_by_code(code: str) -> CarrierDef:
    for c in CARRIERS:
        if c.code == code:
            return c
    raise KeyError(code)
