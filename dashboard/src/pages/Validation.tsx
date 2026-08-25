import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { api, ValidationSummary } from "../api/client";

export default function Validation() {
  const [data, setData] = useState<ValidationSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getValidation()
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  const chartData = data?.points.map((p) => ({
    label: `${p.year}-${String(p.month).padStart(2, "0")}`,
    APIx: p.apix_value_rebased,
    CPI: p.cpi_airfare_value,
  }));

  return (
    <div>
      <h2>Validation vs Official CPI Airfare Sub-Index</h2>
      <p style={{ color: "var(--muted)", marginTop: -8 }}>
        Computed monthly APIx (rebased to the CPI's level in the first overlapping month) compared against
        MoSPI's "Passenger transport by air, domestic" CPI sub-index.
      </p>

      {error && <div className="error">{error}</div>}
      {!data && !error && <div className="loading">Loading...</div>}

      {data && (
        <>
          <div className="stat-row" style={{ marginBottom: 24 }}>
            <div className="stat">
              <div className="label">Months compared</div>
              <div className="value">{data.n_months_compared}</div>
            </div>
            <div className="stat">
              <div className="label">MAPE</div>
              <div className="value">{data.mape_pct.toFixed(2)}%</div>
            </div>
            <div className="stat">
              <div className="label">Pearson correlation</div>
              <div className="value">{data.pearson_correlation?.toFixed(3) ?? "--"}</div>
            </div>
          </div>

          <div className="card">
            <h3>APIx vs CPI, by month</h3>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={chartData} margin={{ top: 10, right: 24, bottom: 30, left: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a3348" />
                <Legend verticalAlign="top" height={32} wrapperStyle={{ fontSize: 12 }} />
                <XAxis
                  dataKey="label"
                  stroke="#93a0b8"
                  fontSize={12}
                  label={{ value: "Month", position: "insideBottom", offset: -15, fill: "#93a0b8", fontSize: 12 }}
                />
                <YAxis
                  stroke="#93a0b8"
                  fontSize={12}
                  domain={["auto", "auto"]}
                  label={{ value: "Index value (base = 100)", angle: -90, position: "left", offset: 10, style: { textAnchor: "middle" }, fill: "#93a0b8", fontSize: 12 }}
                />
                <Tooltip contentStyle={{ background: "#161d2e", border: "1px solid #2a3348" }} />
                <Line type="monotone" dataKey="APIx" stroke="#5b8cff" strokeWidth={2} />
                <Line type="monotone" dataKey="CPI" stroke="#3ecf8e" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="card">
            <h3>Detail</h3>
            <table>
              <thead>
                <tr>
                  <th>Month</th>
                  <th>APIx (rebased)</th>
                  <th>CPI airfare index</th>
                  <th>Diff %</th>
                </tr>
              </thead>
              <tbody>
                {data.points.map((p) => (
                  <tr key={`${p.year}-${p.month}`}>
                    <td>
                      {p.year}-{String(p.month).padStart(2, "0")}
                    </td>
                    <td>{p.apix_value_rebased.toFixed(2)}</td>
                    <td>{p.cpi_airfare_value.toFixed(2)}</td>
                    <td style={{ color: Math.abs(p.pct_diff) > 5 ? "var(--bad)" : "var(--good)" }}>
                      {p.pct_diff.toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
