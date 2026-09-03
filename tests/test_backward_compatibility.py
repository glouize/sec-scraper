import os
import tempfile
import pandas as pd
import sec_revenue_scraper
from tests.test_normalizer import build_synthetic_sec_facts


def test_backward_compatibility_symbols():
    assert hasattr(sec_revenue_scraper, "DEFAULT_USER_AGENT")
    assert hasattr(sec_revenue_scraper, "TICKER_TO_CIK")
    assert hasattr(sec_revenue_scraper, "resolve_cik")
    assert hasattr(sec_revenue_scraper, "fetch_sec_company_facts")
    assert hasattr(sec_revenue_scraper, "parse_quarterly_revenue")
    assert hasattr(sec_revenue_scraper, "generate_revenue_chart")
    assert hasattr(sec_revenue_scraper, "main")


def test_parse_quarterly_revenue_legacy_call():
    facts = build_synthetic_sec_facts()
    df = sec_revenue_scraper.parse_quarterly_revenue(facts)
    assert len(df) == 8
    assert "revenue_billions" in df.columns
    assert "quarter" in df.columns
    assert df.iloc[0]["quarter"] == "Q1 2024"


def test_generate_revenue_chart_legacy_call(sample_revenue_df: pd.DataFrame):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "legacy_chart.png")
        sec_revenue_scraper.generate_revenue_chart(sample_revenue_df, "Tesla, Inc.", "TSLA", out_path)
        assert os.path.exists(out_path)

