"""
Theme Intelligence Investing Dashboard - Flask Backend API

A Flask-based REST API providing:
- RRG (Relative Rotation Graphs) analysis for sectors and themes
- Theme management (CRUD operations)
- Real-time signal detection (large moves, RSI extremes, 52-week levels)
- Market overview data

Runs on http://localhost:5001 with CORS enabled for localhost:3000
"""

import logging
from typing import Dict, List, Tuple

import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

from data_store import DataStore
from rrg_engine import get_rrg_data, get_rrg_data_batch, get_sector_rrg_data
from signal_detector import detect_signals_batch
from stock_universe import StockUniverse
from info_cache import InfoCache
from theme_intelligence_service import HeuristicThemeIntelligence
import yfinance as yf
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(
    app,
    resources={r"/api/*": {"origins": ["http://localhost:3000", "http://127.0.0.1:3000"]}}
)

# Initialize data store
data_store = DataStore()

# Initialize stock universe and intelligence service
stock_universe = StockUniverse()
info_cache = InfoCache()
intelligence_service = HeuristicThemeIntelligence(stock_universe, info_cache)

def _classify_quadrant(rs_ratio, rs_momentum):
    """Classify an RRG position into a quadrant."""
    if rs_ratio >= 100:
        return "leading" if rs_momentum >= 100 else "weakening"
    else:
        return "improving" if rs_momentum >= 100 else "lagging"


def _detect_rrg_transitions(tickers):
    """Check for RRG quadrant transitions using recent history."""
    signals = []
    for ticker in tickers:
        try:
            rrg = get_rrg_data(ticker, benchmark="SPY", period="1y", tail=3)
            if not rrg or len(rrg.get("history", [])) < 2:
                continue

            history = rrg["history"]
            prev = history[-2]
            curr = history[-1]
            prev_q = _classify_quadrant(prev["rs_ratio"], prev["rs_momentum"])
            curr_q = _classify_quadrant(curr["rs_ratio"], curr["rs_momentum"])

            if prev_q != curr_q:
                signals.append({
                    "type": "rrg_transition",
                    "ticker": ticker.upper(),
                    "details": f"RRG moved from {prev_q.title()} to {curr_q.title()}",
                    "from_quadrant": prev_q,
                    "to_quadrant": curr_q,
                    "rs_ratio": round(curr["rs_ratio"], 2),
                    "rs_momentum": round(curr["rs_momentum"], 2),
                    "date": curr.get("date", ""),
                    "significance": 7.0,
                })
        except Exception as e:
            logger.debug(f"RRG transition check failed for {ticker}: {e}")
    return signals


# S&P 500 sector ETFs (all 11 sectors)
SECTOR_ETFS = [
    "XLK",   # Technology
    "XLF",   # Financials
    "XLE",   # Energy
    "XLV",   # Healthcare
    "XLI",   # Industrials
    "XLP",   # Consumer Staples
    "XLU",   # Utilities
    "XLB",   # Materials
    "XLC",   # Communications
    "XLRE",  # Real Estate
    "XLY"    # Consumer Discretionary
]

# All investable single-country ETFs vs ACWI
COUNTRY_ETFS = [
    # Americas
    "SPY",   # United States
    "EWC",   # Canada
    "EWZ",   # Brazil
    "EWW",   # Mexico
    "ARGT",  # Argentina
    "ECH",   # Chile
    "EPU",   # Peru
    # Europe
    "EWU",   # United Kingdom
    "EWG",   # Germany
    "EWQ",   # France
    "EWI",   # Italy
    "EWP",   # Spain
    "EWN",   # Netherlands
    "EWL",   # Switzerland
    "EWD",   # Sweden
    "EWO",   # Austria
    "EWK",   # Belgium
    "EDEN",  # Denmark
    "EIRL",  # Ireland
    "EPOL",  # Poland
    # Asia-Pacific
    "EWJ",   # Japan
    "EWY",   # South Korea
    "EWT",   # Taiwan
    "FXI",   # China
    "INDA",  # India
    "EWH",   # Hong Kong
    "EWS",   # Singapore
    "EWM",   # Malaysia
    "THD",   # Thailand
    "VNM",   # Vietnam
    "ENZL",  # New Zealand
    "EWA",   # Australia
    # Middle East & Africa
    "EIS",   # Israel
    "KSA",   # Saudi Arabia
    "QAT",   # Qatar
    "UAE",   # UAE
    "EZA",   # South Africa
]


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(400)
def bad_request(error):
    """Handle 400 Bad Request errors."""
    return jsonify({"error": "Bad request", "message": str(error)}), 400


@app.errorhandler(404)
def not_found(error):
    """Handle 404 Not Found errors."""
    return jsonify({"error": "Not found", "message": "Resource not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error", "message": str(error)}), 500


# ============================================================================
# Sector RRG Endpoints
# ============================================================================

@app.route("/api/sectors/rrg", methods=["GET"])
def get_sectors_rrg():
    """
    Get RRG data for all S&P 500 sector ETFs vs SPY benchmark.

    Returns:
        JSON with RRG data for each sector ETF including:
        - current RS-Ratio and RS-Momentum
        - historical tail for animation
        - total data points

    Example response:
        {
            "XLK": {
                "ticker": "XLK",
                "benchmark": "SPY",
                "current": {"rs_ratio": 145.2, "rs_momentum": 102.5},
                "history": [...],
                "data_points": 52
            },
            ...
        }
    """
    try:
        logger.info("Fetching RRG data for sectors")
        rrg_data = get_sector_rrg_data(
            sector_etfs=SECTOR_ETFS,
            benchmark="SPY",
            period="1y",
            tail=5
        )

        if not rrg_data:
            return jsonify({
                "status": "error",
                "error": "Unable to fetch live sector RRG data from Yahoo Finance",
                "data": {},
                "count": 0
            }), 503

        return jsonify({
            "status": "success",
            "data": rrg_data,
            "count": len(rrg_data)
        }), 200

    except Exception as e:
        logger.error(f"Error in get_sectors_rrg: {e}")
        return jsonify({"status": "error", "error": f"Failed to fetch sector RRG data: {str(e)}"}), 500


# ============================================================================
# Country RRG Endpoints
# ============================================================================

@app.route("/api/countries/rrg", methods=["GET"])
def get_countries_rrg():
    """Get RRG data for major country ETFs vs ACWI (global) benchmark."""
    try:
        logger.info("Fetching RRG data for countries")
        rrg_data = get_sector_rrg_data(
            sector_etfs=COUNTRY_ETFS,
            benchmark="ACWI",
            period="1y",
            tail=5
        )

        if not rrg_data:
            return jsonify({
                "status": "error",
                "error": "Unable to fetch live country RRG data from Yahoo Finance",
                "data": {},
                "count": 0
            }), 503

        return jsonify({
            "status": "success",
            "data": rrg_data,
            "count": len(rrg_data)
        }), 200

    except Exception as e:
        logger.error(f"Error in get_countries_rrg: {e}")
        return jsonify({"status": "error", "error": f"Failed to fetch country RRG data: {str(e)}"}), 500


# ============================================================================
# Theme Endpoints
# ============================================================================

@app.route("/api/themes", methods=["GET"])
def get_themes():
    """
    Get all investment themes.

    Returns:
        JSON list of themes with their tickers and metadata

    Example response:
        {
            "status": "success",
            "data": [
                {
                    "id": 1,
                    "name": "AI Infrastructure",
                    "thesis": "...",
                    "tickers": ["NVDA", "AMD", ...],
                    "tags": ["semiconductors", "AI"],
                    "created_at": "2024-01-15T10:30:00",
                    "updated_at": "2024-01-15T10:30:00"
                },
                ...
            ],
            "count": 4
        }
    """
    try:
        themes = data_store.get_all_themes()
        return jsonify({
            "status": "success",
            "data": themes,
            "count": len(themes)
        }), 200

    except Exception as e:
        logger.error(f"Error in get_themes: {e}")
        return jsonify({"error": "Failed to fetch themes", "message": str(e)}), 500


@app.route("/api/themes", methods=["POST"])
def create_theme():
    """
    Create a new investment theme.

    Request body:
        {
            "name": "Theme Name",
            "thesis": "Investment thesis description",
            "tickers": ["TICKER1", "TICKER2", ...],
            "tags": ["tag1", "tag2", ...]
        }

    Returns:
        JSON with created theme including id
    """
    try:
        data = request.get_json()

        # Validate required fields
        if not all(key in data for key in ["name", "thesis", "tickers", "tags"]):
            return jsonify({"error": "Missing required fields"}), 400

        if not isinstance(data["tickers"], list) or not isinstance(data["tags"], list):
            return jsonify({"error": "tickers and tags must be lists"}), 400

        if len(data["tickers"]) == 0:
            return jsonify({"error": "At least one ticker is required"}), 400

        # Create theme
        theme = data_store.create_theme(
            name=data["name"],
            thesis=data["thesis"],
            tickers=data["tickers"],
            tags=data["tags"]
        )

        logger.info(f"Created theme: {theme['name']}")
        return jsonify({
            "status": "success",
            "data": theme
        }), 201

    except Exception as e:
        logger.error(f"Error in create_theme: {e}")
        return jsonify({"error": "Failed to create theme", "message": str(e)}), 500


@app.route("/api/themes/<int:theme_id>", methods=["GET"])
def get_theme(theme_id: int):
    """
    Get a specific theme by ID.

    Args:
        theme_id: Theme ID (path parameter)

    Returns:
        JSON with theme data or 404 if not found
    """
    try:
        theme = data_store.get_theme(theme_id)

        if not theme:
            return jsonify({"error": "Theme not found"}), 404

        return jsonify({
            "status": "success",
            "data": theme
        }), 200

    except Exception as e:
        logger.error(f"Error in get_theme: {e}")
        return jsonify({"error": "Failed to fetch theme", "message": str(e)}), 500


@app.route("/api/themes/<int:theme_id>", methods=["PUT"])
def update_theme(theme_id: int):
    """
    Update a theme.

    Args:
        theme_id: Theme ID (path parameter)

    Request body (all fields optional):
        {
            "name": "New name",
            "thesis": "New thesis",
            "tickers": ["NEW", "TICKERS"],
            "tags": ["new", "tags"]
        }

    Returns:
        JSON with updated theme or 404 if not found
    """
    try:
        data = request.get_json() or {}

        # Validate input
        if "tickers" in data and (not isinstance(data["tickers"], list) or len(data["tickers"]) == 0):
            return jsonify({"error": "tickers must be a non-empty list"}), 400

        if "tags" in data and not isinstance(data["tags"], list):
            return jsonify({"error": "tags must be a list"}), 400

        # Update theme
        updated_theme = data_store.update_theme(
            theme_id=theme_id,
            name=data.get("name"),
            thesis=data.get("thesis"),
            tickers=data.get("tickers"),
            tags=data.get("tags")
        )

        if not updated_theme:
            return jsonify({"error": "Theme not found"}), 404

        logger.info(f"Updated theme: {updated_theme['name']}")
        return jsonify({
            "status": "success",
            "data": updated_theme
        }), 200

    except Exception as e:
        logger.error(f"Error in update_theme: {e}")
        return jsonify({"error": "Failed to update theme", "message": str(e)}), 500


@app.route("/api/themes/<int:theme_id>", methods=["DELETE"])
def delete_theme(theme_id: int):
    """
    Delete a theme.

    Args:
        theme_id: Theme ID (path parameter)

    Returns:
        JSON success message or 404 if not found
    """
    try:
        success = data_store.delete_theme(theme_id)

        if not success:
            return jsonify({"error": "Theme not found"}), 404

        logger.info(f"Deleted theme: {theme_id}")
        return jsonify({
            "status": "success",
            "message": f"Theme {theme_id} deleted"
        }), 200

    except Exception as e:
        logger.error(f"Error in delete_theme: {e}")
        return jsonify({"error": "Failed to delete theme", "message": str(e)}), 500


# ============================================================================
# Theme RRG Endpoints
# ============================================================================

@app.route("/api/themes/<int:theme_id>/rrg", methods=["GET"])
def get_theme_rrg(theme_id: int):
    """
    Get RRG data for all tickers in a theme vs SPY benchmark.

    Args:
        theme_id: Theme ID (path parameter)

    Returns:
        JSON with RRG data for each ticker in the theme or 404 if theme not found

    Example response:
        {
            "status": "success",
            "theme": {"id": 1, "name": "AI Infrastructure", ...},
            "rrg_data": {
                "NVDA": {...},
                "AMD": {...},
                ...
            },
            "count": 5
        }
    """
    try:
        # Get theme
        theme = data_store.get_theme(theme_id)
        if not theme:
            return jsonify({"error": "Theme not found"}), 404

        # Calculate RRG for all tickers
        logger.info(f"Calculating RRG for theme: {theme['name']}")
        rrg_data = get_rrg_data_batch(
            theme["tickers"],
            benchmark="SPY",
            period="1y",
            tail=5
        )

        if not rrg_data:
            return jsonify({
                "status": "error",
                "error": "Unable to fetch live RRG data for theme tickers",
            }), 503

        return jsonify({
            "status": "success",
            "theme": {k: v for k, v in theme.items() if k != "tickers"},
            "rrg_data": rrg_data,
            "count": len(rrg_data),
            "missing_count": len(theme["tickers"]) - len(rrg_data)
        }), 200

    except Exception as e:
        logger.error(f"Error in get_theme_rrg: {e}")
        return jsonify({"error": "Failed to fetch theme RRG data", "message": str(e)}), 500


@app.route("/api/themes/rrg-baskets", methods=["GET"])
def get_theme_rrg_baskets():
    """
    Get RRG positions for all themes as equal-weighted baskets.
    Each theme's position is the average RS-Ratio and RS-Momentum
    of its constituent tickers.
    """
    try:
        themes = data_store.get_all_themes()
        if not themes:
            return jsonify({"status": "success", "data": {}, "count": 0}), 200

        # Collect all unique tickers across all themes
        all_tickers = set()
        for theme in themes:
            all_tickers.update(theme.get("tickers", []))

        # Fetch RRG data for all tickers at once
        logger.info(f"Calculating RRG baskets for {len(themes)} themes ({len(all_tickers)} unique tickers)")
        all_rrg = get_rrg_data_batch(
            list(all_tickers), benchmark="SPY", period="1y", tail=5
        )

        # Calculate equal-weighted basket for each theme
        baskets = {}
        for theme in themes:
            tickers = theme.get("tickers", [])
            ticker_data = [all_rrg[t] for t in tickers if t in all_rrg]
            if not ticker_data:
                continue

            n = len(ticker_data)
            avg_ratio = sum(d["current"]["rs_ratio"] for d in ticker_data) / n
            avg_momentum = sum(d["current"]["rs_momentum"] for d in ticker_data) / n

            # Build averaged history from overlapping tail points
            max_tail = min(len(d.get("history", [])) for d in ticker_data) if ticker_data else 0
            history = []
            for i in range(max_tail):
                pts = [d["history"][i] for d in ticker_data if i < len(d.get("history", []))]
                if pts:
                    history.append({
                        "date": pts[0]["date"],
                        "rs_ratio": sum(p["rs_ratio"] for p in pts) / len(pts),
                        "rs_momentum": sum(p["rs_momentum"] for p in pts) / len(pts),
                    })

            baskets[theme["name"]] = {
                "ticker": theme["name"],
                "benchmark": "SPY",
                "current": {
                    "rs_ratio": round(avg_ratio, 2),
                    "rs_momentum": round(avg_momentum, 2),
                },
                "history": history,
                "data_points": n,
                "constituent_count": len(tickers),
                "available_count": n,
                "is_basket": True,
            }

        return jsonify({
            "status": "success",
            "data": baskets,
            "count": len(baskets),
        }), 200

    except Exception as e:
        logger.error(f"Error in get_theme_rrg_baskets: {e}")
        return jsonify({"error": "Failed to calculate theme baskets", "message": str(e)}), 500


# ============================================================================
# Theme Intelligence Endpoints
# ============================================================================


@app.route("/api/themes/<int:theme_id>/suggest-tickers", methods=["POST"])
def suggest_tickers(theme_id: int):
    """
    Suggest additional tickers for a theme based on industry/sector matching.
    Does NOT modify the theme — returns suggestions for user review.
    """
    try:
        theme = data_store.get_theme(theme_id)
        if not theme:
            return jsonify({"error": "Theme not found"}), 404

        data = request.get_json() or {}
        count = min(int(data.get("count", 8)), 20)

        suggestions = intelligence_service.suggest_tickers(
            theme_name=theme["name"],
            theme_thesis=theme["thesis"],
            existing_tickers=theme["tickers"],
            tags=theme.get("tags", []),
            count=count,
        )

        return jsonify({
            "status": "success",
            "theme_id": theme_id,
            "data": suggestions,
            "count": len(suggestions),
        }), 200

    except Exception as e:
        logger.error(f"Error in suggest_tickers: {e}")
        return jsonify({"error": "Failed to suggest tickers", "message": str(e)}), 500


@app.route("/api/universe/stats", methods=["GET"])
def universe_stats():
    """Get stock universe statistics."""
    return jsonify({
        "status": "success",
        "total_tickers": stock_universe.count(),
    }), 200


# ============================================================================
# Signal Detection Endpoints
# ============================================================================

@app.route("/api/signals", methods=["GET"])
def get_signals():
    """
    Get recent signals across all theme tickers.

    Signals include:
    - Large daily price moves (>3%)
    - Proximity to 52-week highs/lows (within 5%)
    - RSI extremes (overbought >70 or oversold <30)

    Query parameters:
        signal_type (optional): Filter by type (large_move, 52week_high, 52week_low, rsi_oversold, rsi_overbought)
        limit (optional): Maximum number of signals to return (default 50)

    Returns:
        JSON list of signals sorted by significance

    Example response:
        {
            "status": "success",
            "data": [
                {
                    "type": "large_move",
                    "ticker": "NVDA",
                    "current_price": 875.50,
                    "pct_change": 4.2,
                    "direction": "up",
                    "date": "2024-03-05",
                    "significance": 4.2
                },
                ...
            ],
            "count": 12
        }
    """
    try:
        # Get all unique tickers
        tickers = data_store.get_all_tickers()

        if not tickers:
            return jsonify({
                "status": "success",
                "data": [],
                "count": 0
            }), 200

        # Detect signals
        logger.info(f"Detecting signals for {len(tickers)} tickers")
        all_signals = detect_signals_batch(tickers)

        # Also check for RRG quadrant transitions
        try:
            rrg_signals = _detect_rrg_transitions(tickers)
            all_signals.extend(rrg_signals)
        except Exception as e:
            logger.debug(f"RRG transition detection failed: {e}")

        # Annotate signals with theme names
        themes = data_store.get_all_themes()
        ticker_to_themes = {}
        for theme in themes:
            for t in theme.get("tickers", []):
                ticker_to_themes.setdefault(t, []).append(theme["name"])
        for signal in all_signals:
            theme_names = ticker_to_themes.get(signal.get("ticker"), [])
            signal["theme"] = ", ".join(theme_names) if theme_names else None

        # Filter by type if requested
        signal_type = request.args.get("signal_type")
        if signal_type:
            all_signals = [s for s in all_signals if s.get("type") == signal_type]

        # Apply limit
        limit = min(int(request.args.get("limit", 50)), 500)
        all_signals = all_signals[:limit]

        return jsonify({
            "status": "success",
            "data": all_signals,
            "count": len(all_signals)
        }), 200

    except Exception as e:
        logger.error(f"Error in get_signals: {e}")
        return jsonify({"error": "Failed to fetch signals", "message": str(e)}), 500


# ============================================================================
# Market Overview Endpoints
# ============================================================================

@app.route("/api/market/overview", methods=["GET"])
def get_market_overview():
    """
    Get broad market data with current values and % changes.

    Returns:
        JSON with major market indices data

    Example response:
        {
            "status": "success",
            "data": {
                "indices": [
                    {
                        "symbol": "^GSPC",
                        "name": "S&P 500",
                        "price": 5234.80,
                        "change": 45.32,
                        "change_pct": 0.87,
                        "last_update": "2024-03-05T16:00:00"
                    },
                    ...
                ]
            }
        }
    """
    try:
        # Major market ETFs (more reliable than index symbols with yfinance)
        indices = [
            {"symbol": "SPY", "name": "S&P 500"},
            {"symbol": "QQQ", "name": "Nasdaq 100"},
            {"symbol": "DIA", "name": "Dow Jones"},
            {"symbol": "IWM", "name": "Russell 2000"},
        ]

        result_indices = []
        errors = []

        for idx in indices:
            try:
                ticker_obj = yf.Ticker(idx["symbol"])
                hist = ticker_obj.history(period="5d", auto_adjust=True)

                if hist is None or hist.empty:
                    errors.append(f"No data for {idx['symbol']}")
                    continue

                # Handle MultiIndex columns
                close = hist["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]

                current = float(close.iloc[-1])
                previous = float(close.iloc[-2]) if len(close) > 1 else current

                change = current - previous
                change_pct = (change / previous * 100) if previous != 0 else 0

                # Use actual data date, not current time
                data_date = hist.index[-1]
                last_update = str(data_date.date()) if hasattr(data_date, 'date') else str(data_date)

                result_indices.append({
                    "symbol": idx["symbol"],
                    "name": idx["name"],
                    "price": round(current, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "last_update": last_update,
                })
            except Exception as e:
                logger.warning(f"Failed to fetch data for {idx['name']}: {e}")
                errors.append(f"{idx['symbol']}: {str(e)}")

        if not result_indices:
            return jsonify({
                "status": "error",
                "error": "Unable to fetch live market data from Yahoo Finance",
                "errors": errors,
            }), 503

        return jsonify({
            "status": "success",
            "data": {
                "indices": result_indices
            },
            "count": len(result_indices),
        }), 200

    except Exception as e:
        logger.error(f"Error in get_market_overview: {e}")
        return jsonify({"status": "error", "error": f"Market data unavailable: {str(e)}"}), 500


# ============================================================================
# Stock Research Endpoints
# ============================================================================

@app.route("/api/stocks/<ticker>/research", methods=["GET"])
def get_stock_research(ticker: str):
    """Get research data and recent entries for a stock. Auto-populates on first view."""
    try:
        t = ticker.upper()
        research = data_store.get_stock_research(t)
        entries = data_store.get_research_entries(t, limit=20)

        if not research:
            # Auto-populate research profile with live market data
            research = _auto_populate_research(t)

        # Add which themes this ticker belongs to
        themes = data_store.get_all_themes()
        ticker_themes = [
            theme["name"] for theme in themes
            if t in theme.get("tickers", [])
        ]
        research["themes"] = ticker_themes

        # Re-fetch entries (may have been created by auto-populate)
        if not entries:
            entries = data_store.get_research_entries(t, limit=20)
        research["recent_entries"] = entries

        return jsonify({"status": "success", "data": research}), 200

    except Exception as e:
        logger.error(f"Error in get_stock_research: {e}")
        return jsonify({"error": "Failed to fetch research", "message": str(e)}), 500


def _auto_populate_research(ticker: str) -> dict:
    """Create initial research profile for a ticker using live yfinance data."""
    return _generate_stock_analysis(ticker, is_refresh=False)


def _generate_stock_analysis(ticker: str, is_refresh: bool = False) -> dict:
    """
    Generate fundamental snapshot from yfinance data.
    Provides factual data only — no analyst-target-based price levels or AI opinions.
    Price targets, catalysts, and risks are left for the user (or future AI) to fill in.
    """
    t = ticker.upper()
    notes_parts = []

    try:
        yf_ticker = yf.Ticker(t)
        info = yf_ticker.info or {}

        company_name = info.get("longName") or info.get("shortName") or t
        sector = info.get("sector", "")
        industry = info.get("industry", "")
        market_cap = info.get("marketCap")

        # --- Build notes ---
        notes_parts.append(company_name)
        if sector and industry:
            notes_parts.append(f"Sector: {sector} | Industry: {industry}")

        if market_cap:
            if market_cap >= 1e12:
                cap_str = f"${market_cap/1e12:.1f}T"
            elif market_cap >= 1e9:
                cap_str = f"${market_cap/1e9:.1f}B"
            else:
                cap_str = f"${market_cap/1e6:.0f}M"
            notes_parts.append(f"Market Cap: {cap_str}")

        # Current price
        current_price = info.get("regularMarketPrice") or info.get("currentPrice")
        if current_price:
            notes_parts.append(f"Current Price: ${current_price:.2f}")

        # Enterprise value
        ev = info.get("enterpriseValue")
        if ev:
            if ev >= 1e12:
                ev_str = f"${ev/1e12:.1f}T"
            elif ev >= 1e9:
                ev_str = f"${ev/1e9:.1f}B"
            else:
                ev_str = f"${ev/1e6:.0f}M"
            notes_parts.append(f"Enterprise Value: {ev_str}")

        # Key valuation metrics
        pe_trailing = info.get("trailingPE")
        pe_forward = info.get("forwardPE")
        peg = info.get("trailingPegRatio")
        ps_trailing = info.get("priceToSalesTrailing12Months")
        pb = info.get("priceToBook")
        ev_revenue = info.get("enterpriseToRevenue")
        ev_ebitda = info.get("enterpriseToEbitda")

        # Forward P/S: calculate from EV and forward revenue if available
        fwd_ps = None
        if ev and info.get("totalRevenue") and info.get("revenueGrowth"):
            fwd_revenue = info["totalRevenue"] * (1 + info["revenueGrowth"])
            if fwd_revenue > 0 and market_cap:
                fwd_ps = market_cap / fwd_revenue

        # EV/EBIT: calculate from EV and EBIT
        ev_ebit = None
        if ev and info.get("ebitda") and info.get("totalRevenue"):
            operating_margin = info.get("operatingMargins")
            if operating_margin and info["totalRevenue"] > 0:
                ebit = info["totalRevenue"] * operating_margin
                if ebit > 0:
                    ev_ebit = ev / ebit

        val_parts = []
        if pe_trailing: val_parts.append(f"P/E: {pe_trailing:.1f}")
        if pe_forward: val_parts.append(f"Fwd P/E: {pe_forward:.1f}")
        if peg: val_parts.append(f"PEG: {peg:.2f}")
        if ps_trailing: val_parts.append(f"P/S: {ps_trailing:.1f}")
        if fwd_ps: val_parts.append(f"Fwd P/S: {fwd_ps:.1f}")
        if pb: val_parts.append(f"P/B: {pb:.1f}")
        if val_parts:
            notes_parts.append("Valuation: " + " | ".join(val_parts))

        ev_parts = []
        if ev_revenue: ev_parts.append(f"EV/Rev: {ev_revenue:.1f}")
        if ev_ebitda: ev_parts.append(f"EV/EBITDA: {ev_ebitda:.1f}")
        if ev_ebit: ev_parts.append(f"EV/EBIT: {ev_ebit:.1f}")
        if ev_parts:
            notes_parts.append("Enterprise: " + " | ".join(ev_parts))

        # Growth metrics
        rev_growth = info.get("revenueGrowth")
        earn_growth = info.get("earningsGrowth")
        growth_parts = []
        if rev_growth: growth_parts.append(f"Revenue Growth: {rev_growth*100:.1f}%")
        if earn_growth: growth_parts.append(f"Earnings Growth: {earn_growth*100:.1f}%")
        if growth_parts:
            notes_parts.append(" | ".join(growth_parts))

        # Margins
        gross = info.get("grossMargins")
        operating = info.get("operatingMargins")
        profit = info.get("profitMargins")
        margin_parts = []
        if gross: margin_parts.append(f"Gross: {gross*100:.1f}%")
        if operating: margin_parts.append(f"Operating: {operating*100:.1f}%")
        if profit: margin_parts.append(f"Net: {profit*100:.1f}%")
        if margin_parts:
            notes_parts.append("Margins: " + " | ".join(margin_parts))

        # 52-week range
        high_52 = info.get("fiftyTwoWeekHigh")
        low_52 = info.get("fiftyTwoWeekLow")
        if high_52 and low_52:
            notes_parts.append(f"52-Week Range: ${low_52:.2f} - ${high_52:.2f}")

        # Add analysis date
        notes_parts.append(f"\n[Data as of: {datetime.now().strftime('%Y-%m-%d %H:%M')}]")

    except Exception as e:
        logger.warning(f"Could not fetch yfinance info for {t}: {e}")
        notes_parts.append(f"Live data fetch failed: {str(e)}")

    notes = "\n".join(notes_parts)

    if is_refresh:
        # Update notes only — preserve user's price levels, catalysts, risks
        existing = data_store.get_stock_research(t)
        if existing:
            result = data_store.upsert_stock_research(ticker=t, notes=notes)
        else:
            result = data_store.upsert_stock_research(
                ticker=t, status="watchlist", notes=notes,
            )
    else:
        result = data_store.upsert_stock_research(
            ticker=t, status="watchlist", notes=notes,
        )

    # Add system entry
    action = "refreshed" if is_refresh else "auto-created"
    data_store.add_research_entry(
        ticker=t,
        content=f"Research profile {action}. {notes_parts[0] if notes_parts else t}",
        entry_type="ai_analysis" if is_refresh else "note",
        source="system",
    )

    return result


@app.route("/api/stocks/<ticker>/refresh", methods=["POST"])
def refresh_stock_analysis(ticker: str):
    """Re-analyze a stock using latest yfinance data. Merges with existing user data."""
    try:
        t = ticker.upper()
        result = _generate_stock_analysis(t, is_refresh=True)

        # Add themes
        themes = data_store.get_all_themes()
        result["themes"] = [
            theme["name"] for theme in themes
            if t in theme.get("tickers", [])
        ]
        result["recent_entries"] = data_store.get_research_entries(t, limit=20)

        return jsonify({"status": "success", "data": result}), 200

    except Exception as e:
        logger.error(f"Error refreshing analysis for {ticker}: {e}")
        return jsonify({"error": f"Failed to refresh: {str(e)}"}), 500


@app.route("/api/stocks/<ticker>/research", methods=["PUT"])
def update_stock_research(ticker: str):
    """Create or update research data for a stock."""
    try:
        data = request.get_json() or {}
        allowed_fields = [
            "status", "buy_target", "sell_target", "stop_loss",
            "position_size", "catalysts", "risks", "notes"
        ]
        filtered = {k: v for k, v in data.items() if k in allowed_fields}

        result = data_store.upsert_stock_research(ticker, **filtered)
        logger.info(f"Updated research for {ticker.upper()}")
        return jsonify({"status": "success", "data": result}), 200

    except Exception as e:
        logger.error(f"Error in update_stock_research: {e}")
        return jsonify({"error": "Failed to update research", "message": str(e)}), 500


@app.route("/api/stocks/<ticker>/notes", methods=["POST"])
def add_stock_note(ticker: str):
    """Add a timestamped research entry for a stock."""
    try:
        data = request.get_json() or {}
        content = data.get("content", "").strip()

        if not content:
            return jsonify({"error": "Content is required"}), 400

        entry = data_store.add_research_entry(
            ticker=ticker,
            content=content,
            entry_type=data.get("entry_type", "note"),
            source=data.get("source", "manual"),
        )

        logger.info(f"Added research note for {ticker.upper()}")
        return jsonify({"status": "success", "data": entry}), 201

    except Exception as e:
        logger.error(f"Error in add_stock_note: {e}")
        return jsonify({"error": "Failed to add note", "message": str(e)}), 500


@app.route("/api/stocks/watchlist", methods=["GET"])
def get_stocks_by_status():
    """Get stocks filtered by status (active, dormant, watchlist)."""
    try:
        status = request.args.get("status", "watchlist")
        stocks = data_store.get_stocks_by_status(status)
        return jsonify({
            "status": "success",
            "data": stocks,
            "count": len(stocks)
        }), 200

    except Exception as e:
        logger.error(f"Error in get_stocks_by_status: {e}")
        return jsonify({"error": "Failed to fetch stocks", "message": str(e)}), 500


@app.route("/api/stocks/search", methods=["GET"])
def search_stocks():
    """Search across all research notes and entries."""
    try:
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify({"status": "success", "data": [], "count": 0}), 200

        results = data_store.search_research(query)
        return jsonify({
            "status": "success",
            "data": results,
            "count": len(results)
        }), 200

    except Exception as e:
        logger.error(f"Error in search_stocks: {e}")
        return jsonify({"error": "Failed to search", "message": str(e)}), 500


# ============================================================================
# Ticker Name Lookup
# ============================================================================

@app.route("/api/tickers/names", methods=["POST"])
def get_ticker_names():
    """Look up company names for a list of tickers. Checks stock universe first, falls back to yfinance."""
    try:
        tickers = request.json.get("tickers", [])
        if not tickers:
            return jsonify({"status": "success", "data": {}}), 200

        upper_tickers = [t.upper() for t in tickers]

        # 1) Check stock universe (instant, local DB)
        conn = stock_universe._get_conn()
        placeholders = ",".join("?" for _ in upper_tickers)
        rows = conn.execute(
            f"SELECT ticker, name FROM stock_universe WHERE ticker IN ({placeholders})",
            upper_tickers
        ).fetchall()
        conn.close()

        names = {row["ticker"]: row["name"] for row in rows}

        # 2) For any missing, fall back to yfinance info cache
        missing = [t for t in upper_tickers if t not in names]
        if missing:
            infos = info_cache.batch_get_or_fetch(missing)
            for ticker, info in infos.items():
                name = info.get("shortName") or info.get("longName")
                if name:
                    names[ticker] = name

        return jsonify({"status": "success", "data": names}), 200

    except Exception as e:
        logger.error(f"Error in get_ticker_names: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


# ============================================================================
# Health Check
# ============================================================================

@app.route("/api/health", methods=["GET"])
def health_check():
    """
    Health check endpoint.

    Returns:
        JSON success message
    """
    return jsonify({
        "status": "ok",
        "service": "Theme Intelligence Dashboard"
    }), 200


# ============================================================================
# Application Startup
# ============================================================================

if __name__ == "__main__":
    logger.info("Starting Theme Intelligence Dashboard API")
    logger.info("Running on http://localhost:5001")
    logger.info("CORS enabled for http://localhost:3000")

    app.run(
        host="localhost",
        port=5001,
        debug=False
    )
