import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { api, ElasticityResponse } from "../api/client";
import { axisProps, chart, tooltipStyle } from "../chartTheme";

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export default function LeadTimeElasticity() {
  const [data, setData] = useState<ElasticityResponse | null>(null);
  const [route, setRoute] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getElasticity(isoDaysAgo(90), isoDaysAgo(0))
      .then((d) => {
        setData(d);
        const firstRoute = Object.keys(d)[0];
        if (firstRoute) setRoute(firstRoute);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const chartData = useMemo(() => {
    if (!data || !route || !data[route]) return [];
    return data[route].map((p) => ({ ...p, label: `T+${p.advance_window_days}` }));
  }, [data, route]);

  // Headline: how much more a last-minute seat costs than the earliest window.
  const priced = chartData.filter((p) => p.avg_fare != null);
  const nearest = priced.length ? priced[0] : null;
  const furthest = priced.length ? priced[priced.length - 1] : null;
  const premium =
    nearest?.avg_fare && furthest?.avg_fare
      ? ((nearest.avg_fare - furthest.avg_fare) / furthest.avg_fare) * 100
      : null;

  return (
    <div>
      <div className="page-head">
        <h2>Lead-Time Elasticity</h2>
        <p>
          Average fare against how far ahead the ticket is bought. The steep left-hand climb is the
          dynamic-pricing effect that monthly manual collection misses entirely.
        </p>
      </div>

      <div className="stat-row">
        <div className="stat">
          <div className="label">T+1 fare</div>
          <div className="value">
            {nearest?.avg_fare ? `₹${Math.round(nearest.avg_fare).toLocaleString("en-IN")}` : "—"}
          </div>
          <div className="hint">Booked a day before departure</div>
        </div>
        <div className="stat">
          <div className="label">T+45 fare</div>
          <div className="value">
            {furthest?.avg_fare ? `₹${Math.round(furthest.avg_fare).toLocaleString("en-IN")}` : "—"}
          </div>
          <div className="hint">Booked 45 days ahead</div>
        </div>
        <div className="stat">
          <div className="label">Last-minute premium</div>
          <div className="value up">{premium !== null ? `+${premium.toFixed(0)}%` : "—"}</div>
          <div className="hint">T+1 versus T+45 on this route</div>
        </div>
      </div>

      <div className="card">
        <h3>
          Fare by advance-purchase window<span className="sub">{route || "—"}</span>
        </h3>

        <div className="controls">
          <label>
            Route
            <select value={route} onChange={(e) => setRoute(e.target.value)}>
              {data &&
                Object.keys(data).map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
            </select>
          </label>
        </div>

        {error && <div className="error">{error}</div>}
        {!data && !error && <div className="loading">Loading elasticity curve…</div>}
        {data && chartData.length === 0 && <div className="empty">No data for this route.</div>}

        {chartData.length > 0 && (
          <ResponsiveContainer width="100%" height={380}>
            <LineChart data={chartData} margin={{ top: 8, right: 18, bottom: 26, left: 14 }}>
              <CartesianGrid stroke={chart.grid} vertical={false} />
              <XAxis
                dataKey="label"
                {...axisProps}
                label={{
                  value: "Advance-purchase window (days before departure)",
                  position: "insideBottom",
                  offset: -16,
                  fill: chart.axis,
                  fontSize: 12,
                }}
              />
              <YAxis
                {...axisProps}
                domain={["auto", "auto"]}
                width={66}
                tickFormatter={(v: number) => `₹${(v / 1000).toFixed(1)}k`}
                label={{
                  value: "Average total fare",
                  angle: -90,
                  position: "insideLeft",
                  style: { textAnchor: "middle", fill: chart.axis, fontSize: 12 },
                }}
              />
              <Tooltip
                contentStyle={tooltipStyle}
                cursor={{ stroke: chart.axisLine, strokeDasharray: "3 3" }}
                formatter={(v: number) => [`₹${Math.round(v).toLocaleString("en-IN")}`, "Avg fare"]}
              />
              <Line
                type="monotone"
                dataKey="avg_fare"
                name="Average fare"
                stroke={chart.series1}
                strokeWidth={2}
                connectNulls
                dot={{ r: 4, fill: chart.series1, strokeWidth: 2, stroke: chart.surface }}
                activeDot={{ r: 6, strokeWidth: 2, stroke: chart.surface }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
