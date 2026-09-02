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

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

const monthLabel = (m: { year: number; month: number }) =>
  `${MONTHS[m.month - 1]} ${m.year}`;

export default function Validation() {
  const [data, setData] = useState<ValidationSummary | null>(null);
  const [openStat, setOpenStat] = useState<"mape" | "correlation" | null>(null);

  const toggle = (which: "mape" | "correlation") =>
    setOpenStat((current) => (current === which ? null : which));
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
            <button
              type="button"
              className={openStat === "mape" ? "stat stat-expandable is-open" : "stat stat-expandable"}
              onClick={() => toggle("mape")}
              aria-expanded={openStat === "mape"}
              aria-controls="mape-detail"
            >
              <div className="label">
                MAPE
                <span className="stat-more" aria-hidden="true">
                  {openStat === "mape" ? "−" : "?"}
                </span>
              </div>
              <div className="value">{data.mape_pct.toFixed(2)}%</div>
              <div className="hint">Mean absolute % difference — tap to read</div>
            </button>
            <button
              type="button"
              className={openStat === "correlation" ? "stat stat-expandable is-open" : "stat stat-expandable"}
              onClick={() => toggle("correlation")}
              aria-expanded={openStat === "correlation"}
              aria-controls="correlation-detail"
            >
              <div className="label">
                Correlation
                <span className="stat-more" aria-hidden="true">
                  {openStat === "correlation" ? "−" : "?"}
                </span>
              </div>
              <div className="value">{data.pearson_correlation?.toFixed(3) ?? "—"}</div>
              <div className="hint">Pearson r, APIx vs CPI — tap to read</div>
            </button>
          </div>

          {openStat === "mape" && (
            <div className="card correlation-detail" id="mape-detail">
              <h3>
                Reading the MAPE<span className="sub">average monthly deviation</span>
              </h3>
              <p className="corr-headline">
                <strong>Average monthly deviation from CPI:</strong>{" "}
                {data.mape_pct.toFixed(2)}% — the more reliable accuracy measure at
                this sample size.
              </p>
              <p>
                Each month, APIx (rebased) is compared against the CPI airfare
                sub-index and the gap taken as a percentage. MAPE is the mean of those
                gaps ignoring sign, so a month 8% high and a month 8% low both count
                as 8% off rather than cancelling out.
              </p>
              {data.deviation_profile && (
                <>
                  <ul className="corr-list">
                    <li>
                      <span>Median month</span>
                      <strong>{data.deviation_profile.median_abs_pct.toFixed(2)}%</strong>
                    </li>
                    <li>
                      <span>Closest month</span>
                      <strong>
                        {monthLabel(data.deviation_profile.best_month)} ·{" "}
                        {data.deviation_profile.best_month.abs_pct.toFixed(2)}%
                      </strong>
                    </li>
                    <li>
                      <span>Furthest month</span>
                      <strong>
                        {monthLabel(data.deviation_profile.worst_month)} ·{" "}
                        {data.deviation_profile.worst_month.abs_pct.toFixed(2)}%
                      </strong>
                    </li>
                    <li>
                      <span>Within 5% of CPI</span>
                      <strong>
                        {data.deviation_profile.within_5pct} of {data.deviation_profile.n}{" "}
                        months
                      </strong>
                    </li>
                  </ul>
                  <p className="corr-fine">
                    A mean hides its own shape, so the median and the extremes are shown
                    beside it. These exclude the first overlapping month: rebasing scales
                    APIx to match CPI exactly there, so its 0.00% deviation is an
                    arithmetic identity rather than a measure of accuracy.
                  </p>
                </>
              )}
              {data.error_metrics && (
                <>
                  <h4 className="corr-sub">Standard error measures</h4>
                  <ul className="corr-list">
                    <li>
                      <span>MAE</span>
                      <strong>
                        {data.error_metrics.mae_index_points.toFixed(2)} pts
                      </strong>
                    </li>
                    <li>
                      <span>RMSE</span>
                      <strong>
                        {data.error_metrics.rmse_index_points.toFixed(2)} pts
                      </strong>
                    </li>
                    <li>
                      <span>MSE</span>
                      <strong>
                        {data.error_metrics.mse_index_points.toFixed(1)}
                      </strong>
                    </li>
                    <li>
                      <span>Mean bias</span>
                      <strong>
                        {data.error_metrics.mean_bias_index_points >= 0 ? "+" : ""}
                        {data.error_metrics.mean_bias_index_points.toFixed(2)} pts
                      </strong>
                    </li>
                  </ul>
                  <p className="corr-fine">
                    In index points, the unit both series are expressed in. RMSE well
                    above MAE means the error sits in a few bad months rather than
                    spread evenly; bias near zero means the index wanders either side
                    of CPI rather than running consistently high or low. Classification
                    measures — accuracy, precision, F1 — do not apply: nothing here is
                    being sorted into classes.
                  </p>
                </>
              )}
            </div>
          )}

          {openStat === "correlation" && (
            <div className="card correlation-detail" id="correlation-detail">
              <h3>
                Reading the correlation<span className="sub">why r alone misleads here</span>
              </h3>
              {data.directional_agreement ? (
                <p className="corr-headline">
                  <strong>Directional agreement:</strong>{" "}
                  {data.directional_agreement.matches} out of{" "}
                  {data.directional_agreement.comparisons} month-on-month moves went
                  the same way as CPI ({data.directional_agreement.pct.toFixed(0)}%).
                </p>
              ) : (
                <p className="corr-headline">
                  <strong>Directional agreement:</strong> not enough months to compare
                  directions yet.
                </p>
              )}
              <p>
                Correlation can be unstable across {data.n_months_compared} data points
                — a single month's noise can swing it. MAPE ({data.mape_pct.toFixed(2)}%)
                is a more reliable measure of how closely APIx tracks CPI at this sample
                size.
              </p>
              <p className="corr-fine">
                {data.n_months_compared} monthly points give{" "}
                {data.n_months_compared - 1} month-on-month moves, which is why the
                denominator above is one less than the comparison-point count.
              </p>
            </div>
          )}

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
