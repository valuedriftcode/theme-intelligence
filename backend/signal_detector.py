"""
Signal detection engine for investment themes.

Identifies important market signals including:
- Large daily price moves (>3%)
- Proximity to 52-week highs/lows (within 5%)
- Overbought/oversold conditions (RSI)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Cache for price data (ticker -> (data, timestamp))
_signal_cache: Dict[str, tuple] = {}
CACHE_TIMEOUT_MINUTES = 15


def _get_cached_data(ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
    """
    Fetch daily price data with caching.
    Uses yf.Ticker().history() which is more reliable than yf.download().
    """
    cache_key = f"{ticker}_{period}"

    # Check cache
    if cache_key in _signal_cache:
        data, timestamp = _signal_cache[cache_key]
        age_minutes = (datetime.now() - timestamp).total_seconds() / 60
        if age_minutes < CACHE_TIMEOUT_MINUTES:
            return data

    # Fetch new data using Ticker().history() — avoids the datetime/str bug in yf.download()
    try:
        ticker_obj = yf.Ticker(ticker)
        data = ticker_obj.history(period=period, auto_adjust=True)

        if data is None or data.empty:
            logger.warning(f"No data found for {ticker}")
            return None

        # Flatten MultiIndex columns if present (newer yfinance versions)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Ensure we have the columns we need
        if "Close" not in data.columns:
            logger.warning(f"No Close column for {ticker}, columns: {data.columns.tolist()}")
            return None

        _signal_cache[cache_key] = (data, datetime.now())
        return data
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {e}")
        return None


def _safe_float(val):
    """Safely convert a value to float, handling numpy arrays and Series."""
    if isinstance(val, (pd.Series, np.ndarray)):
        val = val.iloc[0] if isinstance(val, pd.Series) else val.item()
    return float(val)


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).
    RSI = 100 - (100 / (1 + RS))
    where RS = Average Gain / Average Loss
    """
    # Flatten if it's a DataFrame column with MultiIndex
    if isinstance(prices, pd.DataFrame):
        prices = prices.iloc[:, 0]

    if len(prices) < period + 1:
        return pd.Series(np.nan, index=prices.index)

    delta = prices.diff()
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    avg_gains = gains.rolling(window=period).mean()
    avg_losses = losses.rolling(window=period).mean()
    rs = avg_gains / avg_losses.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def get_price_change_signal(ticker: str) -> Optional[Dict]:
    """Check for large daily price moves (>3%)."""
    try:
        data = _get_cached_data(ticker, period="3mo")
        if data is None or len(data) < 2:
            return None

        close = data["Close"]
        # Handle case where Close might be a DataFrame
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        current = _safe_float(close.iloc[-1])
        previous = _safe_float(close.iloc[-2])

        if previous == 0:
            return None

        pct_change = ((current - previous) / previous) * 100

        if abs(pct_change) > 3.0:
            return {
                "type": "large_move_up" if pct_change > 0 else "large_move_down",
                "ticker": ticker.upper(),
                "current_price": current,
                "pct_change": round(pct_change, 2),
                "details": f"Price {'surged' if pct_change > 0 else 'dropped'} {abs(pct_change):.1f}%",
                "date": str(data.index[-1].date()) if hasattr(data.index[-1], 'date') else str(data.index[-1]),
                "significance": abs(pct_change)
            }

        return None

    except Exception as e:
        logger.error(f"Error checking price change for {ticker}: {e}")
        return None


def get_52week_extreme_signal(ticker: str) -> Optional[List[Dict]]:
    """Check for proximity to 52-week highs/lows (within 5%)."""
    try:
        data = _get_cached_data(ticker, period="1y")
        if data is None or len(data) < 50:
            return None

        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        high_52w = _safe_float(close.max())
        low_52w = _safe_float(close.min())
        current_price = _safe_float(close.iloc[-1])
        date_str = str(data.index[-1].date()) if hasattr(data.index[-1], 'date') else str(data.index[-1])

        signals = []

        # Near 52-week high
        if high_52w > 0:
            distance_from_high = ((high_52w - current_price) / high_52w) * 100
            if 0 <= distance_from_high <= 5:
                signals.append({
                    "type": "near_52w_high",
                    "ticker": ticker.upper(),
                    "current_price": current_price,
                    "details": f"Within {distance_from_high:.1f}% of 52-week high (${high_52w:.2f})",
                    "date": date_str,
                    "significance": 5 - distance_from_high
                })

        # Near 52-week low
        if low_52w > 0:
            distance_from_low = ((current_price - low_52w) / low_52w) * 100
            if 0 <= distance_from_low <= 5:
                signals.append({
                    "type": "near_52w_low",
                    "ticker": ticker.upper(),
                    "current_price": current_price,
                    "details": f"Within {distance_from_low:.1f}% of 52-week low (${low_52w:.2f})",
                    "date": date_str,
                    "significance": 5 - distance_from_low
                })

        return signals if signals else None

    except Exception as e:
        logger.error(f"Error checking 52-week extremes for {ticker}: {e}")
        return None


def get_rsi_extreme_signal(ticker: str) -> Optional[Dict]:
    """Check for RSI extremes (below 30 = oversold, above 70 = overbought)."""
    try:
        data = _get_cached_data(ticker, period="3mo")
        if data is None or len(data) < 20:
            return None

        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        rsi = calculate_rsi(close, period=14)
        latest_rsi = _safe_float(rsi.iloc[-1])
        current_price = _safe_float(close.iloc[-1])
        date_str = str(data.index[-1].date()) if hasattr(data.index[-1], 'date') else str(data.index[-1])

        if np.isnan(latest_rsi):
            return None

        if latest_rsi < 30:
            return {
                "type": "rsi_oversold",
                "ticker": ticker.upper(),
                "current_price": current_price,
                "rsi": round(latest_rsi, 1),
                "details": f"RSI at {latest_rsi:.0f} - oversold territory",
                "date": date_str,
                "significance": 30 - latest_rsi
            }
        elif latest_rsi > 70:
            return {
                "type": "rsi_overbought",
                "ticker": ticker.upper(),
                "current_price": current_price,
                "rsi": round(latest_rsi, 1),
                "details": f"RSI at {latest_rsi:.0f} - overbought territory",
                "date": date_str,
                "significance": latest_rsi - 70
            }

        return None

    except Exception as e:
        logger.error(f"Error checking RSI for {ticker}: {e}")
        return None


def get_ma_crossover_signals(ticker: str) -> List[Dict]:
    """
    Detect moving average crossover signals:
    - Golden Cross: 50 SMA crosses above 200 SMA
    - Death Cross: 50 SMA crosses below 200 SMA
    - Price crossing above/below 50 SMA
    """
    try:
        data = _get_cached_data(ticker, period="1y")
        if data is None or len(data) < 200:
            return []

        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        sma50 = close.rolling(window=50).mean()
        sma200 = close.rolling(window=200).mean()

        if sma50.isna().iloc[-1] or sma200.isna().iloc[-1]:
            return []

        current_price = _safe_float(close.iloc[-1])
        date_str = str(data.index[-1].date()) if hasattr(data.index[-1], 'date') else str(data.index[-1])
        signals = []

        # Check for 50/200 SMA crossover in last 5 trading days
        lookback = min(6, len(sma50.dropna()))
        if lookback >= 2:
            now_above = _safe_float(sma50.iloc[-1]) > _safe_float(sma200.iloc[-1])
            was_above = _safe_float(sma50.iloc[-lookback]) > _safe_float(sma200.iloc[-lookback])

            if now_above and not was_above:
                signals.append({
                    "type": "golden_cross",
                    "ticker": ticker.upper(),
                    "current_price": current_price,
                    "details": "50-day SMA crossed above 200-day SMA (bullish)",
                    "date": date_str,
                    "significance": 8.0,
                })
            elif not now_above and was_above:
                signals.append({
                    "type": "death_cross",
                    "ticker": ticker.upper(),
                    "current_price": current_price,
                    "details": "50-day SMA crossed below 200-day SMA (bearish)",
                    "date": date_str,
                    "significance": 8.0,
                })

        # Check price vs 50 SMA crossover in last 3 days
        lookback_short = min(4, len(close.dropna()))
        if lookback_short >= 2:
            sma50_now = _safe_float(sma50.iloc[-1])
            now_above_sma = current_price > sma50_now
            prev_price = _safe_float(close.iloc[-lookback_short])
            prev_sma = _safe_float(sma50.iloc[-lookback_short])
            was_above_sma = prev_price > prev_sma

            if now_above_sma and not was_above_sma:
                signals.append({
                    "type": "price_above_50sma",
                    "ticker": ticker.upper(),
                    "current_price": current_price,
                    "details": f"Price crossed above 50-day SMA (${sma50_now:.2f})",
                    "date": date_str,
                    "significance": 5.0,
                })
            elif not now_above_sma and was_above_sma:
                signals.append({
                    "type": "price_below_50sma",
                    "ticker": ticker.upper(),
                    "current_price": current_price,
                    "details": f"Price crossed below 50-day SMA (${sma50_now:.2f})",
                    "date": date_str,
                    "significance": 5.0,
                })

        return signals

    except Exception as e:
        logger.error(f"Error checking MA crossovers for {ticker}: {e}")
        return []


def detect_all_signals(ticker: str) -> List[Dict]:
    """Detect all signals for a given ticker."""
    signals = []

    move_signal = get_price_change_signal(ticker)
    if move_signal:
        signals.append(move_signal)

    extreme_signals = get_52week_extreme_signal(ticker)
    if extreme_signals:
        signals.extend(extreme_signals)

    rsi_signal = get_rsi_extreme_signal(ticker)
    if rsi_signal:
        signals.append(rsi_signal)

    ma_signals = get_ma_crossover_signals(ticker)
    if ma_signals:
        signals.extend(ma_signals)

    signals.sort(key=lambda x: x.get("significance", 0), reverse=True)
    return signals


def detect_signals_batch(tickers: List[str]) -> List[Dict]:
    """Detect signals across multiple tickers. Handles errors gracefully."""
    all_signals = []

    for ticker in tickers:
        try:
            signals = detect_all_signals(ticker)
            all_signals.extend(signals)
        except Exception as e:
            logger.error(f"Error detecting signals for {ticker}: {e}")

    all_signals.sort(key=lambda x: x.get("significance", 0), reverse=True)
    return all_signals
