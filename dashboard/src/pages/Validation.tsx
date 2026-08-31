import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api, ValidationSummary } from "../api/client";
import { axisProps, chart, tooltipStyle } from "../chartTheme";

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
      <div className="page-head">
        <h2>Validation vs Official CPI</h2>
        <p>
          The computed monthly APIx, rebased to match the CPI level in the first overlapping month,
          against MoSPI's official All-India "Passenger transport by air, domestic" sub-index. Because
          the two series use different base periods, the comparison tests <em>trend</em>, not level.
          CPI is only published monthly, so the back-test window spans many days but compares at
          monthly points.
        </p>
      </div>

      {error && <div className="error">{error}</div>}
      {!data && !error && <div className="loading">Loading back-test…</div>}

      {data && (
        <>
          <div className="stat-row">
            <div className="stat">
              <div className="label">Days back-tested</div>
              <div className="value">
                {data.days_covered.toLocaleString("en-IN")}
                {data.days_covered >= 30 && (
                  <span className="req-met" title="Problem statement requires at least 30 days">
                    ✓ ≥30 required
                  </span>
                )}
              </div>
              <div className="hint">
                {data.window_start} to {data.window_end}
              </div>
            </div>
            <div className="stat">
              <div className="label">Comparison points</div>
              <div className="value">{data.n_months_compared}</div>
              <div className="hint">CPI is published monthly</div>
            </div>
            <div className="stat">
              <div className="label">MAPE</div>
              <div className="value">{data.mape_pct.toFixed(2)}%</div>
              <div className="hint">Mean absolute % difference</div>
            </div>
            <div className="stat">
              <div className="label">Correlation</div>
              <div className="value">{data.pearson_correlation?.toFixed(3) ?? "—"}</div>
              <div className="hint">Pearson r, APIx vs CPI</div>
            </div>
          </div>

          <div className="card">
            <h3>
              APIx vs CPI airfare index<span className="sub">by month, rebased</span>
            </h3>
            <ResponsiveContainer width="100%" height={380}>
              <LineChart data={chartData} margin={{ top: 8, right: 18, bottom: 26, left: 8 }}>
                <CartesianGrid stroke={chart.grid} vertical={false} />
                <Legend verticalAlign="top" align="left" height={30} iconType="plainline" wrapperStyle={{ fontSize: 13 }} />
                <XAxis
                  dataKey="label"
                  {...axisProps}
                  label={{
                    value: "Month",
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
                  formatter={(v: number) => v.toFixed(2)}
                />
                <Line
                  type="monotone"
                  dataKey="APIx"
                  stroke={chart.series1}
                  strokeWidth={2}
                  dot={{ r: 3, fill: chart.series1, strokeWidth: 2, stroke: chart.surface }}
                  activeDot={{ r: 5, strokeWidth: 2, stroke: chart.surface }}
                />
                <Line
                  type="monotone"
                  dataKey="CPI"
                  stroke={chart.series2}
                  strokeWidth={2}
                  dot={{ r: 3, fill: chart.series2, strokeWidth: 2, stroke: chart.surface }}
                  activeDot={{ r: 5, strokeWidth: 2, stroke: chart.surface }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="card">
            <h3>Month-by-month detail</h3>
            <table>
              <thead>
                <tr>
                  <th>Month</th>
                  <th>APIx (rebased)</th>
                  <th>CPI airfare index</th>
                  <th>Difference</th>
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
                    <td className={Math.abs(p.pct_diff) > 5 ? "up" : ""}>
                      {p.pct_diff >= 0 ? "+" : ""}
                      {p.pct_diff.toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="note">
            <span aria-hidden="true">ⓘ</span>
            <span>
              <strong>Reading these numbers honestly.</strong> This back-test runs on synthetic fare
              data whose pricing rules were written independently of the CPI file — so a low
              correlation is the expected result of comparing two unrelated series, not evidence the
              method fails. What it does validate is that the pipeline, rebasing and comparison maths
              are correct end to end. Feed the same pipeline real scraped fares and this page becomes
              a genuine accuracy test.
            </span>
          </div>
        </>
      )}
    </div>
  );
}
