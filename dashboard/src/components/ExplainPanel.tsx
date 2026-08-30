import { useEffect, useState } from "react";

import { api, ExplainResponse } from "../api/client";

interface Props {
  periodDate: string | null;
  onClose: () => void;
}

/** Slide-in audit trail for a single daily index value: which routes produced
 *  it, what each contributed in index points, what was dropped, and whether
 *  the underlying quotes were live or synthetic. */
export default function ExplainPanel({ periodDate, onClose }: Props) {
  const [data, setData] = useState<ExplainResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!periodDate) return;
    setLoading(true);
    setError(null);
    setData(null);
    api
      .explainIndex(periodDate)
      .then(setData)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [periodDate]);

  // Escape closes, matching the backdrop click.
  useEffect(() => {
    if (!periodDate) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [periodDate, onClose]);

  if (!periodDate) return null;

  const maxPoints = data ? Math.max(...data.routes.map((r) => r.contribution_points), 0.0001) : 1;

  return (
    <>
      <div className="explain-backdrop" onClick={onClose} />
      <aside className="explain-panel" role="dialog" aria-label="Index value breakdown">
        <header className="explain-head">
          <div>
            <div className="explain-eyebrow">Index breakdown</div>
            <h3>{periodDate}</h3>
          </div>
          <button className="explain-close" onClick={onClose} aria-label="Close breakdown">
            ✕
          </button>
        </header>

        {loading && <div className="loading">Reconstructing this value…</div>}
        {error && <div className="error">{error}</div>}

        {data && (
          <div className="explain-body">
            <div className="explain-hero">
              <span className="explain-hero-num">{data.apix_value.toFixed(2)}</span>
              <span className="explain-hero-meta">
                APIx on this date
                <br />
                base period {data.base_period_date} = 100
              </span>
            </div>

            <div className="explain-facts">
              <div>
                <span className="k">Routes used</span>
                <span className="v">
                  {data.routes_included} of {data.routes_total}
                </span>
              </div>
              <div>
                <span className="k">Basket weight covered</span>
                <span className="v">{(data.weight_coverage * 100).toFixed(0)}%</span>
              </div>
              <div>
                <span className="k">Fare quotes behind it</span>
                <span className="v">
                  {(
                    data.provenance.live_observations + data.provenance.synthetic_observations
                  ).toLocaleString("en-IN")}
                </span>
              </div>
              <div>
                <span className="k">Data source</span>
                <span className={`v tag ${data.provenance.pct_live > 0 ? "tag-live" : "tag-syn"}`}>
                  {data.provenance.pct_live > 0
                    ? `${data.provenance.pct_live}% live`
                    : "synthetic"}
                </span>
              </div>
            </div>

            <p className="explain-formula">
              Each route's price relative (today ÷ base) times its renormalised DGCA weight. The
              contributions below sum to exactly {data.apix_value.toFixed(2)}.
            </p>

            <ul className="explain-routes">
              {data.routes.map((r, i) => (
                <li
                  key={r.route}
                  className="explain-route"
                  style={{ animationDelay: `${Math.min(i * 45, 400)}ms` }}
                >
                  <div className="er-top">
                    <span className="er-name">{r.route}</span>
                    <span className="er-points">{r.contribution_points.toFixed(2)} pts</span>
                  </div>

                  <div className="er-bar">
                    <span
                      className="er-fill"
                      style={{ width: `${(r.contribution_points / maxPoints) * 100}%` }}
                    />
                  </div>

                  <div className="er-detail">
                    <span>
                      ₹{Math.round(r.base_fare).toLocaleString("en-IN")} →{" "}
                      <strong>₹{Math.round(r.current_fare).toLocaleString("en-IN")}</strong>
                    </span>
                    <span className={r.pct_change_vs_base >= 0 ? "up" : "down"}>
                      {r.pct_change_vs_base >= 0 ? "▲" : "▼"}{" "}
                      {Math.abs(r.pct_change_vs_base).toFixed(1)}%
                    </span>
                  </div>

                  <div className="er-meta">
                    weight {(r.weight_normalised * 100).toFixed(1)}% · {r.n_obs} quotes ·{" "}
                    {r.carriers.length} carriers
                    {r.n_outliers_excluded > 0 && (
                      <span className="er-flag"> · {r.n_outliers_excluded} outliers removed</span>
                    )}
                    {r.n_sold_out > 0 && <span className="er-flag"> · {r.n_sold_out} sold out</span>}
                  </div>
                </li>
              ))}
            </ul>

            {data.excluded_routes.length > 0 && (
              <div className="explain-excluded">
                <h4>Excluded from this day</h4>
                {data.excluded_routes.map((e) => (
                  <div key={e.route} className="ex-row">
                    <span className="ex-name">{e.route}</span>
                    <span className="ex-reason">{e.reason}</span>
                  </div>
                ))}
                <p className="ex-note">
                  Their weight was redistributed across the remaining routes, so a data gap shifts
                  coverage rather than silently dropping the index.
                </p>
              </div>
            )}
          </div>
        )}
      </aside>
    </>
  );
}
