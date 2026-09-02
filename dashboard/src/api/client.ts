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
  /** Which booking portal this matrix is for, or null for all of them. */
  source: string | null;
}

export interface SourceInfo {
  name: string;
  source_type: "airline" | "ota";
  base_url: string;
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

export interface DirectionalAgreement {
  /** Month-on-month moves where APIx and CPI went the same way. */
  matches: number;
  /** n months give n-1 moves, so this is one less than the point count. */
  comparisons: number;
  pct: number;
}

export interface DeviationMonth {
  year: number;
  month: number;
  abs_pct: number;
}

export interface DeviationProfile {
  median_abs_pct: number;
  best_month: DeviationMonth;
  worst_month: DeviationMonth;
  within_5pct: number;
  /** Comparable months -- one fewer than the point count, see below. */
  n: number;
  /** Rebasing forces the first month to 0% deviation, so it is left out. */
  excludes_rebase_anchor: boolean;
}

export interface ValidationSummary {
  n_months_compared: number;
  days_covered: number;
  window_start: string;
  window_end: string;
  mape_pct: number;
  pearson_correlation: number | null;
  directional_agreement: DirectionalAgreement | null;
  deviation_profile: DeviationProfile | null;
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
  /** Cheapest and dearest single quote seen at this window. */
  low: number;
  high: number;
  /** Share of searches at this window that came back with no seats. */
  sold_out_pct: number;
}

export interface FareBreakdown {
  base_fare: number;
  taxes: number;
  udf: number;
  convenience_fee: number;
}

export interface MonthFare {
  month: number;
  name: string;
  fare: number;
}

export interface LeaderboardRow {
  route: string;
  origin: string;
  destination: string;
  best_fare: number;
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
  fare_breakdown: FareBreakdown;
  carriers: CarrierFare[];
  /** Airline ranking at every booking window, keyed by window days as a
   *  string (JSON object keys). Each list holds its window constant. */
  carriers_by_window: Record<string, CarrierFare[]>;
  months: MonthFare[];
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
  getHeatmap: (
    start: string,
    end: string,
    frequency: "daily" | "weekly" | "monthly" = "weekly",
    source?: string,
  ) => {
    const params = new URLSearchParams({ start, end, frequency });
    if (source) params.set("source", source);
    return getJSON<HeatmapResponse>(`/api/v1/heatmap?${params.toString()}`);
  },
  getSources: () => getJSON<SourceInfo[]>("/api/v1/sources"),
  getElasticity: (start: string, end: string) => {
    const params = new URLSearchParams({ start, end });
    return getJSON<ElasticityResponse>(`/api/v1/elasticity?${params.toString()}`);
  },
  getValidation: () => getJSON<ValidationSummary>("/api/v1/validation"),
  getTraveller: (routeLabel: string) =>
    getJSON<TravellerSummary>(`/api/v1/traveller/${encodeURIComponent(routeLabel)}`),
  getRouteLeaderboard: () => getJSON<LeaderboardRow[]>("/api/v1/traveller"),
};
