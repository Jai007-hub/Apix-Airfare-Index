import { useState } from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";

import Home from "./pages/Home";
import Overview from "./pages/Overview";
import SectorHeatmap from "./pages/SectorHeatmap";
import LeadTimeElasticity from "./pages/LeadTimeElasticity";
import TravellerView from "./pages/TravellerView";
import Validation from "./pages/Validation";
import { useIsMobile } from "./useIsMobile";

const ANALYST_NAV = [
  { to: "/index-trend", label: "Index Trend", ico: "◔" },
  { to: "/heatmap", label: "Sector Heatmap", ico: "▦" },
  { to: "/elasticity", label: "Lead-Time Curve", ico: "◺" },
  { to: "/validation", label: "Validation vs CPI", ico: "≡" },
];

export default function App() {
  const isMobile = useIsMobile();
  // Starts collapsed on every screen size -- the hamburger opens it on demand
  // rather than greeting the page with the sidebar already expanded.
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const closeOnMobile = () => {
    if (isMobile) setSidebarOpen(false);
  };

  // A phone is a traveller's device, a laptop an analyst's, so "/" resolves to
  // a different page on each. Both views stay reachable from either: the
  // sidebar links across, and /fares is a stable address for the phone view.
  const topNav = isMobile
    ? [{ to: "/", label: "Check Fares", ico: "✈", end: true }]
    : [
        { to: "/", label: "Home", ico: "◈", end: true },
        { to: "/fares", label: "Traveller View", ico: "✈", end: false },
      ];

  const renderLink = (item: { to: string; label: string; ico: string; end?: boolean }) => (
    <NavLink
      key={item.to}
      to={item.to}
      end={item.end ?? false}
      className={({ isActive }) => (isActive ? "active" : "")}
      onClick={closeOnMobile}
    >
      <span className="ico" aria-hidden="true">
        {item.ico}
      </span>
      {item.label}
    </NavLink>
  );

  return (
    <>
      <header className="topbar">
        <button
          className="hamburger-btn"
          onClick={() => setSidebarOpen((open) => !open)}
          aria-label={sidebarOpen ? "Hide navigation" : "Show navigation"}
          aria-expanded={sidebarOpen}
        >
          {sidebarOpen ? "✕" : "☰"}
        </button>
        <Link to="/" className="brand">
          <span className="mark">
            AP<span>Ix</span>
          </span>
          <span className="tagline">Real-time Airfare Price Index for India</span>
        </Link>
        <span className="topbar-spacer" />
        <span className="badge">
          <span className="dot" />
          <span className="badge-label">Prototype</span>
        </span>
      </header>

      <div className="app">
        {isMobile && sidebarOpen && (
          <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} />
        )}

        <aside className={`sidebar${sidebarOpen ? "" : " sidebar-closed"}`}>
          <div className="nav-label">{isMobile ? "Fares" : "Dashboard"}</div>
          <nav>{topNav.map(renderLink)}</nav>

          {isMobile && <div className="nav-label nav-label-sub">Analyst view</div>}
          <nav>{ANALYST_NAV.map(renderLink)}</nav>

          <div className="sidebar-foot">
            Built for SIH26056 — MoSPI / NSO.
            <br />
            Index base period = 100.
          </div>
        </aside>

        <main className="main">
          <Routes>
            <Route path="/" element={isMobile ? <TravellerView /> : <Home />} />
            <Route path="/fares" element={<TravellerView />} />
            <Route path="/index-trend" element={<Overview />} />
            <Route path="/heatmap" element={<SectorHeatmap />} />
            <Route path="/elasticity" element={<LeadTimeElasticity />} />
            <Route path="/validation" element={<Validation />} />
          </Routes>
        </main>
      </div>
    </>
  );
}
