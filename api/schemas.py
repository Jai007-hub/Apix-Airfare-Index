from datetime import date

from pydantic import BaseModel


class IndexPoint(BaseModel):
    period_date: date
    apix_value: float


class RouteInfo(BaseModel):
    label: str
    origin: str
    destination: str
    dgca_weight: float


class FarePoint(BaseModel):
    observation_date: date
    route_label: str
    carrier_code: str | None
    advance_window_days: int
    median_base_fare: float
    median_taxes: float
    median_total_fare: float
    n_obs: int
    n_excluded_outliers: int
    n_sold_out: int


class HeatmapResponse(BaseModel):
    periods: list[str]
    routes: list[str]
    matrix: dict[str, dict[str, float]]


class ElasticityPoint(BaseModel):
    advance_window_days: int
    avg_fare: float | None


class ValidationPoint(BaseModel):
    year: int
    month: int
    apix_value_rebased: float
    cpi_airfare_value: float
    pct_diff: float


class ValidationSummary(BaseModel):
    n_months_compared: int
    mape_pct: float
    pearson_correlation: float | None
    points: list[ValidationPoint]
