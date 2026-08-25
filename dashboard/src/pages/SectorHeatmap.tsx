import { useEffect, useMemo, useState } from "react";

import { api, HeatmapResponse } from "../api/client";

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function colorFor(value: number, min: number, max: number): string {
  const t = max > min ? (value - min) / (max - min) : 0.5;
  // cool blue (cheap) -> warm red (expensive)
  const hue = 210 - t * 210; // 210 = blue, 0 = red
  return `hsl(${hue}, 70%, 55%)`;
}

type Frequency = "daily" | "weekly" | "monthly";

export default function SectorHeatmap() {
  const [frequency, setFrequency] = useState<Frequency>("weekly");
  const [start, setStart] = useState(isoDaysAgo(90));
  const [end, setEnd] = useState(isoDaysAgo(0));
  const [data, setData] = useState<HeatmapResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getHeatmap(start, end, frequency)
      .then(setData)
      .catch((e) => setError(String(e)));
  }, [start, end, frequency]);

  const { min, max } = useMemo(() => {
    if (!data) return { min: 0, max: 1 };
    const values = Object.values(data.matrix).flatMap((row) => Object.values(row));
    return { min: Math.min(...values), max: Math.max(...values) };
  }, [data]);

  return (
    <div>
      <h2>Sector-wise Heatmap</h2>
      <p style={{ color: "var(--muted)", marginTop: -8 }}>
        Rows (Y) = route, columns (X) = time period. Each cell = average total fare (INR) for that route in that
        period; color scales from cheapest (blue) to most expensive (red).
      </p>

      <div className="card">
        <div className="controls">
          <label>
            Start{" "}
            <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
          </label>
          <label>
            End{" "}
            <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
          </label>
          {(["daily", "weekly", "monthly"] as Frequency[]).map((f) => (
            <button
              key={f}
              onClick={() => setFrequency(f)}
              style={{
                background: frequency === f ? "var(--accent)" : "transparent",
                color: frequency === f ? "#0b0f18" : "var(--text)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                padding: "6px 14px",
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              {f}
            </button>
          ))}
        </div>

        {error && <div className="error">{error}</div>}
        {!data && !error && <div className="loading">Loading...</div>}

        {data && data.routes.length > 0 && (
          <div className="heatmap-table">
            <table>
              <thead>
                <tr>
                  <th>Route</th>
                  {data.periods.map((p) => (
                    <th key={p}>{p}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.routes.map((route) => (
                  <tr key={route}>
                    <td>{route}</td>
                    {data.periods.map((p) => {
                      const value = data.matrix[route]?.[p];
                      return (
                        <td
                          key={p}
                          className="heatmap-cell"
                          style={{ background: value != null ? colorFor(value, min, max) : "transparent" }}
                        >
                          {value != null ? Math.round(value).toLocaleString() : ""}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && data.routes.length === 0 && <div className="loading">No data in this range.</div>}
      </div>
    </div>
  );
}
