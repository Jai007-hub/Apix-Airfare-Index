import { useEffect, useMemo, useState } from "react";

import { api, HeatmapResponse } from "../api/client";
import { chart, sequentialColor, sequentialTextColor } from "../chartTheme";

type Frequency = "daily" | "weekly" | "monthly";
const FREQUENCIES: Frequency[] = ["daily", "weekly", "monthly"];

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export default function SectorHeatmap() {
  const [frequency, setFrequency] = useState<Frequency>("weekly");
  const [start, setStart] = useState(isoDaysAgo(90));
  const [end, setEnd] = useState(isoDaysAgo(0));
  const [data, setData] = useState<HeatmapResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Bounds come from the index series itself, so the pickers can never offer a
  // date the database has no fares for.
  const [bounds, setBounds] = useState<{ min: string; max: string } | null>(null);

  useEffect(() => {
    api
      .getIndex("daily")
      .then((series) => {
        if (series.length) {
          setBounds({
            min: series[0].period_date,
            max: series[series.length - 1].period_date,
          });
        }
      })
      .catch(() => setBounds(null));
  }, []);

  useEffect(() => {
    setError(null);
    api
      .getHeatmap(start, end, frequency)
      .then(setData)
      .catch((e) => setError(String(e)));
  }, [start, end, frequency]);

  const { min, max } = useMemo(() => {
    if (!data) return { min: 0, max: 1 };
    const values = Object.values(data.matrix).flatMap((row) => Object.values(row));
    if (!values.length) return { min: 0, max: 1 };
    return { min: Math.min(...values), max: Math.max(...values) };
  }, [data]);

  return (
    <div>
      <div className="page-head">
        <h2>Sector-wise Heatmap</h2>
        <p>
          Average all-inclusive fare (₹) for each route, by period. Rows are city-pairs, columns are
          time periods; the darker the cell, the more expensive that sector was.
        </p>
      </div>

      <div className="card">
        <h3>
          Average total fare<span className="sub">₹, includes taxes, UDF &amp; fees</span>
        </h3>

        <div className="controls">
          <div className="seg" role="group" aria-label="Heatmap frequency">
            {FREQUENCIES.map((f) => (
              <button key={f} onClick={() => setFrequency(f)} aria-pressed={frequency === f}>
                {f}
              </button>
            ))}
          </div>
          <label>
            From
            <input
              type="date"
              value={start}
              min={bounds?.min}
              max={bounds?.max}
              onChange={(e) => setStart(e.target.value)}
            />
          </label>
          <label>
            To
            <input
              type="date"
              value={end}
              min={bounds?.min}
              max={bounds?.max}
              onChange={(e) => setEnd(e.target.value)}
            />
          </label>
          {bounds && (
            <span className="hint-inline" style={{ marginLeft: 2 }}>
              data available {bounds.min} to {bounds.max}
            </span>
          )}
        </div>

        {error && <div className="error">{error}</div>}
        {!data && !error && <div className="loading">Loading heatmap…</div>}
        {data && data.routes.length === 0 && (
          <div className="empty">No fare data in this date range.</div>
        )}

        {data && data.routes.length > 0 && (
          <>
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
                        if (value == null) {
                          return <td key={p} className="heatmap-cell" />;
                        }
                        return (
                          <td
                            key={p}
                            className="heatmap-cell"
                            style={{
                              background: sequentialColor(value, min, max),
                              color: sequentialTextColor(value, min, max),
                            }}
                            title={`${route} · ${p} · ₹${Math.round(value).toLocaleString("en-IN")}`}
                          >
                            {Math.round(value).toLocaleString("en-IN")}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="legend-scale">
              <span>₹{Math.round(min).toLocaleString("en-IN")}</span>
              <span className="swatches">
                {chart.sequential.map((c) => (
                  <i key={c} style={{ background: c }} />
                ))}
              </span>
              <span>₹{Math.round(max).toLocaleString("en-IN")}</span>
              <span style={{ marginLeft: 4 }}>cheapest (pale) → most expensive (dark)</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
