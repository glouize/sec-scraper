import pytest
import pandas as pd


@pytest.fixture
def sample_revenue_df() -> pd.DataFrame:
    """Fixture providing a standard 8-quarter normalized revenue DataFrame."""
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
