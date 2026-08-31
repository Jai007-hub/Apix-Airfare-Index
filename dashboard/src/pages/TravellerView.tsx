import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, RouteInfo, TravellerSummary } from "../api/client";

/* Display names for the six airports in the basket. A traveller reads
   "Delhi to Mumbai"; only the analyst pages speak in IATA codes. */
const CITY: Record<string, string> = {
  DEL: "Delhi",
  BOM: "Mumbai",
  BLR: "Bengaluru",
  CCU: "Kolkata",
  HYD: "Hyderabad",
  MAA: "Chennai",
};

const cityName = (code: string) => CITY[code] ?? code;

const rupees = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

/** "45 days ahead" reads better than "T+45" outside a statistics office. */
const windowLabel = (days: number) =>
  days === 1 ? "1 day ahead" : `${days} days ahead`;

const prettyDate = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

export default function TravellerView() {
  const [routes, setRoutes] = useState<RouteInfo[] | null>(null);
  const [selected, setSelected] = useState<string>("DEL-BOM");
  const [summary, setSummary] = useState<TravellerSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getRoutes().then(setRoutes).catch(() => setRoutes([]));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setSummary(null);
    setError(null);
    api
      .getTraveller(selected)
      .then((s) => {
        if (!cancelled) setSummary(s);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load fares for this route.");
      });
    return () => {
      cancelled = true;
    };
  }, [selected]);

  const dearest = summary?.dearest_window.fare ?? 0;

  return (
    <div className="tv">
      <header className="tv-head">
        <h1>What should this flight cost?</h1>
        <p>
          Typical fares on India's busiest routes, and the booking window that
          costs the least.
        </p>
      </header>

      <label className="tv-picker">
        <span>Route</span>
        <select value={selected} onChange={(e) => setSelected(e.target.value)}>
          {(routes ?? []).map((r) => (
            <option key={r.label} value={r.label}>
              {cityName(r.origin)} → {cityName(r.destination)}
            </option>
          ))}
        </select>
      </label>

      {error && <p className="tv-empty">{error}</p>}
      {!summary && !error && <p className="tv-empty">Loading fares…</p>}

      {summary && (
        <>
          <section className="tv-headline">
            <span className="tv-route">
              {cityName(summary.origin)} → {cityName(summary.destination)}
            </span>
            <span className="tv-fare">{rupees(summary.typical_fare)}</span>
            <span className="tv-fare-note">typical one-way economy fare</span>
            {summary.trend_pct !== null && summary.trend_direction !== "flat" && (
              <span className={`tv-trend tv-trend-${summary.trend_direction}`}>
                {summary.trend_direction === "up" ? "▲" : "▼"}{" "}
                {Math.abs(summary.trend_pct).toFixed(1)}% vs the month before
              </span>
            )}
          </section>

          <section className="tv-advice">
            <span className="tv-advice-kicker">Best time to book</span>
            <strong>{windowLabel(summary.cheapest_window.window_days)}</strong>
            <p>
              Booking {summary.cheapest_window.window_days} days out costs about{" "}
              <b>{rupees(summary.cheapest_window.fare)}</b>. Leaving it to{" "}
              {windowLabel(summary.dearest_window.window_days)} costs{" "}
              <b>{rupees(summary.dearest_window.fare)}</b> — so booking early
              saves you around{" "}
              <b className="tv-save">
                {rupees(summary.max_saving)} ({summary.max_saving_pct.toFixed(0)}%)
              </b>
              .
            </p>
          </section>

          <section className="tv-block">
            <h2>Fare by how far ahead you book</h2>
            <ul className="tv-rows">
              {summary.windows.map((w) => {
                const isBest = w.window_days === summary.cheapest_window.window_days;
                const fill = dearest ? (w.fare / dearest) * 100 : 0;
                return (
                  <li key={w.window_days} className={isBest ? "tv-row tv-best" : "tv-row"}>
                    <span className="tv-row-fill" style={{ width: `${fill}%` }} />
                    <span className="tv-row-label">
                      {windowLabel(w.window_days)}
                      {isBest && <em className="tv-tag">cheapest</em>}
                    </span>
                    <span className="tv-row-value">{rupees(w.fare)}</span>
                  </li>
                );
              })}
            </ul>
          </section>

          <section className="tv-block">
            <h2>Airlines, booking {summary.cheapest_window.window_days} days ahead</h2>
            <ul className="tv-rows">
              {summary.carriers.map((c, i) => (
                <li key={c.code} className={i === 0 ? "tv-row tv-best" : "tv-row"}>
                  <span className="tv-row-label">
                    {c.name}
                    {i === 0 && <em className="tv-tag">cheapest</em>}
                  </span>
                  <span className="tv-row-value">{rupees(c.fare)}</span>
                </li>
              ))}
            </ul>
            <p className="tv-fine">
              All airlines compared at the same booking window, so the
              comparison is like-for-like.
            </p>
          </section>

          <p className="tv-note">
            Fares as of {prettyDate(summary.as_of)}, averaged over the previous
            week across the airlines and travel sites APIx tracks. These are
            typical prices for planning, not live quotes — and in this prototype
            they come from a calibrated synthetic feed, not live bookings.
          </p>

          <Link className="tv-analyst-link" to="/index-trend">
            Open the analyst dashboard →
          </Link>
        </>
      )}
    </div>
  );
}
