"""
Configuration management for sec-scraper.
Supports CLI arguments, environment variables, JSON config files, and dynamic path defaults.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from sec_scraper.client import DEFAULT_USER_AGENT


@dataclass
class ScraperConfig:
    """Configuration settings for the SEC scraper pipeline."""

    ticker: str = "TSLA"
    quarters: int = 8
    user_agent: str = DEFAULT_USER_AGENT
    output_csv: str | None = None
    output_chart: str | None = None
    data_dir: str = "data"
    charts_dir: str = "charts"
    concept: str | None = None
    candidate_concepts: list[str] | None = None
    no_chart: bool = False
    quiet: bool = False

    def resolve_output_csv(self) -> str:
        """Resolve the CSV output file path."""
        if self.output_csv:
            return self.output_csv
        clean_ticker = self.ticker.strip().lower()
        if clean_ticker == "tsla" and self.quarters == 8:
            filename = "tesla_revenue_last_8_quarters.csv"
        else:
            filename = f"{clean_ticker}_revenue_last_{self.quarters}_quarters.csv"
        return os.path.join(self.data_dir, filename)

    def resolve_output_chart(self) -> str | None:
        """Resolve the chart output file path, or None if no_chart is True."""
        if self.no_chart:
            return None
        if self.output_chart:
            return self.output_chart
        clean_ticker = self.ticker.strip().lower()
        if clean_ticker == "tsla" and self.quarters == 8:
            filename = "tesla_revenue_last_8_quarters.png"
        else:
            filename = f"{clean_ticker}_revenue_last_{self.quarters}_quarters.png"
        return os.path.join(self.charts_dir, filename)

    @classmethod
    def from_env(cls) -> dict[str, Any]:
        """Read configuration options from environment variables."""
        env_map: dict[str, Any] = {}
        if "SEC_TICKER" in os.environ:
            env_map["ticker"] = os.environ["SEC_TICKER"]
        if "SEC_QUARTERS" in os.environ:
            try:
                env_map["quarters"] = int(os.environ["SEC_QUARTERS"])
            except ValueError:
                pass
        if "SEC_USER_AGENT" in os.environ:
            env_map["user_agent"] = os.environ["SEC_USER_AGENT"]
        if "SEC_OUTPUT_CSV" in os.environ:
            env_map["output_csv"] = os.environ["SEC_OUTPUT_CSV"]
        if "SEC_OUTPUT_CHART" in os.environ:
            env_map["output_chart"] = os.environ["SEC_OUTPUT_CHART"]
        if "SEC_DATA_DIR" in os.environ:
            env_map["data_dir"] = os.environ["SEC_DATA_DIR"]
        if "SEC_CHARTS_DIR" in os.environ:
            env_map["charts_dir"] = os.environ["SEC_CHARTS_DIR"]
        if "SEC_CONCEPT" in os.environ:
            env_map["concept"] = os.environ["SEC_CONCEPT"]
        if "SEC_NO_CHART" in os.environ:
            env_map["no_chart"] = os.environ["SEC_NO_CHART"].lower() in ("1", "true", "yes")
        if "SEC_QUIET" in os.environ:
            env_map["quiet"] = os.environ["SEC_QUIET"].lower() in ("1", "true", "yes")
        return env_map

    @classmethod
    def from_file(cls, path: str | Path) -> dict[str, Any]:
        """Load configuration options from a JSON file."""
        config_path = Path(path)
        if not config_path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object in {path}, got {type(data).__name__}")
        return data

    @classmethod
    def build_parser(cls) -> argparse.ArgumentParser:
        """Construct CLI argument parser with comprehensive configuration flags."""
        parser = argparse.ArgumentParser(
            description="Scrape quarterly revenue from official SEC EDGAR XBRL filings and generate financial charts."
        )
        parser.add_argument(
            "-t", "--ticker",
            type=str,
            default=None,
            help="Company ticker symbol (e.g. AAPL, TSLA, MSFT) or 10-digit CIK (default: TSLA)",
        )
        parser.add_argument(
            "-n", "--quarters", "--count",
            dest="quarters",
            type=int,
            default=None,
            help="Number of quarters to extract and visualize (default: 8)",
        )
        parser.add_argument(
            "--output-csv",
            type=str,
            default=None,
            help="Custom output path for extracted CSV dataset",
        )
        parser.add_argument(
            "--output-chart",
            type=str,
            default=None,
            help="Custom output path for generated chart PNG",
        )
        parser.add_argument(
            "--data-dir",
            type=str,
            default=None,
            help="Directory for default CSV exports (default: data)",
        )
        parser.add_argument(
            "--charts-dir",
            type=str,
            default=None,
            help="Directory for default chart exports (default: charts)",
        )
        parser.add_argument(
            "--user-agent",
            type=str,
            default=None,
            help="SEC-compliant User-Agent header (Fair Access Policy requirement)",
        )
        parser.add_argument(
            "--concept",
            type=str,
            default=None,
            help="Override US-GAAP revenue concept (e.g. Revenues, RevenueFromContractWithCustomerExcludingAssessedTax)",
        )
        parser.add_argument(
            "-c", "--config",
            type=str,
            default=None,
            help="Path to JSON configuration file",
        )
        parser.add_argument(
            "--no-chart",
            action="store_true",
            default=None,
            help="Extract CSV data only and skip rendering chart",
        )
        parser.add_argument(
            "-q", "--quiet",
            action="store_true",
            default=None,
            help="Suppress standard output messages and summary table",
        )
        return parser

    @classmethod
    def from_cli_args(cls, args: Sequence[str] | None = None) -> ScraperConfig:
        """
        Parse CLI arguments and combine with config file, environment, and defaults.
        Precedence order:
            1. Explicit CLI arguments
            2. Config file values (if --config provided)
            3. Environment variables (SEC_*)
            4. Default dataclass values
        """
        parser = cls.build_parser()
        parsed = parser.parse_args(args)

        # 1. Start with defaults
        config_dict: dict[str, Any] = {
            "ticker": "TSLA",
            "quarters": 8,
            "user_agent": DEFAULT_USER_AGENT,
            "data_dir": "data",
            "charts_dir": "charts",
            "no_chart": False,
            "quiet": False,
        }

        # 2. Merge environment variables
        config_dict.update(cls.from_env())

        # 3. Merge config file if provided or if sec_scraper_config.json exists in CWD
        config_file = parsed.config
        if not config_file and os.path.isfile("sec_scraper_config.json"):
            config_file = "sec_scraper_config.json"

        if config_file:
            file_data = cls.from_file(config_file)
            config_dict.update(file_data)

        # 4. Merge explicit CLI flags (only where not None)
        cli_dict = vars(parsed)
        for key, val in cli_dict.items():
            if key in ("config",):
                continue
            if val is not None:
                config_dict[key] = val

        return cls(**{k: v for k, v in config_dict.items() if hasattr(cls, k)})

