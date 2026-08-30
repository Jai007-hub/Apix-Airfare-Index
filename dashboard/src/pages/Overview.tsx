import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { api, IndexPoint } from "../api/client";
import { axisProps, chart, tooltipStyle } from "../chartTheme";

type Frequency = "daily" | "weekly" | "monthly";
const FREQUENCIES: Frequency[] = ["daily", "weekly", "monthly"];

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
  const pctChange = first && last ? ((last - first) / first) * 100 : null;
  const peak = data.length ? Math.max(...data.map((d) => d.apix_value)) : null;

  return (
    <div>
      <div className="page-head">
        <h2>Airfare Price Index (APIx)</h2>
        <p>
          A fixed-basket index across ten DGCA-weighted city-pairs, normalised so the first observed
          period equals 100. Movement above 100 means the basket costs more than it did at the base
          period.
        </p>
      </div>

      <div className="stat-row">
        <div className="stat">
          <div className="label">Latest value</div>
          <div className="value">{last ? last.toFixed(2) : "—"}</div>
          <div className="hint">{frequency} frequency</div>
        </div>
        <div className="stat">
          <div className="label">Change over window</div>
          <div className={`value ${pctChange !== null ? (pctChange >= 0 ? "up" : "down") : ""}`}>
            {pctChange !== null
              ? `${pctChange >= 0 ? "+" : ""}${pctChange.toFixed(2)}%`
              : "—"}
          </div>
          <div className="hint">First to latest period</div>
        </div>
        <div className="stat">
          <div className="label">Peak</div>
          <div className="value">{peak ? peak.toFixed(2) : "—"}</div>
          <div className="hint">Highest index reading</div>
        </div>
        <div className="stat">
          <div className="label">Data points</div>
          <div className="value">{data.length}</div>
          <div className="hint">Periods in series</div>
        </div>
      </div>

      <div className="card">
        <h3>
          Index trend<span className="sub">base period = 100</span>
        </h3>

        <div className="controls">
          <div className="seg" role="group" aria-label="Index frequency">
            {FREQUENCIES.map((f) => (
              <button key={f} onClick={() => setFrequency(f)} aria-pressed={frequency === f}>
                {f}
              </button>
            ))}
          </div>
        </div>

        {loading && <div className="loading">Loading index…</div>}
        {error && <div className="error">{error}</div>}
        {!loading && !error && data.length === 0 && (
          <div className="empty">No index values for this frequency yet.</div>
        )}

        {!loading && !error && data.length > 0 && (
          <ResponsiveContainer width="100%" height={380}>
            <LineChart data={data} margin={{ top: 8, right: 18, bottom: 26, left: 8 }}>
              <CartesianGrid stroke={chart.grid} vertical={false} />
              <XAxis
                dataKey="period_date"
                {...axisProps}
                minTickGap={44}
                label={{
                  value: `Period (${frequency})`,
                  position: "insideBottom",
                  offset: -16,
                  fill: chart.axis,
                  fontSize: 12,
                }}
              />
              <YAxis
                {...axisProps}
                domain={["auto", "auto"]}
                width={58}
                label={{
                  value: "Index (base = 100)",
                  angle: -90,
                  position: "insideLeft",
                  style: { textAnchor: "middle", fill: chart.axis, fontSize: 12 },
                }}
              />
              <Tooltip
                contentStyle={tooltipStyle}
                cursor={{ stroke: chart.axisLine, strokeDasharray: "3 3" }}
                formatter={(v: number) => [v.toFixed(2), "APIx"]}
              />
              <Line
                type="monotone"
                dataKey="apix_value"
                name="APIx"
                stroke={chart.series1}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 2, stroke: chart.surface }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
