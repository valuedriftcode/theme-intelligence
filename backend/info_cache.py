"""
SQLite-backed cache for yfinance Ticker.info data.

yfinance .info calls take 1-2 seconds each — too slow for real-time suggestion.
This cache stores results in SQLite with a 4-hour TTL, and supports parallel
batch fetching via ThreadPoolExecutor for uncached tickers.

Only used for enriching the final ~10-15 suggestion candidates with
detailed fundamentals (growth, margins, description). Industry matching
uses the StockUniverse cache instead.
"""

import sqlite3
import json
import time
import logging
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 4 * 3600  # 4 hours


class InfoCache:

    def __init__(self, db_path: str = "theme_intel.db"):
        self.db_path = db_path
        self._init_table()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS info_cache (
                ticker TEXT PRIMARY KEY,
                info_json TEXT NOT NULL,
                cached_at REAL NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def get(self, ticker: str) -> Optional[Dict]:
        """Get cached info, or None if stale/missing."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT info_json, cached_at FROM info_cache WHERE ticker = ?",
            (ticker.upper(),)
        ).fetchone()
        conn.close()

        if row is None:
            return None
        if time.time() - row["cached_at"] > CACHE_TTL_SECONDS:
            return None
        return json.loads(row["info_json"])

    def put(self, ticker: str, info: Dict):
        """Store info data in cache."""
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO info_cache (ticker, info_json, cached_at)
               VALUES (?, ?, ?)""",
            (ticker.upper(), json.dumps(info), time.time())
        )
        conn.commit()
        conn.close()

    def fetch_and_cache(self, ticker: str) -> Optional[Dict]:
        """Fetch .info from yfinance, cache it, return it."""
        try:
            info = yf.Ticker(ticker).info
            if info and (info.get("regularMarketPrice") or info.get("currentPrice")):
                self.put(ticker, info)
                return info
        except Exception as e:
            logger.warning(f"Failed to fetch info for {ticker}: {e}")
        return None

    def get_or_fetch(self, ticker: str) -> Optional[Dict]:
        """Get from cache, or fetch if missing/stale."""
        cached = self.get(ticker)
        if cached:
            return cached
        return self.fetch_and_cache(ticker)

    def batch_get_or_fetch(
        self, tickers: List[str], max_workers: int = 8
    ) -> Dict[str, Dict]:
        """
        Batch fetch info for multiple tickers.
        Uses thread pool for uncached tickers (yfinance .info is I/O-bound).
        """
        result = {}
        to_fetch = []

        for t in tickers:
            cached = self.get(t.upper())
            if cached:
                result[t.upper()] = cached
            else:
                to_fetch.append(t.upper())

        if not to_fetch:
            return result

        logger.info(f"Fetching .info for {len(to_fetch)} uncached tickers")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.fetch_and_cache, t): t for t in to_fetch}
            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    info = future.result()
                    if info:
                        result[ticker] = info
                except Exception as e:
                    logger.warning(f"Failed to fetch {ticker}: {e}")

        return result
