"""
Command-line orchestrator for the sec-scraper pipeline.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Sequence

import pandas as pd

from sec_scraper.chart import RevenueChart
from sec_scraper.client import DEFAULT_USER_AGENT, EdgarClient, TransportAdapter
from sec_scraper.normalizer import RevenueNormalizer


def run_pipeline(
    ticker: str = "TSLA",
    user_agent: str = DEFAULT_USER_AGENT,
    output_csv: str = "data/tesla_revenue_last_8_quarters.csv",
    output_chart: str = "charts/tesla_revenue_last_8_quarters.png",
    client: EdgarClient | None = None,
    normalizer: RevenueNormalizer | None = None,
    chart: RevenueChart | None = None,
    quiet: bool = False,
) -> tuple[pd.DataFrame, str, str]:
    """Execute the end-to-end extraction, normalization, and visualization pipeline."""
    client = client or EdgarClient(user_agent=user_agent)
    normalizer = normalizer or RevenueNormalizer()
    chart = chart or RevenueChart()

    cik, display_name = client.resolve_cik(ticker)
    if not quiet:
        print(f"Target Company: {display_name} (Ticker: {ticker.upper()}, CIK: {cik})")
        print(f"[1/4] Scraping SEC EDGAR facts for CIK {cik} ...")

    facts = client.get_company_facts(ticker)
    company_name = facts.get("entityName", display_name)

    if not quiet:
        print("[2/4] Normalizing US-GAAP quarterly figures ...")

    df = normalizer.normalize(facts, count=8)

    if not quiet:
        print("\n" + "=" * 70)
        print(f" {company_name} ({ticker.upper()}) — Last 8 Quarters Revenue ")
        print("=" * 70)
        summary_cols = ["quarter", "period_end", "form", "revenue_billions", "qoq_growth_pct", "yoy_growth_pct"]
        print(df[summary_cols].to_string(index=False, justify="center"))
        print("=" * 70 + "\n")

    os.makedirs(os.path.dirname(os.path.abspath(output_csv)), exist_ok=True)
    df.to_csv(output_csv, index=False)
    if not quiet:
        print(f"[3/4] Data exported to: {output_csv}")

    chart.save(df, company_name=company_name, ticker_symbol=ticker, output_path=output_chart)
    if not quiet:
        print(f"[4/4] Chart successfully rendered and saved to: {output_chart}")
        print("\nPipeline completed successfully!")

    return df, output_csv, output_chart


def main(args: Sequence[str] | None = None) -> int:
    """CLI entry point parsing command-line flags and executing pipeline."""
    parser = argparse.ArgumentParser(description="Scrape last 8 quarters revenue from SEC EDGAR and generate chart.")
    parser.add_argument("--ticker", type=str, default="TSLA", help="Company ticker symbol (default: TSLA)")
    parser.add_argument("--user-agent", type=str, default=DEFAULT_USER_AGENT, help="SEC-compliant User-Agent header")
    parser.add_argument("--output-csv", type=str, default="data/tesla_revenue_last_8_quarters.csv", help="CSV output path")
    parser.add_argument("--output-chart", type=str, default="charts/tesla_revenue_last_8_quarters.png", help="Chart PNG output path")
    parsed = parser.parse_args(args)

    try:
        run_pipeline(
            ticker=parsed.ticker,
            user_agent=parsed.user_agent,
            output_csv=parsed.output_csv,
            output_chart=parsed.output_chart,
        )
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
