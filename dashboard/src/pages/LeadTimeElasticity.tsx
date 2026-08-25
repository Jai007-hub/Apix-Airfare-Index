import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { api, ElasticityResponse } from "../api/client";

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
        const first = Object.keys(d)[0];
        if (first) setRoute(first);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const chartData = useMemo(() => {
    if (!data || !route) return [];
    return data[route].map((p) => ({ ...p, label: `T+${p.advance_window_days}` }));
  }, [data, route]);

  return (
    <div>
      <h2>Lead-Time Elasticity</h2>
      <p style={{ color: "var(--muted)", marginTop: -8 }}>
        How average fare changes with advance-purchase window, by route.
      </p>

      <div className="card">
        <div className="controls">
          <select value={route} onChange={(e) => setRoute(e.target.value)}>
            {data &&
              Object.keys(data).map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
          </select>
        </div>

        {error && <div className="error">{error}</div>}
        {!data && !error && <div className="loading">Loading...</div>}

        {chartData.length > 0 && (
          <ResponsiveContainer width="100%" height={380}>
            <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a3348" />
              <XAxis
                dataKey="label"
                stroke="#93a0b8"
                fontSize={12}
                label={{ value: "Advance-purchase window (days before departure)", position: "insideBottom", offset: -5, fill: "#93a0b8", fontSize: 12 }}
              />
              <YAxis
                stroke="#93a0b8"
                fontSize={12}
                domain={["auto", "auto"]}
                label={{ value: "Average total fare (INR)", angle: -90, position: "insideLeft", fill: "#93a0b8", fontSize: 12 }}
              />
              <Tooltip contentStyle={{ background: "#161d2e", border: "1px solid #2a3348" }} />
              <Line type="monotone" dataKey="avg_fare" stroke="#3ecf8e" strokeWidth={2} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
