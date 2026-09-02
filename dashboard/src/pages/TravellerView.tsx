import { useEffect, useMemo, useState } from "react";

import { api, LeaderboardRow, RouteInfo, TravellerSummary } from "../api/client";

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
const windowLabel = (days: number) => (days === 1 ? "1 day ahead" : `${days} days ahead`);

const prettyDate = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

export default function TravellerView() {
  const [routes, setRoutes] = useState<RouteInfo[]>([]);
  const [board, setBoard] = useState<LeaderboardRow[]>([]);
  const [selected, setSelected] = useState("DEL-BOM");
  const [summary, setSummary] = useState<TravellerSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Which booking window the airline table compares at. Defaults to the
  // cheapest one, then follows whatever the reader picks.
  const [carrierWindow, setCarrierWindow] = useState<number | null>(null);
  // Which airline the whole page describes. "" is the all-airline mean.
  const [airline, setAirline] = useState("");

  useEffect(() => {
    api.getRoutes().then(setRoutes).catch(() => setRoutes([]));
    api.getRouteLeaderboard().then(setBoard).catch(() => setBoard([]));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setSummary(null);
    setError(null);
    api
      .getTraveller(selected, airline || undefined)
      .then((s) => !cancelled && setSummary(s))
      .catch(() => !cancelled && setError("Could not load fares for this route."));
    return () => {
      cancelled = true;
    };
  }, [selected, airline]);

  useEffect(() => {
    if (summary) setCarrierWindow(summary.cheapest_window.window_days);
  }, [summary]);

  const [origin, destination] = selected.split("-");

  const origins = useMemo(
    () => Array.from(new Set(routes.map((r) => r.origin))).sort(),
    [routes],
  );

  /* Only the sectors APIx actually tracks are offered. Letting someone pick
     Kolkata -> Chennai and then apologising would be worse than not offering
     it, so the destination list narrows to what the chosen origin flies to. */
  const destinations = useMemo(
    () => routes.filter((r) => r.origin === origin).map((r) => r.destination).sort(),
    [routes, origin],
  );

  const pickOrigin = (next: string) => {
    const first = routes.find((r) => r.origin === next);
    if (first) setSelected(`${next}-${first.destination}`);
  };

  const activeWindow = carrierWindow ?? summary?.cheapest_window.window_days ?? 0;
  const activeCarriers = summary?.carriers_by_window[String(activeWindow)] ?? [];

  const cheapMonth = summary?.months.length
    ? summary.months.reduce((a, b) => (b.fare < a.fare ? b : a))
    : null;
  const dearMonth = summary?.months.length
    ? summary.months.reduce((a, b) => (b.fare > a.fare ? b : a))
    : null;

  const activeSplit =
    summary?.breakdown_by_window[String(activeWindow)] ?? summary?.fare_breakdown;
  const activeFare =
    summary?.windows.find((w) => w.window_days === activeWindow)?.fare ?? 0;

  const breakdownRows = activeSplit
    ? ([
        ["Base fare", activeSplit.base_fare],
        ["Taxes & surcharges", activeSplit.taxes],
        ["User development fee", activeSplit.udf],
        ["Convenience fee", activeSplit.convenience_fee],
      ] as const)
    : [];

  const lateWindow = summary?.windows.find((w) => w.window_days === 1);

  return (
    <div className="tv">
      <div className="tv-top">
        <header className="tv-head">
          <h1>Know the fare before you book.</h1>
          <p>Typical prices on India's busiest routes, and when they're cheapest.</p>
        </header>

        {/* Search card -- the familiar from/to shape, but every option in it is
            a sector we hold real data for. */}
        <div className="tv-search">
          <label className="tv-field">
            <span>From</span>
            <select value={origin} onChange={(e) => pickOrigin(e.target.value)}>
              {origins.map((c) => (
                <option key={c} value={c}>
                  {cityName(c)}
                </option>
              ))}
            </select>
          </label>

          <span className="tv-plane" aria-hidden="true">
            ✈
          </span>

          <label className="tv-field">
            <span>To</span>
            <select
              value={destination}
              onChange={(e) => setSelected(`${origin}-${e.target.value}`)}
            >
              {destinations.map((c) => (
                <option key={c} value={c}>
                  {cityName(c)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="tv-airline-bar">
        <label>
          <span>Airline</span>
          <select
            className="tv-pill-select"
            value={airline}
            onChange={(e) => setAirline(e.target.value)}
          >
            <option value="">All airlines (average)</option>
            {(summary?.carriers ?? []).map((c) => (
              <option key={c.code} value={c.code}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <span className="tv-airline-note">
          {summary?.carrier_name
            ? `Every fare below is ${summary.carrier_name}'s.`
            : "Fares below average all airlines — no single airline charges exactly this."}
        </span>
      </div>

      {error && <p className="tv-empty">{error}</p>}
      {!summary && !error && <p className="tv-empty">Loading fares…</p>}

      {summary && (
        <div className="tv-grid">
          <section className="tv-headline tv-a-headline">
            <div className="tv-headline-top">
              <span className="tv-route">
                {cityName(summary.origin)} → {cityName(summary.destination)}
              </span>
              {summary.trend_pct !== null && summary.trend_direction !== "flat" && (
                <span className={`tv-chip tv-chip-${summary.trend_direction}`}>
                  {summary.trend_direction === "up" ? "▲" : "▼"}{" "}
                  {Math.abs(summary.trend_pct).toFixed(1)}%
                </span>
              )}
            </div>
            <span className="tv-fare">{rupees(summary.typical_fare)}</span>
            {/* The range is the booking-window spread, not the spread within
                one window -- it has to bracket the number above it, and "what
                it costs depending on when you book" is the useful reading. */}
            <span className="tv-fare-note">
              typical one-way economy fare · {rupees(summary.cheapest_window.fare)}–
              {rupees(summary.dearest_window.fare)} depending on when you book
            </span>
          </section>

          <section className="tv-advice tv-a-advice">
            <div className="tv-advice-row">
              <div>
                <span className="tv-advice-kicker">Best time to book</span>
                <strong>{windowLabel(summary.cheapest_window.window_days)}</strong>
              </div>
              <span className="tv-save-badge">
                save {rupees(summary.max_saving)}
              </span>
            </div>
            <p>
              At {summary.cheapest_window.window_days} days out you'd pay about{" "}
              <b>{rupees(summary.cheapest_window.fare)}</b>. Leave it to{" "}
              {windowLabel(summary.dearest_window.window_days)} and it's{" "}
              <b>{rupees(summary.dearest_window.fare)}</b> — around{" "}
              {summary.max_saving_pct.toFixed(0)}% more.
            </p>
          </section>

          <section className="tv-block tv-a-windows">
            <h2>Fare by how far ahead you book</h2>
            <ul className="tv-rows">
              {summary.windows.map((w) => {
                const isBest = w.window_days === summary.cheapest_window.window_days;
                const fill = summary.dearest_window.fare
                  ? (w.fare / summary.dearest_window.fare) * 100
                  : 0;
                const isActive = w.window_days === activeWindow;
                return (
                  <li key={w.window_days}>
                    <button
                      type="button"
                      className={
                        isActive ? "tv-row tv-row-btn tv-best" : "tv-row tv-row-btn"
                      }
                      onClick={() => setCarrierWindow(w.window_days)}
                      aria-pressed={isActive}
                    >
                    <span className="tv-row-fill" style={{ width: `${fill}%` }} />
                    <span className="tv-row-label">
                      {windowLabel(w.window_days)}
                      {isBest && <em className="tv-tag">cheapest window</em>}
                      {w.sold_out_pct >= 1 && (
                        <em className="tv-tag tv-tag-warn">
                          {w.sold_out_pct.toFixed(0)}% sold out
                        </em>
                      )}
                    </span>
                    <span className="tv-row-value">{rupees(w.fare)}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
            <p className="tv-fine">
              {summary.carrier_name
                ? `${summary.carrier_name} fares at each booking window.`
                : "Each row averages every airline at that booking window."}{" "}
              Tap a row to switch the other two panels to that window.
              {lateWindow && lateWindow.sold_out_pct >= 1 && (
                <>
                  {" "}
                  Booking late doesn't just cost more —{" "}
                  {lateWindow.sold_out_pct.toFixed(0)}% of day-before searches on this
                  route came back with no seats at all.
                </>
              )}
            </p>
          </section>

          <section className="tv-block tv-a-breakdown">
            <h2>What you're actually paying for · T+{activeWindow}</h2>
            <ul className="tv-rows tv-rows-plain">
              {breakdownRows.map(([label, value]) => (
                <li key={label} className="tv-row">
                  <span className="tv-row-label">{label}</span>
                  <span className="tv-row-value">{rupees(value)}</span>
                </li>
              ))}
              <li className="tv-row tv-row-total">
                <span className="tv-row-label">Total</span>
                <span className="tv-row-value">{rupees(activeFare)}</span>
              </li>
            </ul>
            <p className="tv-fine">
              Splits the {rupees(activeFare)}{" "}
              {summary.carrier_name ? `${summary.carrier_name} fare` : "average"} at{" "}
              {windowLabel(activeWindow)} — the highlighted row above. Taxes, the airport user development fee and the booking site's
              convenience fee are what separate the headline price from the one you
              pay.
            </p>
          </section>

          <section className="tv-block tv-a-airlines">
            <div className="tv-block-head">
              <h2>Airlines by booking window</h2>
              <select
                className="tv-pill-select"
                value={activeWindow}
                onChange={(e) => setCarrierWindow(Number(e.target.value))}
                aria-label="Booking window to compare airlines at"
              >
                {summary.windows.map((w) => (
                  <option key={w.window_days} value={w.window_days}>
                    T+{w.window_days}
                  </option>
                ))}
              </select>
            </div>
            <ul className="tv-rows tv-rows-plain">
              {activeCarriers.map((c, i) => (
                <li
                  key={c.code}
                  className={
                    c.code === summary.carrier_code || (!summary.carrier_code && i === 0)
                      ? "tv-row tv-best"
                      : "tv-row"
                  }
                >
                  <span className="tv-row-label">
                    {c.name}
                    {i === 0 && <em className="tv-tag">lowest</em>}
                    {c.code === summary.carrier_code && (
                      <em className="tv-tag">showing</em>
                    )}
                  </span>
                  <span className="tv-row-value">{rupees(c.fare)}</span>
                </li>
              ))}
            </ul>
            <p className="tv-fine">
              Fares if you book {windowLabel(activeWindow)} — every airline at the
              same window, so it's like-for-like. Who is cheapest changes with the
              window, which is why it is picked rather than fixed.
              {activeWindow === summary.cheapest_window.window_days && (
                <>
                  {" "}
                  {summary.carrier_code
                    ? `${summary.carrier_name} shows ${rupees(summary.cheapest_window.fare)} here — the same figure the other two panels use.`
                    : `These five average ${rupees(summary.cheapest_window.fare)}, which is the figure the other two panels use.`}
                </>
              )}
            </p>
          </section>

          {cheapMonth && dearMonth && cheapMonth.name !== dearMonth.name && (
            <section className="tv-block tv-a-season">
              <h2>Cheapest time of year to fly this route</h2>
              <div className="tv-stats">
                <div className="tv-stat tv-stat-good">
                  <span>Cheapest</span>
                  <strong>{cheapMonth.name}</strong>
                  <em>{rupees(cheapMonth.fare)}</em>
                </div>
                <div className="tv-stat tv-stat-bad">
                  <span>Dearest</span>
                  <strong>{dearMonth.name}</strong>
                  <em>{rupees(dearMonth.fare)}</em>
                </div>
              </div>
              <ul className="tv-months">
                {summary.months.map((m) => (
                  <li
                    key={m.month}
                    className={
                      m.month === cheapMonth.month
                        ? "tv-month tv-month-good"
                        : m.month === dearMonth.month
                          ? "tv-month tv-month-bad"
                          : "tv-month"
                    }
                  >
                    <span>{m.name}</span>
                    <strong>{rupees(m.fare)}</strong>
                  </li>
                ))}
              </ul>
              <p className="tv-fine">
                Average fare per calendar month across every year on record —
                seasonality, not a forecast.{" "}
                <span className="tv-only-narrow">Swipe for all twelve.</span>
              </p>
            </section>
          )}

          {board.length > 0 && (
            <section className="tv-block tv-a-board">
              <h2>All {board.length} routes, cheapest first</h2>
              <ul className="tv-rows tv-rows-plain">
                {board.map((r) => (
                  <li key={r.route}>
                    <button
                      type="button"
                      className={
                        r.route === selected ? "tv-row tv-row-btn tv-best" : "tv-row tv-row-btn"
                      }
                      onClick={() => setSelected(r.route)}
                    >
                      <span className="tv-row-label">
                        {cityName(r.origin)} → {cityName(r.destination)}
                      </span>
                      <span className="tv-row-value">from {rupees(r.best_fare)}</span>
                    </button>
                  </li>
                ))}
              </ul>
              <p className="tv-fine">
                Every route APIx tracks, at its own cheapest booking window. Tap any
                one to switch to it — quicker than working back through the from/to
                pickers, which only list cities that a tracked route departs from.
              </p>
            </section>
          )}

          <p className="tv-note tv-a-note">
            Fares as of {prettyDate(summary.as_of)}, averaged over the previous
            week across the airlines and travel sites APIx tracks. These are
            typical prices for planning, not live quotes — and in this prototype
            they come from a calibrated synthetic feed, not live bookings.
          </p>
        </div>
      )}
    </div>
  );
}
