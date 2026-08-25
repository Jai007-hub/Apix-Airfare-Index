import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { api, IndexPoint } from "../api/client";

type Frequency = "daily" | "weekly" | "monthly";

export default function Overview() {
  const [frequency, setFrequency] = useState<Frequency>("daily");
  const [data, setData] = useState<IndexPoint[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .getIndex(frequency)
      .then(setData)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [frequency]);

  const first = data[0]?.apix_value;
  const last = data[data.length - 1]?.apix_value;
  const pctChange = first && last ? (((last - first) / first) * 100).toFixed(2) : null;

  return (
    <div>
      <h2>Airfare Price Index (APIx)</h2>
      <p style={{ color: "var(--muted)", marginTop: -8 }}>
        DGCA-traffic-weighted index across the city-pair basket. Base period = 100.
      </p>

      <div className="stat-row" style={{ marginBottom: 24 }}>
        <div className="stat">
          <div className="label">Latest APIx ({frequency})</div>
          <div className="value">{last ? last.toFixed(2) : "--"}</div>
        </div>
        <div className="stat">
          <div className="label">Change over period</div>
          <div className="value" style={{ color: pctChange && Number(pctChange) >= 0 ? "var(--bad)" : "var(--good)" }}>
            {pctChange ? `${pctChange}%` : "--"}
          </div>
        </div>
        <div className="stat">
          <div className="label">Data points</div>
          <div className="value">{data.length}</div>
        </div>
      </div>

      <div className="card">
        <h3>Index trend</h3>
        <div className="controls">
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

        {loading && <div className="loading">Loading...</div>}
        {error && <div className="error">{error}</div>}
        {!loading && !error && data.length > 0 && (
          <ResponsiveContainer width="100%" height={380}>
            <LineChart data={data} margin={{ top: 5, right: 20, bottom: 20, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a3348" />
              <XAxis
                dataKey="period_date"
                stroke="#93a0b8"
                fontSize={12}
                label={{ value: `Date (${frequency})`, position: "insideBottom", offset: -5, fill: "#93a0b8", fontSize: 12 }}
              />
              <YAxis
                stroke="#93a0b8"
                fontSize={12}
                domain={["auto", "auto"]}
                label={{ value: "APIx (base period = 100)", angle: -90, position: "insideLeft", fill: "#93a0b8", fontSize: 12 }}
              />
              <Tooltip contentStyle={{ background: "#161d2e", border: "1px solid #2a3348" }} />
              <Line type="monotone" dataKey="apix_value" stroke="#5b8cff" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
