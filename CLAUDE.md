# Theme Intelligence App

An investing dashboard that visualizes Relative Rotation Graphs (RRG) for sectors, countries, and custom investment themes, with signal detection and research notes.

## User

- Not a software engineer — explain things in plain language
- Anonymous identity: GitHub user `valuedriftcode`, email `valuedriftcode@users.noreply.github.com`
- Suggest pushing to GitHub at the end of sessions when code changes exist
- Use `python3` (not `python`) on this Mac
- GitHub CLI path: `/Users/ericmeng/.local/bin/gh`

## Tech Stack

- **Frontend**: React 18 (port 3000), Recharts for charts, Axios for API calls
- **Backend**: Flask (port 5001), yfinance for market data, SQLite database
- **Database**: `backend/theme_intel.db` (gitignored — user data, not in repo)
- **Start/Stop**: Double-click `.command` files in project root from Finder

## Project Structure

```
frontend/src/
  App.js                  — Main layout, fullscreen panel orchestration
  App.css                 — Global styles, dark theme (#0a0a0a / #1a1a1a)
  api/client.js           — All API functions (Axios, base URL localhost:5001)
  components/
    RRGChart.js           — RRG visualization (sectors, countries, themes), quadrant zoom, trails
    Heatmap.js            — Finviz-style treemap heatmap (all themes or single theme, 1D/1W/1M/3M/1Y)
    SignalsPanel.js        — Signal table (price moves, RSI, 52-week, RRG transitions)
    ThemeManager.js        — Theme CRUD, ticker management, compact/expanded views
    ThemeForm.js           — Create/edit theme form
    TickerSuggestionPanel.js — AI-suggested tickers for themes
    StockDetailPanel.js    — Individual stock research profiles
    TopBar.js              — Market overview ticker (SPY, QQQ, DIA, IWM)

backend/
  app.py                  — Flask API, 23+ endpoints, SECTOR_ETFS/COUNTRY_ETFS lists
  rrg_engine.py           — RRG calculation (RS-Ratio, RS-Momentum via JdK method)
  signal_detector.py      — Signal detection pipeline
  data_store.py           — SQLite operations (themes, research, signals)
  stock_universe.py       — 8K+ stock universe for ticker suggestions
  theme_intelligence_service.py — Pluggable AI backend (ABC with suggest_tickers, discover_themes)
  info_cache.py           — Caching layer for stock info
```

## Key Concepts

- **RRG**: Relative Rotation Graphs plot RS-Ratio (X) vs RS-Momentum (Y), centered at 100. Quadrants rotate clockwise: Leading → Weakening → Lagging → Improving
- **Sectors view**: 11 GICS sector ETFs vs SPY benchmark
- **Countries view**: 37 single-country ETFs vs ACWI (global) benchmark
- **Theme view**: User-created baskets of tickers, shown on RRG
- **Signals**: Automated detection of price moves, RSI extremes, 52-week highs/lows, RRG quadrant transitions

## Current Features

- RRG with sectors, countries (37), and custom themes
- Fullscreen expand (⛶) on all panels, Escape to exit
- Quadrant zoom buttons (Leading/Weakening/Lagging/Improving)
- Symmetric axes, faded default trails with bright hover highlight
- Always-visible ticker labels
- Theme CRUD with ticker suggestion engine
- Signal detection table
- Stock research profiles with notes/catalysts/risks
- Market overview ticker bar

## Vision / Roadmap

The app is currently a manual dashboard. The goal is automated monitoring that surfaces what matters so the user can focus on decisions. Proposed next features (not yet prioritized):

1. **Daily Digest** — "What happened overnight" summary
2. **News/Event Feed** — Per-theme news monitoring
3. **AI Theme Discovery** — Framework exists (ThemeIntelligenceService ABC)
4. **Smarter Alerts** — Theme-level quadrant transitions, not just individual tickers
5. **Automated Research Notes** — AI-generated analysis entries

## API Endpoints (key ones)

- `GET /api/sectors/rrg` — Sector RRG data
- `GET /api/countries/rrg` — Country RRG data
- `GET /api/themes` — List themes
- `POST /api/themes` — Create theme
- `GET /api/themes/:id/rrg` — Theme RRG data
- `GET /api/signals` — Current signals
- `GET /api/heatmap?period=1d&theme_id=5` — Heatmap performance data (1d/1w/1mo/3mo/1y)
- `GET /api/stock/:ticker` — Stock research profile
