import { useState } from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";

import Home from "./pages/Home";
import Overview from "./pages/Overview";
import SectorHeatmap from "./pages/SectorHeatmap";
import LeadTimeElasticity from "./pages/LeadTimeElasticity";
import TravellerView from "./pages/TravellerView";
import Validation from "./pages/Validation";
import { useIsMobile } from "./useIsMobile";

const NAV = [
  { to: "/", label: "Home", ico: "◈", end: true },
  { to: "/fares", label: "Traveller View", ico: "✈", end: false },
  { to: "/index-trend", label: "Index Trend", ico: "◔", end: false },
  { to: "/heatmap", label: "Sector Heatmap", ico: "▦", end: false },
  { to: "/elasticity", label: "Lead-Time Curve", ico: "◺", end: false },
  { to: "/validation", label: "Validation vs CPI", ico: "≡", end: false },
];

export default function App() {
  const isMobile = useIsMobile();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // A phone is a traveller's device, a laptop an analyst's. Rather than
  // shrinking the dashboard onto a phone, the phone gets its own product --
  // the fare view and nothing else, so there is no navigation to get lost in.
  // The analyst pages stay on the laptop, where the charts are readable.
  if (isMobile) {
    return (
      <>
        <header className="topbar topbar-mobile">
          <Link to="/" className="brand">
            <span className="mark">
              AP<span>Ix</span>
            </span>
          </Link>
          <span className="topbar-spacer" />
          <span className="badge">
            <span className="dot" />
            <span className="badge-label">Prototype</span>
          </span>
        </header>
        <div className="app">
          <main className="main">
            <TravellerView />
          </main>
        </div>
      </>
    );
  }

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
        <aside className={`sidebar${sidebarOpen ? "" : " sidebar-closed"}`}>
          <div className="nav-label">Dashboard</div>
          <nav>
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => (isActive ? "active" : "")}
              >
                <span className="ico" aria-hidden="true">
                  {item.ico}
                </span>
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="sidebar-foot">
            Built for SIH26056 — MoSPI / NSO.
            <br />
            Index base period = 100.
          </div>
        </aside>

        <main className="main">
          <Routes>
            <Route path="/" element={<Home />} />
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
