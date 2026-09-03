import os
import tempfile
import pandas as pd
import matplotlib.pyplot as plt
from sec_scraper.chart import RevenueChart


def create_sample_df():
    return pd.DataFrame([
        {"quarter": "Q1 2024", "revenue_billions": 10.0, "yoy_growth_pct": None, "qoq_growth_pct": None},
        {"quarter": "Q2 2024", "revenue_billions": 12.0, "yoy_growth_pct": None, "qoq_growth_pct": 20.0},
        {"quarter": "Q3 2024", "revenue_billions": 14.0, "yoy_growth_pct": None, "qoq_growth_pct": 16.7},
        {"quarter": "Q4 2024", "revenue_billions": 16.0, "yoy_growth_pct": None, "qoq_growth_pct": 14.3},
        {"quarter": "Q1 2025", "revenue_billions": 15.0, "yoy_growth_pct": 50.0, "qoq_growth_pct": -6.25},
        {"quarter": "Q2 2025", "revenue_billions": 18.0, "yoy_growth_pct": 50.0, "qoq_growth_pct": 20.0},
        {"quarter": "Q3 2025", "revenue_billions": 21.0, "yoy_growth_pct": 50.0, "qoq_growth_pct": 16.7},
        {"quarter": "Q4 2025", "revenue_billions": 24.0, "yoy_growth_pct": 50.0, "qoq_growth_pct": 14.3},
    ])


def test_create_figure_generates_in_memory_plot():
    df = create_sample_df()
    chart = RevenueChart()
    fig = chart.create_figure(df, company_name="Tesla, Inc.", ticker_symbol="TSLA")

    try:
        assert isinstance(fig, plt.Figure)
        axes = fig.get_axes()
        assert len(axes) >= 1
        ax = axes[0]
        # Check that 8 ticks exist for the 8 quarters
        assert len(ax.get_xticks()) == 8
        # Verify suptitle
        assert "Tesla, Inc. (TSLA)" in fig._suptitle.get_text()
    finally:
        plt.close(fig)


def test_save_figure_writes_to_disk():
    df = create_sample_df()
    chart = RevenueChart()

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "subdir", "test_chart.png")
        saved_path = chart.save(df, company_name="Tesla, Inc.", ticker_symbol="TSLA", output_path=out_path)

        assert os.path.exists(saved_path)
        assert os.path.getsize(saved_path) > 1000  # Non-trivial image file
