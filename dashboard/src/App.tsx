import { useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";

import Overview from "./pages/Overview";
import SectorHeatmap from "./pages/SectorHeatmap";
import LeadTimeElasticity from "./pages/LeadTimeElasticity";
import Validation from "./pages/Validation";

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="app">
      <button
        className="hamburger-btn"
        onClick={() => setSidebarOpen((open) => !open)}
        aria-label={sidebarOpen ? "Close menu" : "Open menu"}
        aria-expanded={sidebarOpen}
      >
        {sidebarOpen ? "✕" : "☰"}
      </button>
      <aside className={`sidebar${sidebarOpen ? "" : " sidebar-closed"}`}>
        <h1>APIx</h1>
        <p className="subtitle">Real-time Airfare Price Index</p>
        <nav>
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Overview
          </NavLink>
          <NavLink to="/heatmap" className={({ isActive }) => (isActive ? "active" : "")}>
            Sector Heatmap
          </NavLink>
          <NavLink to="/elasticity" className={({ isActive }) => (isActive ? "active" : "")}>
            Lead-Time Elasticity
          </NavLink>
          <NavLink to="/validation" className={({ isActive }) => (isActive ? "active" : "")}>
            Validation vs CPI
          </NavLink>
        </nav>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/heatmap" element={<SectorHeatmap />} />
          <Route path="/elasticity" element={<LeadTimeElasticity />} />
          <Route path="/validation" element={<Validation />} />
        </Routes>
      </main>
    </div>
  );
}
