"""
Theme intelligence service — ticker suggestion and theme discovery.

Pluggable architecture: HeuristicThemeIntelligence uses yfinance data and
industry matching. Can be swapped for ClaudeThemeIntelligence (or DeepSeek, etc.)
by implementing the same interface.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class ThemeIntelligenceService(ABC):
    """Abstract base class for theme intelligence. Subclass to swap AI backend."""

    @abstractmethod
    def suggest_tickers(
        self,
        theme_name: str,
        theme_thesis: str,
        existing_tickers: List[str],
        tags: List[str],
        count: int = 8,
    ) -> List[Dict]:
        """
        Suggest additional tickers for an existing theme.
        Returns list of: { ticker, company_name, sector, industry, market_cap,
                           rationale, confidence }
        """
        pass

    @abstractmethod
    def discover_themes(
        self, existing_themes: List[Dict], count: int = 3
    ) -> List[Dict]:
        """
        Generate new theme suggestions.
        Returns list of: { name, thesis, tickers[], tags[], rationale, confidence }
        """
        pass


class HeuristicThemeIntelligence(ThemeIntelligenceService):
    """
    Heuristic-based intelligence using StockUniverse and InfoCache.

    Suggest tickers algorithm:
    1. Look up industries/sectors of existing theme tickers
    2. Query universe for all tickers in matching industries
    3. Score by: industry match, sector match, keyword relevance, market cap
    4. Enrich top candidates with yfinance .info details
    """

    def __init__(self, stock_universe, info_cache):
        self.universe = stock_universe
        self.info_cache = info_cache

    def suggest_tickers(
        self, theme_name, theme_thesis, existing_tickers, tags, count=8
    ):
        existing_upper = set(t.upper() for t in existing_tickers)

        # Step 1: Find industries/sectors of existing tickers
        existing_infos = self.universe.get_ticker_infos(list(existing_upper))
        target_industries = set()
        target_sectors = set()

        for ticker, info in existing_infos.items():
            if info.get("industry"):
                target_industries.add(info["industry"])
            if info.get("sector"):
                target_sectors.add(info["sector"])

        # For tickers not in our universe, try yfinance .info
        missing = existing_upper - set(existing_infos.keys())
        if missing:
            yf_infos = self.info_cache.batch_get_or_fetch(list(missing))
            for ticker, info in yf_infos.items():
                ind = info.get("industry")
                sec = info.get("sector")
                if ind:
                    target_industries.add(ind)
                if sec:
                    target_sectors.add(sec)

        if not target_industries and not target_sectors:
            logger.warning(f"No industry/sector data for theme '{theme_name}'")
            return []

        # Step 2: Get candidates from matching industries
        candidates_raw = self.universe.get_by_industries(list(target_industries))

        # Also get same-sector stocks (lower priority)
        for sector in target_sectors:
            candidates_raw.extend(self.universe.get_by_sector(sector))

        # Deduplicate
        seen = set()
        candidates = []
        for c in candidates_raw:
            t = c["ticker"]
            if t not in seen and t not in existing_upper:
                seen.add(t)
                candidates.append(c)

        # Step 3: Score candidates
        search_terms = self._extract_search_terms(theme_name, theme_thesis, tags)
        scored = []

        for c in candidates:
            score = 0.0
            reasons = []

            # Industry match (strongest signal)
            if c.get("industry") in target_industries:
                score += 50
                reasons.append(f"Same industry: {c['industry']}")
            elif c.get("sector") in target_sectors:
                score += 20
                reasons.append(f"Same sector: {c['sector']}")

            # Keyword match against company name
            name_lower = (c.get("name") or "").lower()
            industry_lower = (c.get("industry") or "").lower()
            text = f"{name_lower} {industry_lower}"

            hits = sum(1 for term in search_terms if term in text)
            if hits > 0:
                score += hits * 15
                reasons.append(f"Keyword matches: {hits}")

            # Market cap preference (liquidity)
            mcap = c.get("market_cap")
            if mcap and mcap > 10e9:
                score += 8
            elif mcap and mcap > 1e9:
                score += 5
            elif mcap and mcap > 100e6:
                score += 2

            if score < 15:
                continue

            scored.append({
                **c,
                "_score": score,
                "rationale": "; ".join(reasons),
                "confidence": min(1.0, score / 100),
            })

        scored.sort(key=lambda x: x["_score"], reverse=True)

        # Step 4: Take top candidates and enrich with yfinance .info
        top = scored[: count * 2]  # fetch extra in case some fail
        tickers_to_enrich = [c["ticker"] for c in top]
        enriched = self.info_cache.batch_get_or_fetch(tickers_to_enrich)

        results = []
        for c in top:
            info = enriched.get(c["ticker"])
            market_cap = c.get("market_cap")
            company_name = c.get("name") or c["ticker"]

            # Enrich from .info if available
            if info:
                company_name = info.get("longName") or info.get("shortName") or company_name
                if not market_cap:
                    market_cap = info.get("marketCap")

            results.append({
                "ticker": c["ticker"],
                "company_name": company_name,
                "sector": c.get("sector") or (info or {}).get("sector", ""),
                "industry": c.get("industry") or (info or {}).get("industry", ""),
                "market_cap": self._format_market_cap(market_cap),
                "market_cap_raw": market_cap,
                "rationale": c["rationale"],
                "confidence": c["confidence"],
                "country": c.get("country", "US"),
            })

            if len(results) >= count:
                break

        return results

    def discover_themes(self, existing_themes, count=3):
        """
        Placeholder for heuristic theme discovery.
        Real theme generation is done via Claude Code in conversation.
        """
        return []

    def _extract_search_terms(self, name, thesis, tags):
        """Extract meaningful search terms from theme context."""
        stop_words = {
            "the", "and", "for", "with", "that", "this", "from", "are", "was",
            "will", "companies", "company", "investing", "investment", "theme",
            "through", "based", "their", "also", "have", "been", "being",
            "into", "such", "each", "which", "about", "more", "other",
        }
        words = set()
        for text in [name, thesis]:
            if not text:
                continue
            for word in text.lower().split():
                cleaned = word.strip(".,;:!?()[]\"'-/")
                if len(cleaned) > 3 and cleaned not in stop_words:
                    words.add(cleaned)
        words.update(t.lower() for t in (tags or []) if len(t) > 2)
        return list(words)

    def _format_market_cap(self, cap) -> str:
        if not cap:
            return "--"
        if cap >= 1e12:
            return f"${cap / 1e12:.1f}T"
        if cap >= 1e9:
            return f"${cap / 1e9:.1f}B"
        if cap >= 1e6:
            return f"${cap / 1e6:.0f}M"
        return f"${cap:,.0f}"
