"""
Command-line orchestrator for the sec-scraper pipeline.
"""

from __future__ import annotations

import os
import sys
from typing import Sequence

import pandas as pd

from sec_scraper.chart import RevenueChart
from sec_scraper.client import DEFAULT_USER_AGENT, EdgarClient, TransportAdapter
from sec_scraper.config import ScraperConfig
from sec_scraper.normalizer import RevenueNormalizer


def run_pipeline(
    ticker: str = "TSLA",
    quarters: int = 8,
    user_agent: str | None = None,
    output_csv: str | None = None,
    output_chart: str | None = None,
    concept: str | None = None,
    no_chart: bool = False,
    config: ScraperConfig | None = None,
    client: EdgarClient | None = None,
    normalizer: RevenueNormalizer | None = None,
    chart: RevenueChart | None = None,
    quiet: bool = False,
) -> tuple[pd.DataFrame, str, str | None]:
    """Execute the end-to-end extraction, normalization, and visualization pipeline."""
    if config is not None:
        effective_ticker = config.ticker
        effective_quarters = config.quarters
        effective_user_agent = config.user_agent
        effective_csv = output_csv or config.resolve_output_csv()
        effective_chart = output_chart if output_chart is not None else config.resolve_output_chart()
        effective_concept = concept or config.concept
        effective_no_chart = config.no_chart if not no_chart else True
        effective_quiet = quiet or config.quiet
    else:
        effective_ticker = ticker
        effective_quarters = quarters
        effective_user_agent = user_agent or DEFAULT_USER_AGENT
        fallback_cfg = ScraperConfig(
            ticker=ticker,
            quarters=quarters,
            user_agent=effective_user_agent,
            output_csv=output_csv,
            output_chart=output_chart,
            concept=concept,
            no_chart=no_chart,
            quiet=quiet,
        )
        effective_csv = fallback_cfg.resolve_output_csv()
        effective_chart = fallback_cfg.resolve_output_chart()
        effective_concept = concept
        effective_no_chart = no_chart
        effective_quiet = quiet

    client = client or EdgarClient(user_agent=effective_user_agent)
    normalizer = normalizer or RevenueNormalizer(concept=effective_concept)
    chart = chart or RevenueChart()

    cik, display_name = client.resolve_cik(effective_ticker)
    if not effective_quiet:
        print(f"Target Company: {display_name} (Ticker: {effective_ticker.upper()}, CIK: {cik})")
        print(f"[1/4] Scraping SEC EDGAR facts for CIK {cik} ...")

    facts = client.get_company_facts(effective_ticker)
    company_name = facts.get("entityName", display_name)

    if not effective_quiet:
        print("[2/4] Normalizing US-GAAP quarterly figures ...")

    df = normalizer.normalize(facts, count=effective_quarters, concept=effective_concept)

    if not effective_quiet:
        print("\n" + "=" * 70)
        print(f" {company_name} ({effective_ticker.upper()}) \u2014 Last {len(df)} Quarters Revenue ")
        print("=" * 70)
        summary_cols = ["quarter", "period_end", "form", "revenue_billions", "qoq_growth_pct", "yoy_growth_pct"]
        print(df[summary_cols].to_string(index=False, justify="center"))
        print("=" * 70 + "\n")

    os.makedirs(os.path.dirname(os.path.abspath(effective_csv)), exist_ok=True)
    df.to_csv(effective_csv, index=False)
    if not effective_quiet:
        print(f"[3/4] Data exported to: {effective_csv}")

    saved_chart: str | None = None
    if not effective_no_chart and effective_chart:
        chart.save(df, company_name=company_name, ticker_symbol=effective_ticker, output_path=effective_chart)
        saved_chart = effective_chart
        if not effective_quiet:
            print(f"[4/4] Chart successfully rendered and saved to: {effective_chart}")
    elif not effective_quiet:
        print("[4/4] Chart generation skipped (--no-chart enabled).")

    if not effective_quiet:
        print("\nPipeline completed successfully!")

    return df, effective_csv, saved_chart


def main(args: Sequence[str] | None = None) -> int:
    """CLI entry point parsing command-line flags and executing pipeline."""
    try:
        config = ScraperConfig.from_cli_args(args)
        run_pipeline(
            ticker=config.ticker,
            quarters=config.quarters,
            user_agent=config.user_agent,
            output_csv=config.resolve_output_csv(),
            output_chart=config.resolve_output_chart(),
            concept=config.concept,
            no_chart=config.no_chart,
            quiet=config.quiet,
            config=config,
        )
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
