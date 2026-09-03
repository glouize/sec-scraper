"""
Tests for ScraperConfig configuration management.
"""

import json
import os
import tempfile
import pytest

from sec_scraper.config import ScraperConfig


def test_default_config_resolution():
    cfg = ScraperConfig()
    assert cfg.ticker == "TSLA"
    assert cfg.quarters == 8
    assert cfg.resolve_output_csv() == os.path.join("data", "tesla_revenue_last_8_quarters.csv")
    assert cfg.resolve_output_chart() == os.path.join("charts", "tesla_revenue_last_8_quarters.png")


def test_dynamic_path_resolution_for_different_tickers_and_quarters():
    cfg_aapl = ScraperConfig(ticker="AAPL", quarters=8)
    assert cfg_aapl.resolve_output_csv() == os.path.join("data", "aapl_revenue_last_8_quarters.csv")
    assert cfg_aapl.resolve_output_chart() == os.path.join("charts", "aapl_revenue_last_8_quarters.png")

    cfg_custom_n = ScraperConfig(ticker="MSFT", quarters=12)
    assert cfg_custom_n.resolve_output_csv() == os.path.join("data", "msft_revenue_last_12_quarters.csv")
    assert cfg_custom_n.resolve_output_chart() == os.path.join("charts", "msft_revenue_last_12_quarters.png")


def test_no_chart_option():
    cfg = ScraperConfig(ticker="AAPL", no_chart=True)
    assert cfg.resolve_output_chart() is None


def test_custom_paths_override():
    cfg = ScraperConfig(output_csv="custom/dir/data.csv", output_chart="custom/dir/chart.png")
    assert cfg.resolve_output_csv() == "custom/dir/data.csv"
    assert cfg.resolve_output_chart() == "custom/dir/chart.png"


def test_from_env(monkeypatch):
    monkeypatch.setenv("SEC_TICKER", "NVDA")
    monkeypatch.setenv("SEC_QUARTERS", "6")
    monkeypatch.setenv("SEC_USER_AGENT", "CustomAgent/2.0")
    monkeypatch.setenv("SEC_NO_CHART", "true")

    cfg = ScraperConfig.from_cli_args([])
    assert cfg.ticker == "NVDA"
    assert cfg.quarters == 6
    assert cfg.user_agent == "CustomAgent/2.0"
    assert cfg.no_chart is True


def test_from_json_config_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "test_config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({
                "ticker": "AMZN",
                "quarters": 4,
                "data_dir": "custom_data",
                "charts_dir": "custom_charts",
            }, f)

        cfg = ScraperConfig.from_cli_args(["--config", config_path])
        assert cfg.ticker == "AMZN"
        assert cfg.quarters == 4
        assert cfg.resolve_output_csv() == os.path.join("custom_data", "amzn_revenue_last_4_quarters.csv")
        assert cfg.resolve_output_chart() == os.path.join("custom_charts", "amzn_revenue_last_4_quarters.png")


def test_cli_flags_override_file_and_env(monkeypatch):
    monkeypatch.setenv("SEC_TICKER", "NVDA")
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "cfg.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"ticker": "GOOGL", "quarters": 10}, f)

        # CLI flag --ticker AAPL should override both config file GOOGL and env NVDA
        cfg = ScraperConfig.from_cli_args(["-c", config_path, "-t", "AAPL", "-n", "12"])
        assert cfg.ticker == "AAPL"
        assert cfg.quarters == 12

