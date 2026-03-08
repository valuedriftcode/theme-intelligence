"""
Stock universe provider.

Maintains a comprehensive database of tradeable stocks for ticker suggestion.
- US stocks: fetched from NASDAQ screener API (~8K tickers)
- International: curated list of major names across HK, Europe, Japan, India, LatAm
- All cached in SQLite with weekly refresh.
"""

import sqlite3
import json
import time
import logging
from typing import List, Dict, Optional
import requests

logger = logging.getLogger(__name__)

NASDAQ_API_URL = "https://api.nasdaq.com/api/screener/stocks"
REFRESH_INTERVAL_SECONDS = 7 * 24 * 3600  # 1 week

# Curated international stocks not covered by NASDAQ API
INTERNATIONAL_STOCKS = [
    # Hong Kong - Tech & Internet
    {"ticker": "0700.HK", "name": "Tencent Holdings", "sector": "Technology", "industry": "Internet Content & Information", "country": "HK"},
    {"ticker": "9988.HK", "name": "Alibaba Group", "sector": "Consumer Cyclical", "industry": "Internet Retail", "country": "HK"},
    {"ticker": "3690.HK", "name": "Meituan", "sector": "Consumer Cyclical", "industry": "Internet Retail", "country": "HK"},
    {"ticker": "9618.HK", "name": "JD.com", "sector": "Consumer Cyclical", "industry": "Internet Retail", "country": "HK"},
    {"ticker": "9888.HK", "name": "Baidu", "sector": "Technology", "industry": "Internet Content & Information", "country": "HK"},
    {"ticker": "1810.HK", "name": "Xiaomi", "sector": "Technology", "industry": "Consumer Electronics", "country": "HK"},
    {"ticker": "0981.HK", "name": "Semiconductor Manufacturing Intl", "sector": "Technology", "industry": "Semiconductors", "country": "HK"},
    # Hong Kong - EV & Auto
    {"ticker": "1211.HK", "name": "BYD Company", "sector": "Consumer Cyclical", "industry": "Auto Manufacturers", "country": "HK"},
    {"ticker": "2015.HK", "name": "Li Auto", "sector": "Consumer Cyclical", "industry": "Auto Manufacturers", "country": "HK"},
    {"ticker": "9868.HK", "name": "XPeng", "sector": "Consumer Cyclical", "industry": "Auto Manufacturers", "country": "HK"},
    {"ticker": "0175.HK", "name": "Geely Automobile", "sector": "Consumer Cyclical", "industry": "Auto Manufacturers", "country": "HK"},
    # Hong Kong - Energy & Power
    {"ticker": "1816.HK", "name": "CGN Power", "sector": "Utilities", "industry": "Utilities - Regulated Electric", "country": "HK"},
    {"ticker": "1133.HK", "name": "Harbin Electric", "sector": "Industrials", "industry": "Electrical Equipment & Parts", "country": "HK"},
    {"ticker": "3393.HK", "name": "Wasion Holdings", "sector": "Technology", "industry": "Scientific & Technical Instruments", "country": "HK"},
    {"ticker": "0902.HK", "name": "Huaneng Power", "sector": "Utilities", "industry": "Utilities - Regulated Electric", "country": "HK"},
    {"ticker": "0836.HK", "name": "China Resources Power", "sector": "Utilities", "industry": "Utilities - Independent Power Producers", "country": "HK"},
    {"ticker": "1038.HK", "name": "CK Infrastructure", "sector": "Utilities", "industry": "Utilities - Diversified", "country": "HK"},
    # Hong Kong - Financials
    {"ticker": "0005.HK", "name": "HSBC Holdings", "sector": "Financial Services", "industry": "Banks - Diversified", "country": "HK"},
    {"ticker": "1398.HK", "name": "ICBC", "sector": "Financial Services", "industry": "Banks - Diversified", "country": "HK"},
    {"ticker": "3988.HK", "name": "Bank of China", "sector": "Financial Services", "industry": "Banks - Diversified", "country": "HK"},
    {"ticker": "2318.HK", "name": "Ping An Insurance", "sector": "Financial Services", "industry": "Insurance - Diversified", "country": "HK"},
    {"ticker": "0388.HK", "name": "Hong Kong Exchanges", "sector": "Financial Services", "industry": "Financial Data & Stock Exchanges", "country": "HK"},
    # Hong Kong - Healthcare
    {"ticker": "2269.HK", "name": "WuXi Biologics", "sector": "Healthcare", "industry": "Biotechnology", "country": "HK"},
    {"ticker": "1177.HK", "name": "Sino Biopharmaceutical", "sector": "Healthcare", "industry": "Drug Manufacturers - Specialty & Generic", "country": "HK"},
    # Hong Kong - Real Estate & Industrials
    {"ticker": "0016.HK", "name": "Sun Hung Kai Properties", "sector": "Real Estate", "industry": "Real Estate - Development", "country": "HK"},
    {"ticker": "0669.HK", "name": "Techtronic Industries", "sector": "Industrials", "industry": "Specialty Industrial Machinery", "country": "HK"},
    {"ticker": "2382.HK", "name": "Sunny Optical", "sector": "Technology", "industry": "Electronic Components", "country": "HK"},
    # China A-shares (Shanghai/Shenzhen)
    {"ticker": "600900.SS", "name": "China Yangtze Power", "sector": "Utilities", "industry": "Utilities - Regulated Electric", "country": "CN"},
    {"ticker": "601012.SS", "name": "LONGi Green Energy", "sector": "Technology", "industry": "Solar", "country": "CN"},
    {"ticker": "300750.SZ", "name": "CATL", "sector": "Industrials", "industry": "Electrical Equipment & Parts", "country": "CN"},
    {"ticker": "000858.SZ", "name": "Wuliangye Yibin", "sector": "Consumer Defensive", "industry": "Beverages - Wineries & Distilleries", "country": "CN"},
    {"ticker": "600519.SS", "name": "Kweichow Moutai", "sector": "Consumer Defensive", "industry": "Beverages - Wineries & Distilleries", "country": "CN"},
    {"ticker": "601899.SS", "name": "Zijin Mining", "sector": "Basic Materials", "industry": "Gold", "country": "CN"},
    # Japan
    {"ticker": "7203.T", "name": "Toyota Motor", "sector": "Consumer Cyclical", "industry": "Auto Manufacturers", "country": "JP"},
    {"ticker": "6758.T", "name": "Sony Group", "sector": "Technology", "industry": "Consumer Electronics", "country": "JP"},
    {"ticker": "6861.T", "name": "Keyence", "sector": "Technology", "industry": "Scientific & Technical Instruments", "country": "JP"},
    {"ticker": "6367.T", "name": "Daikin Industries", "sector": "Industrials", "industry": "Building Products & Equipment", "country": "JP"},
    {"ticker": "8306.T", "name": "Mitsubishi UFJ", "sector": "Financial Services", "industry": "Banks - Diversified", "country": "JP"},
    {"ticker": "9984.T", "name": "SoftBank Group", "sector": "Technology", "industry": "Information Technology Services", "country": "JP"},
    {"ticker": "6501.T", "name": "Hitachi", "sector": "Industrials", "industry": "Conglomerates", "country": "JP"},
    {"ticker": "7741.T", "name": "HOYA Corporation", "sector": "Healthcare", "industry": "Medical Instruments & Supplies", "country": "JP"},
    {"ticker": "6902.T", "name": "Denso", "sector": "Consumer Cyclical", "industry": "Auto Parts", "country": "JP"},
    {"ticker": "4063.T", "name": "Shin-Etsu Chemical", "sector": "Basic Materials", "industry": "Specialty Chemicals", "country": "JP"},
    {"ticker": "8035.T", "name": "Tokyo Electron", "sector": "Technology", "industry": "Semiconductor Equipment & Materials", "country": "JP"},
    # Europe
    {"ticker": "ASML.AS", "name": "ASML Holding", "sector": "Technology", "industry": "Semiconductor Equipment & Materials", "country": "NL"},
    {"ticker": "MC.PA", "name": "LVMH", "sector": "Consumer Cyclical", "industry": "Luxury Goods", "country": "FR"},
    {"ticker": "SAP.DE", "name": "SAP SE", "sector": "Technology", "industry": "Software - Application", "country": "DE"},
    {"ticker": "SIE.DE", "name": "Siemens AG", "sector": "Industrials", "industry": "Conglomerates", "country": "DE"},
    {"ticker": "OR.PA", "name": "L'Oreal", "sector": "Consumer Defensive", "industry": "Household & Personal Products", "country": "FR"},
    {"ticker": "SAN.PA", "name": "Sanofi", "sector": "Healthcare", "industry": "Drug Manufacturers - General", "country": "FR"},
    {"ticker": "AIR.PA", "name": "Airbus SE", "sector": "Industrials", "industry": "Aerospace & Defense", "country": "FR"},
    {"ticker": "NVO.CO", "name": "Novo Nordisk", "sector": "Healthcare", "industry": "Drug Manufacturers - General", "country": "DK"},
    {"ticker": "NESN.SW", "name": "Nestle", "sector": "Consumer Defensive", "industry": "Packaged Foods", "country": "CH"},
    {"ticker": "ROG.SW", "name": "Roche Holding", "sector": "Healthcare", "industry": "Drug Manufacturers - General", "country": "CH"},
    {"ticker": "NOVN.SW", "name": "Novartis", "sector": "Healthcare", "industry": "Drug Manufacturers - General", "country": "CH"},
    {"ticker": "AZN.L", "name": "AstraZeneca", "sector": "Healthcare", "industry": "Drug Manufacturers - General", "country": "UK"},
    {"ticker": "SHEL.L", "name": "Shell PLC", "sector": "Energy", "industry": "Oil & Gas Integrated", "country": "UK"},
    {"ticker": "ULVR.L", "name": "Unilever", "sector": "Consumer Defensive", "industry": "Household & Personal Products", "country": "UK"},
    {"ticker": "RIO.L", "name": "Rio Tinto", "sector": "Basic Materials", "industry": "Other Industrial Metals & Mining", "country": "UK"},
    {"ticker": "GSK.L", "name": "GSK plc", "sector": "Healthcare", "industry": "Drug Manufacturers - General", "country": "UK"},
    {"ticker": "BARC.L", "name": "Barclays", "sector": "Financial Services", "industry": "Banks - Diversified", "country": "UK"},
    {"ticker": "IFX.DE", "name": "Infineon Technologies", "sector": "Technology", "industry": "Semiconductors", "country": "DE"},
    {"ticker": "STM.PA", "name": "STMicroelectronics", "sector": "Technology", "industry": "Semiconductors", "country": "FR"},
    {"ticker": "ENEL.MI", "name": "Enel SpA", "sector": "Utilities", "industry": "Utilities - Regulated Electric", "country": "IT"},
    {"ticker": "ISP.MI", "name": "Intesa Sanpaolo", "sector": "Financial Services", "industry": "Banks - Diversified", "country": "IT"},
    {"ticker": "BBVA.MC", "name": "BBVA", "sector": "Financial Services", "industry": "Banks - Diversified", "country": "ES"},
    # India
    {"ticker": "RELIANCE.NS", "name": "Reliance Industries", "sector": "Energy", "industry": "Oil & Gas Refining & Marketing", "country": "IN"},
    {"ticker": "TCS.NS", "name": "Tata Consultancy", "sector": "Technology", "industry": "Information Technology Services", "country": "IN"},
    {"ticker": "INFY.NS", "name": "Infosys", "sector": "Technology", "industry": "Information Technology Services", "country": "IN"},
    {"ticker": "HDFCBANK.NS", "name": "HDFC Bank", "sector": "Financial Services", "industry": "Banks - Regional", "country": "IN"},
    {"ticker": "ICICIBANK.NS", "name": "ICICI Bank", "sector": "Financial Services", "industry": "Banks - Regional", "country": "IN"},
    {"ticker": "HINDUNILVR.NS", "name": "Hindustan Unilever", "sector": "Consumer Defensive", "industry": "Household & Personal Products", "country": "IN"},
    {"ticker": "BHARTIARTL.NS", "name": "Bharti Airtel", "sector": "Communication Services", "industry": "Telecom Services", "country": "IN"},
    {"ticker": "TATAMOTORS.NS", "name": "Tata Motors", "sector": "Consumer Cyclical", "industry": "Auto Manufacturers", "country": "IN"},
    {"ticker": "ADANIENT.NS", "name": "Adani Enterprises", "sector": "Industrials", "industry": "Conglomerates", "country": "IN"},
    # Latin America
    {"ticker": "VALE3.SA", "name": "Vale SA", "sector": "Basic Materials", "industry": "Other Industrial Metals & Mining", "country": "BR"},
    {"ticker": "PETR4.SA", "name": "Petrobras", "sector": "Energy", "industry": "Oil & Gas Integrated", "country": "BR"},
    {"ticker": "ITUB4.SA", "name": "Itau Unibanco", "sector": "Financial Services", "industry": "Banks - Diversified", "country": "BR"},
    {"ticker": "WEGE3.SA", "name": "WEG SA", "sector": "Industrials", "industry": "Specialty Industrial Machinery", "country": "BR"},
    {"ticker": "BIMBOA.MX", "name": "Grupo Bimbo", "sector": "Consumer Defensive", "industry": "Packaged Foods", "country": "MX"},
    {"ticker": "FEMSAUBD.MX", "name": "FEMSA", "sector": "Consumer Defensive", "industry": "Beverages - Non-Alcoholic", "country": "MX"},
    {"ticker": "GFNORTEO.MX", "name": "Banorte", "sector": "Financial Services", "industry": "Banks - Regional", "country": "MX"},
    # Korea
    {"ticker": "005930.KS", "name": "Samsung Electronics", "sector": "Technology", "industry": "Consumer Electronics", "country": "KR"},
    {"ticker": "000660.KS", "name": "SK Hynix", "sector": "Technology", "industry": "Semiconductors", "country": "KR"},
    {"ticker": "373220.KS", "name": "LG Energy Solution", "sector": "Industrials", "industry": "Electrical Equipment & Parts", "country": "KR"},
    {"ticker": "051910.KS", "name": "LG Chem", "sector": "Basic Materials", "industry": "Specialty Chemicals", "country": "KR"},
    {"ticker": "035420.KS", "name": "Naver", "sector": "Technology", "industry": "Internet Content & Information", "country": "KR"},
    # Taiwan
    {"ticker": "2330.TW", "name": "TSMC", "sector": "Technology", "industry": "Semiconductors", "country": "TW"},
    {"ticker": "2317.TW", "name": "Hon Hai Precision", "sector": "Technology", "industry": "Electronic Components", "country": "TW"},
    {"ticker": "2454.TW", "name": "MediaTek", "sector": "Technology", "industry": "Semiconductors", "country": "TW"},
    # Australia
    {"ticker": "BHP.AX", "name": "BHP Group", "sector": "Basic Materials", "industry": "Other Industrial Metals & Mining", "country": "AU"},
    {"ticker": "CBA.AX", "name": "Commonwealth Bank", "sector": "Financial Services", "industry": "Banks - Diversified", "country": "AU"},
    {"ticker": "CSL.AX", "name": "CSL Limited", "sector": "Healthcare", "industry": "Biotechnology", "country": "AU"},
    # Southeast Asia
    {"ticker": "D05.SI", "name": "DBS Group", "sector": "Financial Services", "industry": "Banks - Diversified", "country": "SG"},
    {"ticker": "SE", "name": "Sea Limited", "sector": "Technology", "industry": "Internet Content & Information", "country": "SG"},
    {"ticker": "GRAB", "name": "Grab Holdings", "sector": "Technology", "industry": "Software - Application", "country": "SG"},
    # Thematic ETFs (global)
    {"ticker": "URA", "name": "Global X Uranium ETF", "sector": "Energy", "industry": "Uranium", "country": "US"},
    {"ticker": "SOXX", "name": "iShares Semiconductor ETF", "sector": "Technology", "industry": "Semiconductors", "country": "US"},
    {"ticker": "XBI", "name": "SPDR S&P Biotech ETF", "sector": "Healthcare", "industry": "Biotechnology", "country": "US"},
    {"ticker": "TAN", "name": "Invesco Solar ETF", "sector": "Technology", "industry": "Solar", "country": "US"},
    {"ticker": "LIT", "name": "Global X Lithium ETF", "sector": "Basic Materials", "industry": "Specialty Chemicals", "country": "US"},
    {"ticker": "KWEB", "name": "KraneShares China Internet ETF", "sector": "Technology", "industry": "Internet Content & Information", "country": "CN"},
    {"ticker": "REMX", "name": "VanEck Rare Earth ETF", "sector": "Basic Materials", "industry": "Other Industrial Metals & Mining", "country": "US"},
    {"ticker": "ICLN", "name": "iShares Global Clean Energy ETF", "sector": "Utilities", "industry": "Utilities - Renewable", "country": "US"},
    {"ticker": "ARKK", "name": "ARK Innovation ETF", "sector": "Technology", "industry": "Asset Management", "country": "US"},
    {"ticker": "EWW", "name": "iShares MSCI Mexico ETF", "sector": "Financial Services", "industry": "Asset Management", "country": "MX"},
    {"ticker": "EWZ", "name": "iShares MSCI Brazil ETF", "sector": "Financial Services", "industry": "Asset Management", "country": "BR"},
    {"ticker": "FXI", "name": "iShares China Large-Cap ETF", "sector": "Financial Services", "industry": "Asset Management", "country": "CN"},
    {"ticker": "INDA", "name": "iShares MSCI India ETF", "sector": "Financial Services", "industry": "Asset Management", "country": "IN"},
    {"ticker": "EWJ", "name": "iShares MSCI Japan ETF", "sector": "Financial Services", "industry": "Asset Management", "country": "JP"},
    {"ticker": "VNM", "name": "VanEck Vietnam ETF", "sector": "Financial Services", "industry": "Asset Management", "country": "VN"},
]


class StockUniverse:
    """
    Comprehensive stock universe with SQLite caching.
    US stocks from NASDAQ API + curated international names.
    """

    def __init__(self, db_path: str = "theme_intel.db"):
        self.db_path = db_path
        self._init_table()
        self._ensure_fresh()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_universe (
                ticker TEXT PRIMARY KEY,
                name TEXT,
                sector TEXT,
                industry TEXT,
                market_cap REAL,
                country TEXT DEFAULT 'US',
                last_updated REAL
            )
        """)
        conn.commit()
        conn.close()

    def _ensure_fresh(self):
        """Refresh if data is stale or empty."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT MIN(last_updated) as oldest, COUNT(*) as cnt FROM stock_universe"
        ).fetchone()
        conn.close()

        count = row["cnt"] if row else 0
        oldest = row["oldest"] if row else 0

        if count < 100 or (time.time() - (oldest or 0)) > REFRESH_INTERVAL_SECONDS:
            logger.info("Stock universe is stale or empty, refreshing...")
            self.refresh()

    def refresh(self):
        """Fetch US stocks from NASDAQ API and merge with international list."""
        us_stocks = self._fetch_nasdaq()
        intl_stocks = INTERNATIONAL_STOCKS

        conn = self._get_conn()
        now = time.time()

        # Insert US stocks
        for stock in us_stocks:
            conn.execute(
                """INSERT OR REPLACE INTO stock_universe
                   (ticker, name, sector, industry, market_cap, country, last_updated)
                   VALUES (?, ?, ?, ?, ?, 'US', ?)""",
                (stock["ticker"], stock["name"], stock["sector"],
                 stock["industry"], stock.get("market_cap"), now)
            )

        # Insert international stocks
        for stock in intl_stocks:
            conn.execute(
                """INSERT OR REPLACE INTO stock_universe
                   (ticker, name, sector, industry, market_cap, country, last_updated)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (stock["ticker"], stock["name"], stock["sector"],
                 stock["industry"], stock.get("market_cap"), stock["country"], now)
            )

        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM stock_universe").fetchone()[0]
        conn.close()
        logger.info(f"Stock universe refreshed: {len(us_stocks)} US + {len(intl_stocks)} international = {total} total")

    def _fetch_nasdaq(self) -> List[Dict]:
        """Fetch all US-listed stocks from NASDAQ screener API."""
        stocks = []
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Accept": "application/json",
            }
            resp = requests.get(
                NASDAQ_API_URL,
                params={"tableType": "earnings", "limit": 0, "download": "true"},
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            rows = data.get("data", {}).get("rows", [])
            if not rows:
                # Try alternate response structure
                rows = data.get("data", {}).get("table", {}).get("rows", [])

            for row in rows:
                ticker = (row.get("symbol") or row.get("ticker") or "").strip()
                if not ticker or len(ticker) > 10:
                    continue
                # Skip warrants, units, preferred
                if any(c in ticker for c in ["/", "^", "+"]):
                    continue

                name = row.get("name") or row.get("companyName") or ""
                sector = row.get("sector") or ""
                industry = row.get("industry") or ""

                cap_str = row.get("marketCap") or row.get("mktCap") or ""
                market_cap = self._parse_market_cap(cap_str)

                stocks.append({
                    "ticker": ticker,
                    "name": name,
                    "sector": sector,
                    "industry": industry,
                    "market_cap": market_cap,
                })

            logger.info(f"Fetched {len(stocks)} US stocks from NASDAQ API")

        except Exception as e:
            logger.error(f"Failed to fetch from NASDAQ API: {e}")
            # If NASDAQ fetch fails, we still have international stocks

        return stocks

    def _parse_market_cap(self, cap_str) -> Optional[float]:
        """Parse market cap string like '$1.5B' or numeric value."""
        if not cap_str:
            return None
        if isinstance(cap_str, (int, float)):
            return float(cap_str)
        try:
            s = str(cap_str).replace("$", "").replace(",", "").strip()
            if not s:
                return None
            multiplier = 1
            if s.endswith("T"):
                multiplier = 1e12
                s = s[:-1]
            elif s.endswith("B"):
                multiplier = 1e9
                s = s[:-1]
            elif s.endswith("M"):
                multiplier = 1e6
                s = s[:-1]
            return float(s) * multiplier
        except (ValueError, TypeError):
            return None

    # ---- Query methods ----

    def get_by_industry(self, industry: str) -> List[Dict]:
        """Get all tickers in a given industry."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM stock_universe WHERE industry = ? ORDER BY market_cap DESC",
            (industry,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_by_industries(self, industries: List[str]) -> List[Dict]:
        """Get all tickers across multiple industries."""
        if not industries:
            return []
        conn = self._get_conn()
        placeholders = ",".join("?" * len(industries))
        rows = conn.execute(
            f"SELECT * FROM stock_universe WHERE industry IN ({placeholders}) ORDER BY market_cap DESC",
            industries
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_by_sector(self, sector: str) -> List[Dict]:
        """Get all tickers in a given sector."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM stock_universe WHERE sector = ? ORDER BY market_cap DESC",
            (sector,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_ticker_info(self, ticker: str) -> Optional[Dict]:
        """Get cached universe info for a single ticker."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM stock_universe WHERE ticker = ?", (ticker.upper(),)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_ticker_infos(self, tickers: List[str]) -> Dict[str, Dict]:
        """Get cached universe info for multiple tickers."""
        if not tickers:
            return {}
        conn = self._get_conn()
        placeholders = ",".join("?" * len(tickers))
        rows = conn.execute(
            f"SELECT * FROM stock_universe WHERE ticker IN ({placeholders})",
            [t.upper() for t in tickers]
        ).fetchall()
        conn.close()
        return {r["ticker"]: dict(r) for r in rows}

    def search(self, keyword: str, limit: int = 50) -> List[Dict]:
        """Search by name, ticker, or industry."""
        conn = self._get_conn()
        pattern = f"%{keyword}%"
        rows = conn.execute(
            """SELECT * FROM stock_universe
               WHERE ticker LIKE ? OR name LIKE ? OR industry LIKE ?
               ORDER BY market_cap DESC LIMIT ?""",
            (pattern, pattern, pattern, limit)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def count(self) -> int:
        conn = self._get_conn()
        c = conn.execute("SELECT COUNT(*) FROM stock_universe").fetchone()[0]
        conn.close()
        return c
