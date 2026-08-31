const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export interface IndexPoint {
  period_date: string;
  apix_value: number;
}

export interface RouteInfo {
  label: string;
  origin: string;
  destination: string;
  dgca_weight: number;
}

export interface HeatmapResponse {
  periods: string[];
  routes: string[];
  matrix: Record<string, Record<string, number>>;
}

export interface ElasticityPoint {
  advance_window_days: number;
  avg_fare: number | null;
}

export type ElasticityResponse = Record<string, ElasticityPoint[]>;

export interface ValidationPoint {
  year: number;
  month: number;
  apix_value_rebased: number;
  cpi_airfare_value: number;
  pct_diff: number;
}

export interface ValidationSummary {
  n_months_compared: number;
  days_covered: number;
  window_start: string;
  window_end: string;
  mape_pct: number;
  pearson_correlation: number | null;
  points: ValidationPoint[];
}

export interface ExplainRoute {
  route: string;
  weight: number;
  weight_normalised: number;
  base_date: string;
  base_fare: number;
  current_fare: number;
  price_relative: number;
  pct_change_vs_base: number;
  contribution_points: number;
  n_obs: number;
  n_outliers_excluded: number;
  n_sold_out: number;
  carriers: string[];
  live_observations: number;
  synthetic_observations: number;
}

export interface ExplainResponse {
  period_date: string;
  frequency: string;
  apix_value: number;
  base_period_date: string;
  routes_included: number;
  routes_total: number;
  weight_coverage: number;
  routes: ExplainRoute[];
  excluded_routes: { route: string; weight: number; reason: string }[];
  provenance: {
    live_observations: number;
    synthetic_observations: number;
    pct_live: number;
  };
}

export interface FareWindow {
  window_days: number;
  fare: number;
}

export interface CarrierFare {
  code: string;
  name: string;
  fare: number;
}

/** Consumer-facing summary of one route -- powers the phone view. */
export interface TravellerSummary {
  route: string;
  origin: string;
  destination: string;
  as_of: string;
  typical_fare: number;
  cheapest_window: FareWindow;
  dearest_window: FareWindow;
  max_saving: number;
  max_saving_pct: number;
  windows: FareWindow[];
  carriers: CarrierFare[];
  trend_pct: number | null;
  trend_direction: "up" | "down" | "flat";
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`GET ${path} failed: ${res.status} ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getIndex: (frequency: "daily" | "weekly" | "monthly", start?: string, end?: string) => {
    const params = new URLSearchParams({ frequency });
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    return getJSON<IndexPoint[]>(`/api/v1/index?${params.toString()}`);
  },
  getRoutes: () => getJSON<RouteInfo[]>("/api/v1/routes"),
  explainIndex: (periodDate: string) =>
    getJSON<ExplainResponse>(`/api/v1/index/explain?period_date=${periodDate}`),
  getHeatmap: (start: string, end: string, frequency: "daily" | "weekly" | "monthly" = "weekly") => {
    const params = new URLSearchParams({ start, end, frequency });
    return getJSON<HeatmapResponse>(`/api/v1/heatmap?${params.toString()}`);
  },
  getElasticity: (start: string, end: string) => {
    const params = new URLSearchParams({ start, end });
    return getJSON<ElasticityResponse>(`/api/v1/elasticity?${params.toString()}`);
  },
  getValidation: () => getJSON<ValidationSummary>("/api/v1/validation"),
  getTraveller: (routeLabel: string) =>
    getJSON<TravellerSummary>(`/api/v1/traveller/${encodeURIComponent(routeLabel)}`),
};
