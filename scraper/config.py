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
#
# The ten trunk routes carry 95% of the basket weight; the five North-East
# routes below share the remaining 5%. That split is the point of including
# them: they are thin, expensive sectors whose fares move differently from
# the trunk network, and a CPI airfare component built only from metro trunk
# routes would miss that entirely. Their weights are small because their
# passenger volumes are, not because the routes matter less.
#
# Order here is the display order everywhere -- trunk routes first, then the
# North-East additions.
ROUTES = [
    # -- trunk routes (95% of basket weight) ------------------------------
    RouteDef("DEL", "BOM", "DEL-BOM", 0.209),
    RouteDef("DEL", "BLR", "DEL-BLR", 0.133),
    RouteDef("BOM", "BLR", "BOM-BLR", 0.114),
    RouteDef("DEL", "CCU", "DEL-CCU", 0.095),
    RouteDef("BLR", "HYD", "BLR-HYD", 0.076),
    RouteDef("MAA", "DEL", "MAA-DEL", 0.0855),
    RouteDef("DEL", "HYD", "DEL-HYD", 0.0855),
    RouteDef("BOM", "CCU", "BOM-CCU", 0.057),
    RouteDef("BLR", "CCU", "BLR-CCU", 0.0475),
    RouteDef("MAA", "BLR", "MAA-BLR", 0.0475),
    # -- North-East regional routes (5% of basket weight) -----------------
    RouteDef("IMF", "DEL", "IMF-DEL", 0.015),   # Imphal, Manipur
    RouteDef("DIB", "DEL", "DIB-DEL", 0.012),   # Dibrugarh, Upper Assam
    RouteDef("SHL", "CCU", "SHL-CCU", 0.010),   # Shillong, Meghalaya
    RouteDef("IXA", "BLR", "IXA-BLR", 0.008),   # Agartala, Tripura
    RouteDef("IXI", "GAU", "IXI-GAU", 0.005),   # Lilabari, Assam/Arunachal border
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
