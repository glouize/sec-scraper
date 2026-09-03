import os
import tempfile
import pandas as pd
from sec_scraper.cli import run_pipeline, main
from sec_scraper.client import EdgarClient, FixtureTransportAdapter
from tests.test_normalizer import build_synthetic_sec_facts


def test_run_pipeline_end_to_end():
    mock_facts = build_synthetic_sec_facts()
    adapter = FixtureTransportAdapter(fixtures={
        "https://data.sec.gov/api/xbrl/companyfacts/CIK0001318605.json": mock_facts
    })
    client = EdgarClient(transport=adapter)

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "test.csv")
        chart_path = os.path.join(tmpdir, "test.png")

        df, out_csv, out_chart = run_pipeline(
            ticker="TSLA",
            output_csv=csv_path,
            output_chart=chart_path,
            client=client,
            quiet=True,
        )

        assert len(df) == 8
        assert os.path.exists(out_csv)
        assert os.path.exists(out_chart)
        # Verify CSV content
        read_df = pd.read_csv(out_csv)
        assert len(read_df) == 8
        assert "revenue_billions" in read_df.columns


def test_main_cli_returns_zero_on_success(monkeypatch):
    mock_facts = build_synthetic_sec_facts()
    adapter = FixtureTransportAdapter(fixtures={
        "https://data.sec.gov/api/xbrl/companyfacts/CIK0001318605.json": mock_facts
    })
    
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "cli_test.csv")
        chart_path = os.path.join(tmpdir, "cli_test.png")

        # Mock EdgarClient inside run_pipeline or pass args
        from sec_scraper import cli
        original_run = cli.run_pipeline
        monkeypatch.setattr(
            cli,
            "run_pipeline",
            lambda **kwargs: original_run(**{**kwargs, "client": EdgarClient(transport=adapter), "quiet": True})
        )

        exit_code = main(["--ticker", "TSLA", "--output-csv", csv_path, "--output-chart", chart_path])
        assert exit_code == 0
        assert os.path.exists(csv_path)
