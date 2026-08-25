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
  mape_pct: number;
  pearson_correlation: number | null;
  points: ValidationPoint[];
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
  getHeatmap: (start: string, end: string, frequency: "daily" | "weekly" | "monthly" = "weekly") => {
    const params = new URLSearchParams({ start, end, frequency });
    return getJSON<HeatmapResponse>(`/api/v1/heatmap?${params.toString()}`);
  },
  getElasticity: (start: string, end: string) => {
    const params = new URLSearchParams({ start, end });
    return getJSON<ElasticityResponse>(`/api/v1/elasticity?${params.toString()}`);
  },
  getValidation: () => getJSON<ValidationSummary>("/api/v1/validation"),
};
