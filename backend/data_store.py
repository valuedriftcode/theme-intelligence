"""
SQLite data storage for themes and related data.
Manages theme creation, updates, and persistence.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple


class DataStore:
    """
    Simple SQLite-based storage for themes and tickers.
    Handles all database operations with proper error handling.
    """

    def __init__(self, db_path: str = "theme_intel.db"):
        """
        Initialize the data store and create tables if they don't exist.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize database tables."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create themes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS themes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                thesis TEXT NOT NULL,
                tags TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create theme_tickers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS theme_tickers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                theme_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (theme_id) REFERENCES themes(id) ON DELETE CASCADE
            )
        """)

        # Stock-level research (one record per ticker, independent of themes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_research (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'active',
                buy_target REAL,
                sell_target REAL,
                stop_loss REAL,
                position_size TEXT,
                catalysts TEXT DEFAULT '[]',
                risks TEXT DEFAULT '[]',
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Timestamped research log (append-only)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                entry_type TEXT NOT NULL DEFAULT 'note',
                content TEXT NOT NULL,
                source TEXT DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

        # Initialize with sample themes if empty
        if self.get_all_themes() == []:
            self._init_sample_themes()

    def _init_sample_themes(self) -> None:
        """Initialize database with sample themes."""
        sample_themes = [
            {
                "name": "AI Infrastructure",
                "thesis": "Companies powering the AI revolution through semiconductors, data centers, and computing infrastructure",
                "tickers": ["NVDA", "AMD", "AVGO", "MRVL", "SMCI"],
                "tags": ["semiconductors", "AI", "infrastructure", "cloud"]
            },
            {
                "name": "Nuclear Renaissance",
                "thesis": "Nuclear energy players benefiting from energy security, climate solutions, and renewed policy support",
                "tickers": ["CEG", "VST", "NRG", "SMR", "LEU"],
                "tags": ["energy", "nuclear", "clean-energy", "commodities"]
            },
            {
                "name": "GLP-1 / Obesity",
                "thesis": "Pharmaceutical companies developing and manufacturing GLP-1 receptor agonists for obesity treatment",
                "tickers": ["LLY", "NVO", "AMGN", "VKTX"],
                "tags": ["healthcare", "pharma", "obesity", "obesity-treatment"]
            },
            {
                "name": "Nearshoring / Mexico",
                "thesis": "Mexico and nearshoring beneficiaries as supply chains shift from Asia to Americas",
                "tickers": ["EWW", "BSMX", "VIST", "CSAN"],
                "tags": ["mexico", "nearshoring", "supply-chain", "emerging-markets"]
            }
        ]

        for theme_data in sample_themes:
            self.create_theme(
                name=theme_data["name"],
                thesis=theme_data["thesis"],
                tickers=theme_data["tickers"],
                tags=theme_data["tags"]
            )

    def create_theme(
        self,
        name: str,
        thesis: str,
        tickers: List[str],
        tags: List[str]
    ) -> Dict:
        """
        Create a new theme with associated tickers.

        Args:
            name: Theme name
            thesis: Investment thesis description
            tickers: List of stock tickers
            tags: List of tags for categorization

        Returns:
            Dictionary with created theme data including id
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Insert theme
            cursor.execute(
                """
                INSERT INTO themes (name, thesis, tags)
                VALUES (?, ?, ?)
                """,
                (name, thesis, json.dumps(tags))
            )
            theme_id = cursor.lastrowid

            # Insert tickers
            for ticker in tickers:
                cursor.execute(
                    """
                    INSERT INTO theme_tickers (theme_id, ticker)
                    VALUES (?, ?)
                    """,
                    (theme_id, ticker.upper())
                )

            conn.commit()

            return {
                "id": theme_id,
                "name": name,
                "thesis": thesis,
                "tickers": [t.upper() for t in tickers],
                "tags": tags,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        finally:
            conn.close()

    def get_all_themes(self) -> List[Dict]:
        """
        Get all themes with their tickers.

        Returns:
            List of theme dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM themes ORDER BY created_at DESC")
            themes = cursor.fetchall()

            result = []
            for theme_row in themes:
                theme_dict = dict(theme_row)
                theme_dict["tags"] = json.loads(theme_dict["tags"])

                # Get tickers for this theme
                cursor.execute(
                    "SELECT ticker FROM theme_tickers WHERE theme_id = ? ORDER BY added_at",
                    (theme_dict["id"],)
                )
                tickers = [row[0] for row in cursor.fetchall()]
                theme_dict["tickers"] = tickers

                result.append(theme_dict)

            return result
        finally:
            conn.close()

    def get_theme(self, theme_id: int) -> Optional[Dict]:
        """
        Get a specific theme by ID.

        Args:
            theme_id: Theme ID

        Returns:
            Theme dictionary or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM themes WHERE id = ?", (theme_id,))
            theme_row = cursor.fetchone()

            if not theme_row:
                return None

            theme_dict = dict(theme_row)
            theme_dict["tags"] = json.loads(theme_dict["tags"])

            # Get tickers
            cursor.execute(
                "SELECT ticker FROM theme_tickers WHERE theme_id = ? ORDER BY added_at",
                (theme_id,)
            )
            tickers = [row[0] for row in cursor.fetchall()]
            theme_dict["tickers"] = tickers

            return theme_dict
        finally:
            conn.close()

    def update_theme(
        self,
        theme_id: int,
        name: Optional[str] = None,
        thesis: Optional[str] = None,
        tickers: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """
        Update an existing theme.

        Args:
            theme_id: Theme ID to update
            name: New theme name (optional)
            thesis: New thesis (optional)
            tickers: New list of tickers (optional)
            tags: New list of tags (optional)

        Returns:
            Updated theme dictionary or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Check if theme exists
            cursor.execute("SELECT * FROM themes WHERE id = ?", (theme_id,))
            if not cursor.fetchone():
                return None

            # Update theme fields if provided
            update_fields = []
            params = []

            if name is not None:
                update_fields.append("name = ?")
                params.append(name)

            if thesis is not None:
                update_fields.append("thesis = ?")
                params.append(thesis)

            if tags is not None:
                update_fields.append("tags = ?")
                params.append(json.dumps(tags))

            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(theme_id)

            if len(update_fields) > 1:  # More than just updated_at
                cursor.execute(
                    f"UPDATE themes SET {', '.join(update_fields)} WHERE id = ?",
                    params
                )

            # Update tickers if provided
            if tickers is not None:
                cursor.execute("DELETE FROM theme_tickers WHERE theme_id = ?", (theme_id,))
                for ticker in tickers:
                    cursor.execute(
                        "INSERT INTO theme_tickers (theme_id, ticker) VALUES (?, ?)",
                        (theme_id, ticker.upper())
                    )

            conn.commit()

            # Return updated theme
            return self.get_theme(theme_id)
        finally:
            conn.close()

    def delete_theme(self, theme_id: int) -> bool:
        """
        Delete a theme and its associated tickers.

        Args:
            theme_id: Theme ID to delete

        Returns:
            True if deleted, False if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM themes WHERE id = ?", (theme_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_all_tickers(self) -> List[str]:
        """
        Get all unique tickers across all themes.

        Returns:
            Sorted list of unique tickers
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT DISTINCT ticker FROM theme_tickers ORDER BY ticker")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    # ========================================================================
    # Stock Research
    # ========================================================================

    def get_stock_research(self, ticker: str) -> Optional[Dict]:
        """Get research data for a stock, including its theme memberships."""
        ticker = ticker.upper()
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM stock_research WHERE ticker = ?", (ticker,))
            row = cursor.fetchone()

            if not row:
                return None

            data = dict(row)
            data["catalysts"] = json.loads(data.get("catalysts") or "[]")
            data["risks"] = json.loads(data.get("risks") or "[]")

            # Get theme memberships
            cursor.execute("""
                SELECT t.name FROM themes t
                JOIN theme_tickers tt ON t.id = tt.theme_id
                WHERE tt.ticker = ?
            """, (ticker,))
            data["themes"] = [r[0] for r in cursor.fetchall()]

            return data
        finally:
            conn.close()

    def upsert_stock_research(self, ticker: str, **kwargs) -> Dict:
        """Create or update stock research. Returns the saved record."""
        ticker = ticker.upper()
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Check if exists
            cursor.execute("SELECT id FROM stock_research WHERE ticker = ?", (ticker,))
            exists = cursor.fetchone()

            if exists:
                # Build dynamic UPDATE
                fields = []
                params = []
                for key in ["status", "buy_target", "sell_target", "stop_loss",
                            "position_size", "notes"]:
                    if key in kwargs:
                        fields.append(f"{key} = ?")
                        params.append(kwargs[key])

                for key in ["catalysts", "risks"]:
                    if key in kwargs:
                        fields.append(f"{key} = ?")
                        params.append(json.dumps(kwargs[key]))

                fields.append("updated_at = CURRENT_TIMESTAMP")
                params.append(ticker)

                if fields:
                    cursor.execute(
                        f"UPDATE stock_research SET {', '.join(fields)} WHERE ticker = ?",
                        params
                    )
            else:
                catalysts = json.dumps(kwargs.get("catalysts", []))
                risks = json.dumps(kwargs.get("risks", []))
                cursor.execute("""
                    INSERT INTO stock_research
                        (ticker, status, buy_target, sell_target, stop_loss,
                         position_size, catalysts, risks, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ticker,
                    kwargs.get("status", "active"),
                    kwargs.get("buy_target"),
                    kwargs.get("sell_target"),
                    kwargs.get("stop_loss"),
                    kwargs.get("position_size"),
                    catalysts,
                    risks,
                    kwargs.get("notes", ""),
                ))

            conn.commit()
            return self.get_stock_research(ticker)
        finally:
            conn.close()

    def get_stocks_by_status(self, status: str) -> List[Dict]:
        """Get all stocks with a given status."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT * FROM stock_research WHERE status = ? ORDER BY updated_at DESC",
                (status,)
            )
            results = []
            for row in cursor.fetchall():
                data = dict(row)
                data["catalysts"] = json.loads(data.get("catalysts") or "[]")
                data["risks"] = json.loads(data.get("risks") or "[]")
                # Get theme memberships
                cursor.execute("""
                    SELECT t.name FROM themes t
                    JOIN theme_tickers tt ON t.id = tt.theme_id
                    WHERE tt.ticker = ?
                """, (data["ticker"],))
                data["themes"] = [r[0] for r in cursor.fetchall()]
                results.append(data)
            return results
        finally:
            conn.close()

    def get_all_stock_research(self) -> List[Dict]:
        """Get all stock research records."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM stock_research ORDER BY updated_at DESC")
            results = []
            for row in cursor.fetchall():
                data = dict(row)
                data["catalysts"] = json.loads(data.get("catalysts") or "[]")
                data["risks"] = json.loads(data.get("risks") or "[]")
                results.append(data)
            return results
        finally:
            conn.close()

    def add_research_entry(
        self, ticker: str, content: str,
        entry_type: str = "note", source: str = "manual"
    ) -> Dict:
        """Add a timestamped research entry for a stock."""
        ticker = ticker.upper()
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Auto-create stock_research record if it doesn't exist
            cursor.execute("SELECT id FROM stock_research WHERE ticker = ?", (ticker,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO stock_research (ticker) VALUES (?)", (ticker,)
                )

            cursor.execute("""
                INSERT INTO research_entries (ticker, entry_type, content, source)
                VALUES (?, ?, ?, ?)
            """, (ticker, entry_type, content, source))

            entry_id = cursor.lastrowid
            conn.commit()

            return {
                "id": entry_id,
                "ticker": ticker,
                "entry_type": entry_type,
                "content": content,
                "source": source,
                "created_at": datetime.utcnow().isoformat(),
            }
        finally:
            conn.close()

    def get_research_entries(self, ticker: str, limit: int = 50) -> List[Dict]:
        """Get research entries for a stock, newest first."""
        ticker = ticker.upper()
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM research_entries
                WHERE ticker = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (ticker, limit))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def search_research(self, query: str) -> List[Dict]:
        """Search across stock research notes and entries."""
        conn = self._get_connection()
        cursor = conn.cursor()
        pattern = f"%{query}%"

        try:
            # Search stock_research notes
            cursor.execute("""
                SELECT ticker, 'research' as match_type, notes as matched_text,
                       updated_at as date
                FROM stock_research
                WHERE notes LIKE ? OR catalysts LIKE ? OR risks LIKE ?
                ORDER BY updated_at DESC
            """, (pattern, pattern, pattern))
            results = [dict(row) for row in cursor.fetchall()]

            # Search research_entries
            cursor.execute("""
                SELECT ticker, entry_type as match_type, content as matched_text,
                       created_at as date
                FROM research_entries
                WHERE content LIKE ?
                ORDER BY created_at DESC
                LIMIT 50
            """, (pattern,))
            results.extend([dict(row) for row in cursor.fetchall()])

            return results
        finally:
            conn.close()
