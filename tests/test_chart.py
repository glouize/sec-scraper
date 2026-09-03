import os
import tempfile
import pandas as pd
import matplotlib.pyplot as plt
from sec_scraper.chart import RevenueChart


def test_create_figure_generates_in_memory_plot(sample_revenue_df: pd.DataFrame):
    chart = RevenueChart()
    fig = chart.create_figure(sample_revenue_df, company_name="Tesla, Inc.", ticker_symbol="TSLA")

    try:
        assert isinstance(fig, plt.Figure)
        axes = fig.get_axes()
        assert len(axes) >= 1
        ax = axes[0]
        # Check that 8 ticks exist for the 8 quarters
        assert len(ax.get_xticks()) == 8
        # Verify title via public texts list
        titles = [t.get_text() for t in fig.texts]
        assert any("Tesla, Inc. (TSLA)" in t for t in titles)
    finally:
        plt.close(fig)


def test_save_figure_writes_to_disk(sample_revenue_df: pd.DataFrame):
    chart = RevenueChart()

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "subdir", "test_chart.png")
        saved_path = chart.save(sample_revenue_df, company_name="Tesla, Inc.", ticker_symbol="TSLA", output_path=out_path)

        assert os.path.exists(saved_path)
        assert os.path.getsize(saved_path) > 1000  # Non-trivial image file
