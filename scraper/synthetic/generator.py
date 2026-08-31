"""Calibrated synthetic fare generator.

Produces the same shape of records the live spiders would (see
scraper/items.py) for every (route x carrier x source x advance-window)
combination on a given observation date, using the stylized-fact functions
in calibration.py. This is what scripts/seed_demo_data.py and the demo
pipeline run by default, so the rest of the system (cleaning, index
construction, API, dashboard) is fully exercisable without depending on
live scraping succeeding.

Every record is tagged data_source_type="synthetic_fallback" so it's never
confused with a live-scraped observation downstream.
"""
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from scraper import config
from scraper.synthetic import calibration


@dataclass
class FareRecord:
    scraped_at: datetime
    observation_date: date
    source_name: str
    route_label: str
    origin: str
    destination: str
    carrier_code: str
    flight_number: str
    departure_date: date
    advance_window_days: int
    fare_class: str
    base_fare: float
    taxes: float
    udf: float
    convenience_fee: float
    total_fare: float
    availability_status: str
    data_source_type: str = "synthetic_fallback"


class SyntheticFareGenerator:
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate_for_day(self, observation_date: date) -> list[FareRecord]:
        records: list[FareRecord] = []
        for route in config.ROUTES:
            for source in config.SOURCES:
                carriers = self._carriers_for_source(source)
                for carrier in carriers:
                    for window in config.ADVANCE_WINDOWS:
                        record = self._generate_one(observation_date, route, source, carrier, window)
                        if record is not None:
                            records.append(record)
        return records

    def _carriers_for_source(self, source: config.SourceDef) -> list[config.CarrierDef]:
        if source.source_type == "airline":
            code = config.AIRLINE_SOURCE_TO_CARRIER_CODE[source.name]
            return [config.carrier_by_code(code)]
        # OTAs aggregate all carriers.
        return config.CARRIERS

    def _generate_one(self, observation_date, route, source, carrier, window):
        departure_date = observation_date + timedelta(days=window)
        scraped_at = datetime.combine(observation_date, datetime.min.time()) + timedelta(
            hours=self.rng.uniform(6, 22)
        )

        # Unavailable for one of two distinct reasons -- sold out (demand) or
        # cancelled (operational). Both carry no fare, but the pipeline counts
        # and reports them separately.
        draw = self.rng.random()
        unavailable = None
        if draw < calibration.sold_out_probability(window):
            unavailable = "sold_out"
        elif draw < calibration.sold_out_probability(window) + calibration.cancelled_probability(window):
            unavailable = "cancelled"

        if unavailable is not None:
            return FareRecord(
                scraped_at=scraped_at,
                observation_date=observation_date,
                source_name=source.name,
                route_label=route.label,
                origin=route.origin,
                destination=route.destination,
                carrier_code=carrier.code,
                flight_number=f"{carrier.code}{self.rng.randint(100, 999)}",
                departure_date=departure_date,
                advance_window_days=window,
                fare_class="Economy",
                base_fare=None,
                taxes=None,
                udf=None,
                convenience_fee=None,
                total_fare=None,
                availability_status=unavailable,
            )

        base_fare = calibration.base_fare_for(
            route.label, carrier.carrier_type, window, departure_date, observation_date, self.rng
        )
        taxes = calibration.taxes_for(base_fare)
        udf = calibration.udf_for(route.origin, route.destination)
        convenience_fee = calibration.convenience_fee_for(source.name)
        total_fare = round(base_fare + taxes + udf + convenience_fee, 2)

        return FareRecord(
            scraped_at=scraped_at,
            observation_date=observation_date,
            source_name=source.name,
            route_label=route.label,
            origin=route.origin,
            destination=route.destination,
            carrier_code=carrier.code,
            flight_number=f"{carrier.code}{self.rng.randint(100, 999)}",
            departure_date=departure_date,
            advance_window_days=window,
            fare_class="Economy",
            base_fare=base_fare,
            taxes=taxes,
            udf=udf,
            convenience_fee=convenience_fee,
            total_fare=total_fare,
            availability_status="available",
        )

    def generate_range(self, start: date, end: date) -> list[FareRecord]:
        """Inclusive of start and end."""
        records: list[FareRecord] = []
        current = start
        while current <= end:
            records.extend(self.generate_for_day(current))
            current += timedelta(days=1)
        return records
