"""
RRG (Relative Rotation Graphs) calculation engine.

Implements the JdK RRG methodology for calculating:
- RS-Line: ratio of ticker price to benchmark price
- RS-Ratio: RS-Line as percentage of its 14-week SMA (centered at 100)
- RS-Momentum: RS-Ratio as percentage of its 14-week SMA (centered at 100)

Standard parameters: weekly data, 14-week lookback, 5-week tail.
Center = 100: >100 outperforming/improving, <100 underperforming/deteriorating.

This module provides the mathematical core for the dashboard's RRG visualization.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf
from functools import lru_cache

logger = logging.getLogger(__name__)

# Cache settings for yfinance data
CACHE_TIMEOUT_MINUTES = 15
_price_data_cache: Dict[str, Tuple[pd.DataFrame, datetime]] = {}


def _get_cached_price_data(
    ticker: str,
    period: str = "1y",
    interval: str = "1wk"
) -> Optional[pd.DataFrame]:
    """
    Fetch price data with simple in-memory caching.

    Args:
        ticker: Stock ticker symbol
        period: Time period for data
        interval: Data interval (1wk for weekly data)

    Returns:
        DataFrame with price data or None if fetch failed
    """
    cache_key = f"{ticker}_{period}_{interval}"

    # Check cache
    if cache_key in _price_data_cache:
        data, timestamp = _price_data_cache[cache_key]
        age_minutes = (datetime.now() - timestamp).total_seconds() / 60
        if age_minutes < CACHE_TIMEOUT_MINUTES:
            return data

    # Fetch new data using Ticker().history() for consistent single-level columns
    try:
        ticker_obj = yf.Ticker(ticker)
        data = ticker_obj.history(period=period, interval=interval, auto_adjust=True)
        if data is None or data.empty:
            logger.warning(f"No price data found for {ticker}")
            return None

        # Flatten MultiIndex columns if present (newer yfinance versions)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Normalize timezone-aware indices to timezone-naive
        # (international tickers return tz-aware timestamps that won't align with US data)
        if data.index.tz is not None:
            data.index = data.index.tz_localize(None)

        _price_data_cache[cache_key] = (data, datetime.now())
        return data
    except Exception as e:
        logger.error(f"Error fetching price data for {ticker}: {e}")
        return None


def calculate_rs_line(
    ticker_data: pd.DataFrame,
    benchmark_data: pd.DataFrame
) -> pd.Series:
    """
    Calculate RS-Line (Relative Strength Line).

    RS-Line = ticker_close / benchmark_close

    Args:
        ticker_data: DataFrame with ticker OHLCV data
        benchmark_data: DataFrame with benchmark OHLCV data

    Returns:
        Series with RS-Line values

    Raises:
        ValueError: If data is missing or incompatible
    """
    if ticker_data.empty or benchmark_data.empty:
        raise ValueError("Cannot calculate RS-Line with empty data")

    # Ensure we have Close prices
    ticker_close = ticker_data.get("Close")
    benchmark_close = benchmark_data.get("Close")

    if ticker_close is None or benchmark_close is None:
        raise ValueError("Missing Close price data")

    # Align dates
    aligned = pd.DataFrame({
        "ticker": ticker_close,
        "benchmark": benchmark_close
    }).dropna()

    if aligned.empty:
        raise ValueError("No overlapping dates between ticker and benchmark")

    # Calculate RS-Line
    rs_line = aligned["ticker"] / aligned["benchmark"]
    return rs_line


def calculate_rs_ratio(rs_line: pd.Series, window: int = 14) -> pd.Series:
    """
    Calculate RS-Ratio using standard ratio-to-moving-average normalization.

    RS-Ratio = (RS-Line / SMA(RS-Line, 14)) × 100

    Centered at 100:
    - 100 = RS-Line at its 14-week average (neutral)
    - > 100 = outperforming vs recent history
    - < 100 = underperforming vs recent history

    This is the standard open approximation of the JdK methodology.
    No arbitrary scaling factors — values naturally range ~90-110.

    Args:
        rs_line: Series with RS-Line values
        window: Rolling window size (default 14 weeks per standard methodology)

    Returns:
        Series with RS-Ratio values (centered at 100)
    """
    if len(rs_line) < window:
        logger.warning(f"RS-Line has fewer than {window} periods, using available data")
        window = max(1, len(rs_line) - 1)

    sma = rs_line.rolling(window=window, min_periods=1).mean()
    sma = sma.replace(0, np.nan)

    return (rs_line / sma) * 100


def calculate_rs_momentum(rs_ratio: pd.Series, window: int = 14) -> pd.Series:
    """
    Calculate RS-Momentum using standard ratio-to-moving-average normalization.

    RS-Momentum = (RS-Ratio / SMA(RS-Ratio, 14)) × 100

    Centered at 100:
    - > 100 = RS-Ratio improving (accelerating relative strength)
    - < 100 = RS-Ratio declining (decelerating relative strength)

    Args:
        rs_ratio: Series with RS-Ratio values
        window: Rolling window for normalization (default 14 weeks)

    Returns:
        Series with RS-Momentum values (centered at 100)
    """
    if len(rs_ratio) < window:
        logger.warning(f"RS-Ratio has fewer than {window} periods, using available data")
        window = max(1, len(rs_ratio) - 1)

    sma = rs_ratio.rolling(window=window, min_periods=1).mean()
    sma = sma.replace(0, np.nan)

    return (rs_ratio / sma) * 100


def get_rrg_data(
    ticker: str,
    benchmark: str = "SPY",
    period: str = "1y",
    tail: int = 5
) -> Optional[Dict]:
    """
    Calculate complete RRG data for a ticker vs benchmark.

    Args:
        ticker: Stock ticker symbol
        benchmark: Benchmark ticker (default SPY)
        period: Historical period to analyze
        tail: Number of recent data points to return for animation trails

    Returns:
        Dictionary with RRG data or None if calculation failed

    Example:
        {
            "ticker": "NVDA",
            "benchmark": "SPY",
            "current": {
                "rs_ratio": 145.2,
                "rs_momentum": 102.5
            },
            "history": [
                {"date": "2024-01-05", "rs_ratio": 140.1, "rs_momentum": 98.3},
                ...
            ]
        }
    """
    try:
        # Fetch price data
        ticker_data = _get_cached_price_data(ticker, period=period, interval="1wk")
        benchmark_data = _get_cached_price_data(benchmark, period=period, interval="1wk")

        if ticker_data is None or benchmark_data is None:
            logger.warning(f"Could not fetch price data for {ticker} or {benchmark}")
            return None

        # Calculate RS-Line
        rs_line = calculate_rs_line(ticker_data, benchmark_data)

        # Calculate RS-Ratio and RS-Momentum (standard 14-week lookback)
        rs_ratio = calculate_rs_ratio(rs_line, window=14)
        rs_momentum = calculate_rs_momentum(rs_ratio, window=14)

        # Combine results
        result_df = pd.DataFrame({
            "rs_ratio": rs_ratio,
            "rs_momentum": rs_momentum
        }).dropna()

        # Remove infinite values
        result_df = result_df[np.isfinite(result_df["rs_ratio"]) & np.isfinite(result_df["rs_momentum"])]

        if result_df.empty:
            logger.warning(f"No valid RRG data for {ticker}")
            return None

        # Get current values
        current = {
            "rs_ratio": float(result_df["rs_ratio"].iloc[-1]),
            "rs_momentum": float(result_df["rs_momentum"].iloc[-1])
        }

        # Get historical tail
        tail_data = result_df.tail(tail).copy()
        history = [
            {
                "date": str(idx.date()),
                "rs_ratio": float(row["rs_ratio"]),
                "rs_momentum": float(row["rs_momentum"])
            }
            for idx, row in tail_data.iterrows()
        ]

        return {
            "ticker": ticker.upper(),
            "benchmark": benchmark.upper(),
            "current": current,
            "history": history,
            "data_points": len(result_df)
        }

    except Exception as e:
        logger.error(f"Error calculating RRG for {ticker}: {e}")
        return None


def get_rrg_data_batch(
    tickers: List[str],
    benchmark: str = "SPY",
    period: str = "1y",
    tail: int = 5
) -> Dict[str, Dict]:
    """
    Calculate RRG data for multiple tickers.

    Gracefully handles errors - if one ticker fails, others continue.

    Args:
        tickers: List of ticker symbols
        benchmark: Benchmark ticker
        period: Historical period
        tail: Number of recent data points to return

    Returns:
        Dictionary mapping tickers to their RRG data
    """
    results = {}

    for ticker in tickers:
        rrg = get_rrg_data(ticker, benchmark=benchmark, period=period, tail=tail)
        if rrg is not None:
            results[ticker] = rrg
        else:
            logger.warning(f"Failed to calculate RRG for {ticker}")

    return results


def get_sector_rrg_data(
    sector_etfs: Optional[List[str]] = None,
    benchmark: str = "SPY",
    period: str = "1y",
    tail: int = 5
) -> Dict[str, Dict]:
    """
    Calculate RRG data for S&P sectors.

    Args:
        sector_etfs: List of sector ETF tickers. Defaults to all 11 S&P sectors.
        benchmark: Benchmark ticker (default SPY)
        period: Historical period
        tail: Number of recent data points

    Returns:
        Dictionary mapping sector ETFs to their RRG data
    """
    if sector_etfs is None:
        # All 11 S&P 500 sector ETFs
        sector_etfs = [
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

    return get_rrg_data_batch(
        sector_etfs,
        benchmark=benchmark,
        period=period,
        tail=tail
    )
