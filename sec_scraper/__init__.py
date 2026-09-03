"""
sec-scraper: Pull quarterly revenue from SEC EDGAR filings and generate publication-ready financial charts.
"""

from sec_scraper.chart import RevenueChart
from sec_scraper.client import (
    DEFAULT_USER_AGENT,
    KNOWN_TICKER_TO_CIK,
    EdgarClient,
    FixtureTransportAdapter,
    HttpTransportAdapter,
    TransportAdapter,
)
from sec_scraper.normalizer import RevenueNormalizer
from sec_scraper.cli import run_pipeline

__all__ = [
    "RevenueNormalizer",
    "RevenueChart",
    "EdgarClient",
    "TransportAdapter",
    "HttpTransportAdapter",
    "FixtureTransportAdapter",
    "DEFAULT_USER_AGENT",
    "KNOWN_TICKER_TO_CIK",
    "run_pipeline",
]
