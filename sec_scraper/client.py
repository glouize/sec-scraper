"""
SEC EDGAR ingestion client with an injectable transport adapter seam.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Protocol

DEFAULT_USER_AGENT = "FinancialResearch/1.0 (academic_research@example.com)"

KNOWN_TICKER_TO_CIK: dict[str, str] = {
    "TSLA": "0001318605",
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "NVDA": "0001045810",
    "GOOGL": "0001652044",
    "AMZN": "0001018724",
    "META": "0001326801",
}


class TransportAdapter(Protocol):
    """Port for JSON network requests across the external SEC boundary."""

    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        """Fetch and return JSON from a URL."""
        ...


class HttpTransportAdapter:
    """Production HTTP transport adapter utilizing urllib.request."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content)


class FixtureTransportAdapter:
    """In-memory transport adapter for testing and offline fixtures."""

    def __init__(self, fixtures: dict[str, Any] | None = None):
        self.fixtures: dict[str, Any] = fixtures or {}
        self.calls: list[dict[str, Any]] = []

    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        self.calls.append({"url": url, "headers": headers})
        if url in self.fixtures:
            return self.fixtures[url]
        # Match by substring if full URL is not exact
        for fixture_url, data in self.fixtures.items():
            if fixture_url in url or url in fixture_url:
                return data
        raise KeyError(f"No fixture configured for URL: {url}")


class EdgarClient:
    """
    Deep client module for SEC EDGAR interactions.
    Encapsulates CIK resolution, Fair Access User-Agent headers, and XBRL company facts fetching.
    """

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        transport: TransportAdapter | None = None,
        known_tickers: dict[str, str] | None = None,
    ):
        self.user_agent = user_agent
        self.transport = transport or HttpTransportAdapter()
        self.known_tickers = known_tickers or dict(KNOWN_TICKER_TO_CIK)

    def resolve_cik(self, ticker_or_cik: str) -> tuple[str, str]:
        """Resolve a ticker symbol to a 10-digit zero-padded CIK and display name."""
        clean_symbol = ticker_or_cik.strip().upper()

        if clean_symbol in self.known_tickers:
            return self.known_tickers[clean_symbol], clean_symbol

        if clean_symbol.isdigit():
            return clean_symbol.zfill(10), clean_symbol

        # Query SEC company_tickers.json directory
        url = "https://www.sec.gov/files/company_tickers.json"
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        try:
            data = self.transport.get_json(url, headers=headers)
            for entry in data.values():
                if entry.get("ticker") == clean_symbol:
                    cik = str(entry["cik_str"]).zfill(10)
                    title = entry.get("title", clean_symbol)
                    # Cache resolved CIK for subsequent lookups
                    self.known_tickers[clean_symbol] = cik
                    return cik, title
        except Exception as exc:
            pass

        raise ValueError(f"Could not resolve CIK for symbol: {ticker_or_cik}")

    def get_company_facts(self, ticker_or_cik: str) -> dict[str, Any]:
        """Fetch structured XBRL company facts for a company."""
        cik, _ = self.resolve_cik(ticker_or_cik)
        padded_cik = cik.zfill(10)
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{padded_cik}.json"
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        return self.transport.get_json(url, headers=headers)

