"""SQLAlchemy models for the Airfare Price Index (APIx) prototype.

Layer summary:
  CityPair / Carrier / Source -> reference/dimension tables (the basket).
  RawObservation              -> one row per scraped/synthetic fare quote, immutable.
  CleanFare                   -> daily aggregate per (route, carrier, advance-window)
                                  produced by pipeline/clean.py from RawObservation.
  IndexValue                  -> computed APIx at daily/weekly/monthly frequency.
  ValidationResult            -> APIx vs official CPI airfare sub-index, per month.
"""
import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class CarrierType(str, enum.Enum):
    LCC = "LCC"
    FSC = "FSC"


class SourceType(str, enum.Enum):
    AIRLINE = "airline"
    OTA = "ota"


class AvailabilityStatus(str, enum.Enum):
    AVAILABLE = "available"
    SOLD_OUT = "sold_out"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class DataSourceType(str, enum.Enum):
    LIVE = "live"
    SYNTHETIC_FALLBACK = "synthetic_fallback"


class CityPair(Base):
    __tablename__ = "city_pairs"

    id = Column(Integer, primary_key=True)
    origin = Column(String(3), nullable=False)
    destination = Column(String(3), nullable=False)
    label = Column(String(16), nullable=False, unique=True)  # e.g. "DEL-BOM"
    dgca_weight = Column(Float, nullable=False)  # basket weight, sums to 1.0 across active pairs
    is_active = Column(Boolean, default=True, nullable=False)

    raw_observations = relationship("RawObservation", back_populates="route")
    clean_fares = relationship("CleanFare", back_populates="route")


class Carrier(Base):
    __tablename__ = "carriers"

    id = Column(Integer, primary_key=True)
    code = Column(String(8), nullable=False, unique=True)  # e.g. "6E"
    name = Column(String(64), nullable=False)
    carrier_type = Column(Enum(CarrierType), nullable=False)

    raw_observations = relationship("RawObservation", back_populates="carrier")
    clean_fares = relationship("CleanFare", back_populates="carrier")


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, unique=True)  # e.g. "makemytrip"
    source_type = Column(Enum(SourceType), nullable=False)
    base_url = Column(String(256), nullable=False)
    robots_txt_url = Column(String(256), nullable=True)

    raw_observations = relationship("RawObservation", back_populates="source")


class RawObservation(Base):
    """One scraped/synthetic fare quote. Immutable — never updated in place."""

    __tablename__ = "raw_observations"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "route_id",
            "carrier_id",
            "flight_number",
            "fare_class",
            "observation_date",
            "departure_date",
            name="uq_raw_observation_identity",
        ),
    )

    id = Column(Integer, primary_key=True)
    scraped_at = Column(DateTime, nullable=False)
    observation_date = Column(Date, nullable=False)  # date(scraped_at), indexed for grouping
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("city_pairs.id"), nullable=False)
    carrier_id = Column(Integer, ForeignKey("carriers.id"), nullable=True)

    flight_number = Column(String(16), nullable=True)
    departure_date = Column(Date, nullable=False)
    advance_window_days = Column(Integer, nullable=False)  # T+1, T+7, T+15, T+30, T+45
    fare_class = Column(String(16), nullable=True)  # e.g. "Economy"

    base_fare = Column(Float, nullable=True)
    taxes = Column(Float, nullable=True)
    udf = Column(Float, nullable=True)
    convenience_fee = Column(Float, nullable=True)
    total_fare = Column(Float, nullable=True)
    currency = Column(String(3), nullable=False, default="INR")

    availability_status = Column(
        Enum(AvailabilityStatus), nullable=False, default=AvailabilityStatus.UNKNOWN
    )
    data_source_type = Column(Enum(DataSourceType), nullable=False)
    raw_payload = Column(Text, nullable=True)  # original JSON, for audit/debugging

    source = relationship("Source", back_populates="raw_observations")
    route = relationship("CityPair", back_populates="raw_observations")
    carrier = relationship("Carrier", back_populates="raw_observations")


class CleanFare(Base):
    """Daily aggregate per (route, carrier, advance-window), post outlier removal."""

    __tablename__ = "clean_fares"
    __table_args__ = (
        UniqueConstraint(
            "observation_date",
            "route_id",
            "carrier_id",
            "advance_window_days",
            name="uq_clean_fare_identity",
        ),
    )

    id = Column(Integer, primary_key=True)
    observation_date = Column(Date, nullable=False)
    route_id = Column(Integer, ForeignKey("city_pairs.id"), nullable=False)
    carrier_id = Column(Integer, ForeignKey("carriers.id"), nullable=True)
    advance_window_days = Column(Integer, nullable=False)

    median_base_fare = Column(Float, nullable=False)
    median_taxes = Column(Float, nullable=False)
    median_total_fare = Column(Float, nullable=False)
    min_total_fare = Column(Float, nullable=False)
    max_total_fare = Column(Float, nullable=False)

    n_obs = Column(Integer, nullable=False)
    n_excluded_outliers = Column(Integer, nullable=False, default=0)
    n_sold_out = Column(Integer, nullable=False, default=0)

    route = relationship("CityPair", back_populates="clean_fares")
    carrier = relationship("Carrier", back_populates="clean_fares")


class IndexValue(Base):
    __tablename__ = "index_values"
    __table_args__ = (
        UniqueConstraint("frequency", "period_date", name="uq_index_value_identity"),
    )

    id = Column(Integer, primary_key=True)
    frequency = Column(String(8), nullable=False)  # "daily" | "weekly" | "monthly"
    period_date = Column(Date, nullable=False)  # anchor date for the period
    apix_value = Column(Float, nullable=False)
    base_period_date = Column(Date, nullable=False)
    route_breakdown = Column(Text, nullable=True)  # JSON: {route_label: avg_total_fare}


class ValidationResult(Base):
    __tablename__ = "validation_results"
    __table_args__ = (UniqueConstraint("period_month", name="uq_validation_month"),)

    id = Column(Integer, primary_key=True)
    period_month = Column(Date, nullable=False)  # first-of-month
    apix_value_rebased = Column(Float, nullable=False)
    cpi_airfare_value = Column(Float, nullable=False)
    pct_diff = Column(Float, nullable=False)
