# APIx -- Real-time Airfare Price Index for India

A prototype pipeline that scrapes/synthesizes airline & OTA fares across a
DGCA-weighted city-pair basket and five advance-purchase windows (T+1/7/15/30/45),
cleans and decomposes them, builds a real-time airfare price index, validates
it against the official MoSPI CPI airfare sub-index, and serves it via an API
+ React dashboard. See `docs/ARCHITECTURE.md` for the full design and
`docs/VALIDATION.md` for why this defaults to a calibrated synthetic dataset
rather than depending on live scraping succeeding.

## 1. Clone the repo

```bash
git clone <this-repo-url>
cd Apix-Airfare-Index
```

You'll need **Python 3.11+** and **Node.js (LTS)** installed. Check with
`python --version` / `python3 --version` and `node --version` -- install from
[python.org](https://python.org) and [nodejs.org](https://nodejs.org) if either
is missing, then **open a brand-new terminal** afterward (an already-open one
won't see a just-installed program).

## 2. One-time setup

The project keeps its own virtual environment (`.venv/`) rather than relying
on whatever `python` a terminal happens to resolve to system-wide -- this
matters if the machine has more than one Python version installed.

**Windows (PowerShell or the VS Code terminal):**
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd dashboard
npm install
cd ..
```

**macOS (Terminal):**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd dashboard
npm install
cd ..
```

Then, on either OS, generate the demo dataset -- synthetic fare history,
cleaned, indexed, and back-tested against `cpi_1054.xlsx`:
```bash
python -m scripts.seed_demo_data
```
This covers **1 Jan 2025 - 31 Jul 2026**, exactly the period the CPI file
spans, so every generated month has a real CPI month to be validated
against. Both ends are fixed rather than running to "today", so everyone who
seeds gets an identical database. It generates ~1.06M fare records and takes
roughly **4 minutes** -- it looks stalled partway through; let it finish.

## 3. Run it

**Option A -- one command:**
- Windows: double-click `start_dashboard.bat` (or run `.\start_dashboard.bat`)
- macOS: `bash start_dashboard.command` (double-clicking it in Finder also
  works once you've run it via Terminal the first time -- see the note in
  that file if Gatekeeper blocks it)

Both start the API and the dashboard together and open
`http://localhost:5173` in your browser automatically.

**Option B -- two terminals, manually:**
```bash
# Terminal 1 -- API
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS
uvicorn api.main:app --reload
# -> http://127.0.0.1:8000/docs

# Terminal 2 -- dashboard
cd dashboard
npm run dev
# -> http://localhost:5173
```

### Two audiences, two front ends

The dashboard serves a different landing page depending on screen width:

- **Laptop / desktop** opens the **analyst view** — the index trend, sector
  heatmap, lead-time curve and the CPI back-test, with the "explain this
  number" audit trail behind every index point.
- **Phone** opens the **traveller view** at `/fares` — no charts, just the
  numbers a passenger needs: the typical fare on a route, which advance-booking
  window is cheapest and what that saves, a like-for-like airline comparison at
  that window, and whether fares are rising or falling.

Both are reachable from either device: `/fares` is a stable address, and the
sidebar links across in both directions. The two views read the *same* cleaned
fare table — the traveller view is a different question asked of the same data
(`index/traveller.py`, served at `GET /api/v1/traveller/{route}`), not a
separate dataset.

### Opening it from your phone

Both servers bind to all network interfaces, so on the same Wi-Fi you can
open `http://<this-computer's-LAN-IP>:5173` from a phone. Find the IP with
`ipconfig` (Windows, look for the Wi-Fi adapter's IPv4 address) or
`ifconfig | grep inet` (macOS). If it doesn't connect, check that Windows
Firewall allows `python.exe`/`node.exe` through and that the network isn't
set to "Public" (Settings -> Network & Internet -> Wi-Fi -> network profile).

## Keeping multiple machines in sync

This repo is the source of truth -- changes don't sync automatically between
machines, you move them explicitly with git:

- **Push changes up** (from whichever machine made them):
  ```bash
  git add -A
  git commit -m "describe what changed"
  git push
  ```
- **Pull changes down** (on any other machine, before you start working):
  ```bash
  git pull
  ```

If you've been given **read-only (Collaborator: Read) access** to this
private repo, `git pull` always works, but `git push` will be rejected by
GitHub -- that's intentional, not a bug, so you can safely `git pull` any
time without risk of overwriting anyone's work.

Note that `apix.db` (the seeded demo database) is intentionally **not**
tracked by git -- it's ~250MB of generated data, regenerated locally by
`scripts.seed_demo_data`. **`git pull` therefore updates code but not
data.** If a pull changes the seed range or the index maths, delete
`apix.db` and re-seed on that machine, otherwise the dashboard keeps showing
figures built from the old data.

## Live scraping (optional, in addition to the synthetic default)

```bash
playwright install chromium
python -m scraper.run live --sources indigo,makemytrip     # hardened reference spiders
python -m scraper.run live                                  # all 11 sources (9 use placeholder selectors -- see docs/ETHICAL_SCRAPING.md)
```

Live and synthetic rows coexist in the same database, distinguished by
`data_source_type`. Re-run the daily job manually any time with
`python -m scraper.run synthetic --days 1` or start the long-lived scheduler
(`python -m scraper.scheduler`, see `.env.example` for mode/timing config).

## Tests

```bash
pytest
```

26 tests cover fare decomposition, outlier cleaning, index-construction math,
lead-time elasticity, the synthetic generator, offline (fixture-HTML) spider
parsing, and the API layer.

## Layout

```
scraper/    scraping engine (Scrapy+Playwright spiders, ethical-scraping
            middlewares, scheduler) + the calibrated synthetic generator
pipeline/   RawObservation -> CleanFare (decomposition, outlier removal, dedupe)
db/         SQLAlchemy schema (SQLite by default, DATABASE_URL for Postgres)
index/      APIx construction, basket weights, elasticity, heatmap,
            traveller-facing route summary
validation/ backtest against cpi_1054.xlsx (the real CPI airfare sub-index)
api/        FastAPI app
dashboard/  React + Vite + Recharts UI
scripts/    demo data seed + top-up
tests/      pytest suite
docs/       architecture, ethical-scraping policy, data dictionary, API, validation
```

See `docs/ARCHITECTURE.md`, `docs/ETHICAL_SCRAPING.md`,
`docs/DATA_DICTIONARY.md`, `docs/API.md`, `docs/VALIDATION.md`.
