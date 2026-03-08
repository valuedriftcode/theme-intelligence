"""
Mock data provider for when Yahoo Finance is unavailable.
Generates realistic-looking RRG, signal, and market data.
On the user's real computer, yfinance will work and this module won't be used.
"""

import math
import random
from datetime import datetime, timedelta

# Seed for consistent-ish data across restarts
random.seed(42)

SECTOR_NAMES = {
    "XLK": "Technology", "XLF": "Financials", "XLE": "Energy",
    "XLV": "Healthcare", "XLI": "Industrials", "XLP": "Consumer Staples",
    "XLU": "Utilities", "XLB": "Materials", "XLC": "Communications",
    "XLRE": "Real Estate", "XLY": "Consumer Discretionary"
}

# Pre-set quadrant positions for sectors (realistic snapshot)
SECTOR_POSITIONS = {
    "XLK":  {"ratio": 108, "momentum": 103, "quadrant": "leading"},
    "XLF":  {"ratio": 104, "momentum": 97,  "quadrant": "weakening"},
    "XLE":  {"ratio": 94,  "momentum": 95,  "quadrant": "lagging"},
    "XLV":  {"ratio": 96,  "momentum": 106, "quadrant": "improving"},
    "XLI":  {"ratio": 102, "momentum": 101, "quadrant": "leading"},
    "XLP":  {"ratio": 93,  "momentum": 98,  "quadrant": "lagging"},
    "XLU":  {"ratio": 91,  "momentum": 104, "quadrant": "improving"},
    "XLB":  {"ratio": 97,  "momentum": 94,  "quadrant": "lagging"},
    "XLC":  {"ratio": 106, "momentum": 105, "quadrant": "leading"},
    "XLRE": {"ratio": 89,  "momentum": 102, "quadrant": "improving"},
    "XLY":  {"ratio": 103, "momentum": 93,  "quadrant": "weakening"},
}

# Pre-set positions for theme stocks
STOCK_POSITIONS = {
    "NVDA": {"ratio": 115, "momentum": 108}, "AMD": {"ratio": 105, "momentum": 96},
    "AVGO": {"ratio": 110, "momentum": 104}, "MRVL": {"ratio": 98, "momentum": 107},
    "SMCI": {"ratio": 88, "momentum": 92},
    "CEG":  {"ratio": 112, "momentum": 110}, "VST": {"ratio": 109, "momentum": 106},
    "NRG":  {"ratio": 104, "momentum": 102}, "SMR": {"ratio": 95, "momentum": 108},
    "LEU":  {"ratio": 101, "momentum": 105},
    "LLY":  {"ratio": 107, "momentum": 94},  "NVO": {"ratio": 103, "momentum": 91},
    "AMGN": {"ratio": 96, "momentum": 98},   "VKTX": {"ratio": 85, "momentum": 110},
    "EWW":  {"ratio": 92, "momentum": 96},   "BSMX": {"ratio": 88, "momentum": 102},
    "VIST": {"ratio": 97, "momentum": 104},  "CSAN": {"ratio": 90, "momentum": 93},
}


def _generate_trail(current_ratio, current_momentum, points=5):
    """Generate a clockwise trail leading to current position."""
    trail = []
    for i in range(points):
        age = points - i
        # Trail points move clockwise toward current
        angle_offset = age * 0.3
        trail.append({
            "date": (datetime.now() - timedelta(weeks=age)).strftime("%Y-%m-%d"),
            "rs_ratio": round(current_ratio - age * random.uniform(0.5, 2.0) * math.cos(angle_offset), 2),
            "rs_momentum": round(current_momentum - age * random.uniform(0.3, 1.5) * math.sin(angle_offset), 2),
        })
    return trail


def get_mock_rrg_data(ticker, benchmark="SPY"):
    """Generate mock RRG data for a single ticker."""
    pos = STOCK_POSITIONS.get(ticker, SECTOR_POSITIONS.get(ticker))
    if not pos:
        # Unknown ticker - random position
        pos = {
            "ratio": round(random.uniform(85, 115), 1),
            "momentum": round(random.uniform(88, 112), 1)
        }

    ratio = pos["ratio"] + random.uniform(-1, 1)
    momentum = pos["momentum"] + random.uniform(-1, 1)
    trail = _generate_trail(ratio, momentum)

    return {
        "ticker": ticker.upper(),
        "benchmark": benchmark.upper(),
        "current": {
            "rs_ratio": round(ratio, 2),
            "rs_momentum": round(momentum, 2)
        },
        "history": trail,
        "data_points": 52
    }


def get_mock_rrg_batch(tickers, benchmark="SPY"):
    """Generate mock RRG data for multiple tickers."""
    return {t: get_mock_rrg_data(t, benchmark) for t in tickers}


def get_mock_sector_rrg():
    """Generate mock RRG data for all sectors."""
    return get_mock_rrg_batch(list(SECTOR_NAMES.keys()))


def get_mock_market_overview():
    """Generate mock market overview data."""
    return [
        {"symbol": "SPY", "name": "S&P 500", "price": 5842.15, "change": 23.47, "change_pct": 0.40},
        {"symbol": "QQQ", "name": "Nasdaq 100", "price": 20318.62, "change": -45.81, "change_pct": -0.23},
        {"symbol": "DIA", "name": "Dow Jones", "price": 43127.50, "change": 112.30, "change_pct": 0.26},
        {"symbol": "IWM", "name": "Russell 2000", "price": 2087.33, "change": -8.54, "change_pct": -0.41},
    ]


def get_mock_signals(tickers):
    """Generate mock signals for given tickers."""
    signal_types = [
        ("large_move_up", "Price surged {pct:.1f}% on heavy volume", "green"),
        ("large_move_down", "Price dropped {pct:.1f}% on heavy volume", "red"),
        ("near_52w_high", "Within {pct:.1f}% of 52-week high", "blue"),
        ("near_52w_low", "Within {pct:.1f}% of 52-week low", "orange"),
        ("rsi_overbought", "RSI at {val:.0f} - overbought territory", "yellow"),
        ("rsi_oversold", "RSI at {val:.0f} - oversold territory", "purple"),
    ]

    signals = []
    today = datetime.now().strftime("%Y-%m-%d")

    # Generate a few signals for random tickers
    for ticker in random.sample(tickers, min(8, len(tickers))):
        sig_type, template, color = random.choice(signal_types)
        pct = random.uniform(3.0, 12.0)
        val = random.uniform(20, 35) if "oversold" in sig_type else random.uniform(72, 88)

        signals.append({
            "ticker": ticker,
            "type": sig_type,
            "details": template.format(pct=pct, val=val),
            "date": today,
            "significance": round(random.uniform(2.0, 9.0), 1),
            "theme": _get_theme_for_ticker(ticker),
        })

    signals.sort(key=lambda s: s["significance"], reverse=True)
    return signals


def _get_theme_for_ticker(ticker):
    """Map ticker to its theme name."""
    theme_map = {
        "NVDA": "AI Infrastructure", "AMD": "AI Infrastructure", "AVGO": "AI Infrastructure",
        "MRVL": "AI Infrastructure", "SMCI": "AI Infrastructure",
        "CEG": "Nuclear Renaissance", "VST": "Nuclear Renaissance", "NRG": "Nuclear Renaissance",
        "SMR": "Nuclear Renaissance", "LEU": "Nuclear Renaissance",
        "LLY": "GLP-1 / Obesity", "NVO": "GLP-1 / Obesity", "AMGN": "GLP-1 / Obesity",
        "VKTX": "GLP-1 / Obesity",
        "EWW": "Nearshoring / Mexico", "BSMX": "Nearshoring / Mexico",
        "VIST": "Nearshoring / Mexico", "CSAN": "Nearshoring / Mexico",
    }
    return theme_map.get(ticker, "Unknown")
