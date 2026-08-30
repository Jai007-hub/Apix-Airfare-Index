import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, IndexPoint, RouteInfo, ValidationSummary } from "../api/client";

const SECTIONS = [
  {
    to: "/index-trend",
    ico: "◔",
    title: "Index Trend",
    body: "The headline APIx series at daily, weekly and monthly frequency.",
  },
  {
    to: "/heatmap",
    ico: "▦",
    title: "Sector Heatmap",
    body: "Average fare by route and period — which sectors are running hot.",
  },
  {
    to: "/elasticity",
    ico: "◺",
    title: "Lead-Time Curve",
    body: "How fares climb as departure nears, across five booking windows.",
  },
  {
    to: "/validation",
    ico: "≡",
    title: "Validation vs CPI",
    body: "Back-test against MoSPI's official All-India airfare sub-index.",
  },
];

export default function Home() {
  const [daily, setDaily] = useState<IndexPoint[] | null>(null);
  const [routes, setRoutes] = useState<RouteInfo[] | null>(null);
  const [validation, setValidation] = useState<ValidationSummary | null>(null);

  useEffect(() => {
    // Each panel degrades independently -- a missing series shouldn't blank the page.
    api.getIndex("daily").then(setDaily).catch(() => setDaily([]));
    api.getRoutes().then(setRoutes).catch(() => setRoutes([]));
    api.getValidation().then(setValidation).catch(() => setValidation(null));
  }, []);

  const latest = daily?.length ? daily[daily.length - 1] : null;
  const first = daily?.length ? daily[0] : null;
  const pctChange =
    latest && first && first.apix_value
      ? ((latest.apix_value - first.apix_value) / first.apix_value) * 100
      : null;

  return (
    <div>
      <section className="hero">
        <h1>
          A daily price index for <em>what Indians actually pay</em> to fly.
        </h1>
        <p className="lede">
          CPI prices air travel from a limited set of outlets, monthly — while over 90% of domestic
          tickets are bought online at fares that swing 200–400% within a single day. APIx automates
          that collection across a DGCA-weighted basket of city-pairs and five advance-purchase
          windows, then publishes a transparent index that NSO and RBI can consume through an API.
        </p>

        <div className="hero-figure">
          <span className="num">{latest ? latest.apix_value.toFixed(1) : "—"}</span>
          <span className="meta">
            Latest daily APIx
            {latest && (
              <>
                {" · "}
                {latest.period_date}
              </>
            )}
            <br />
            {pctChange !== null && (
              <span className={pctChange >= 0 ? "up" : "down"}>
                {pctChange >= 0 ? "▲" : "▼"} {Math.abs(pctChange).toFixed(1)}% over the observed
                window
              </span>
            )}
          </span>
        </div>
      </section>

      <div className="stat-row">
        <div className="stat">
          <div className="label">Routes in basket</div>
          <div className="value">{routes ? routes.length : "—"}</div>
          <div className="hint">Weighted by DGCA traffic share</div>
        </div>
        <div className="stat">
          <div className="label">Daily observations</div>
          <div className="value">{daily ? daily.length : "—"}</div>
          <div className="hint">Consecutive days of index history</div>
        </div>
        <div className="stat">
          <div className="label">Booking windows</div>
          <div className="value">5</div>
          <div className="hint">T+1, T+7, T+15, T+30, T+45</div>
        </div>
        <div className="stat">
          <div className="label">Months back-tested</div>
          <div className="value">{validation ? validation.n_months_compared : "—"}</div>
          <div className="hint">Against official CPI airfare index</div>
        </div>
      </div>

      <div className="nav-cards">
        {SECTIONS.map((s) => (
          <Link key={s.to} to={s.to} className="nav-card">
            <span className="ico" aria-hidden="true">
              {s.ico}
            </span>
            <h4>{s.title}</h4>
            <p>{s.body}</p>
          </Link>
        ))}
      </div>

      <div className="card">
        <h3>
          How the pipeline runs<span className="sub">scheduled daily</span>
        </h3>
        <div className="pipeline">
          <span className="step">Scrape airline &amp; OTA portals</span>
          <span className="arrow">→</span>
          <span className="step">Clean &amp; de-duplicate</span>
          <span className="arrow">→</span>
          <span className="step">Split base fare / taxes / UDF</span>
          <span className="arrow">→</span>
          <span className="step">Weight by route</span>
          <span className="arrow">→</span>
          <span className="step">Publish index + API</span>
        </div>
      </div>

      <div className="note">
        <span aria-hidden="true">ⓘ</span>
        <span>
          <strong>On the data shown here.</strong> The scraping engine is real — Scrapy + Playwright,
          robots.txt-compliant, rate-limited, with CAPTCHA detection that backs off rather than
          evading. Every major airline and OTA portal tested currently blocks automated access at the
          page or search-API layer, so this demo runs on a calibrated synthetic dataset. Every record
          carries a <code>live</code> / <code>synthetic</code> tag, and real fares flow through the
          identical pipeline the moment a source becomes available.
        </span>
      </div>
    </div>
  );
}
