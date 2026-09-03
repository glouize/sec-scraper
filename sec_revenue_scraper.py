"""
SEC EDGAR Revenue Scraper & Financial Chart Generator
======================================================
Legacy facade and script entry point maintaining backward compatibility
with existing automation and callers, delegating to the deep sec_scraper package.
"""

from __future__ import annotations

import sys
from typing import Any

import pandas as pd

from sec_scraper.chart import RevenueChart
from sec_scraper.client import (
    DEFAULT_USER_AGENT,
    KNOWN_TICKER_TO_CIK,
    EdgarClient,
    HttpTransportAdapter,
)
from sec_scraper.cli import main, run_pipeline
from sec_scraper.config import ScraperConfig
from sec_scraper.normalizer import RevenueNormalizer

# Re-export legacy constants
TICKER_TO_CIK = KNOWN_TICKER_TO_CIK


def resolve_cik(ticker_or_cik: str, user_agent: str = DEFAULT_USER_AGENT) -> tuple[str, str]:
    """Resolve a ticker symbol to a 10-digit zero-padded CIK and company name."""
    client = EdgarClient(user_agent=user_agent)
    return client.resolve_cik(ticker_or_cik)


def fetch_sec_company_facts(cik: str, user_agent: str = DEFAULT_USER_AGENT) -> dict[str, Any]:
    """Fetch structured XBRL company facts directly from SEC EDGAR API."""
    client = EdgarClient(user_agent=user_agent)
    return client.get_company_facts(cik)


def parse_quarterly_revenue(facts: dict[str, Any]) -> pd.DataFrame:
    """
    Extract quarterly revenue from SEC facts.
    Accurately handles Form 10-Q standalone 3-month filings and derives
    Form 10-K 4th quarter figures where Q4 = FY - 9M.
    """
    normalizer = RevenueNormalizer()
    return normalizer.normalize(facts, count=8)


def generate_revenue_chart(
    df: pd.DataFrame, company_name: str, ticker_symbol: str, output_path: str
) -> str:
    """Generate a clean, high-resolution financial chart."""
    chart = RevenueChart()
    return chart.save(df, company_name=company_name, ticker_symbol=ticker_symbol, output_path=output_path)


if __name__ == "__main__":
    sys.exit(main())
