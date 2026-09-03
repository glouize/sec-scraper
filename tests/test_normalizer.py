import pytest
import pandas as pd
from sec_scraper.normalizer import RevenueNormalizer


def build_synthetic_sec_facts():
    """Construct a minimal valid SEC XBRL facts structure with 8 quarters across 2 fiscal years."""
    usd_entries = [
        # FY 2024
        # Q1 2024: 2024-01-01 to 2024-03-31 (90 days) - $10B
        {"form": "10-Q", "frame": "CY2024Q1", "fy": 2024, "fp": "Q1", "start": "2024-01-01", "end": "2024-03-31", "val": 10_000_000_000, "filed": "2024-04-15", "accn": "0001-24-01"},
        # Q2 2024: 2024-04-01 to 2024-06-30 (90 days) - $12B
        {"form": "10-Q", "frame": "CY2024Q2", "fy": 2024, "fp": "Q2", "start": "2024-04-01", "end": "2024-06-30", "val": 12_000_000_000, "filed": "2024-07-15", "accn": "0001-24-02"},
        # Q3 2024 discrete: 2024-07-01 to 2024-09-30 (91 days) - $14B
        {"form": "10-Q", "frame": "CY2024Q3", "fy": 2024, "fp": "Q3", "start": "2024-07-01", "end": "2024-09-30", "val": 14_000_000_000, "filed": "2024-10-15", "accn": "0001-24-03"},
        # Q3 2024 9M cumulative: 2024-01-01 to 2024-09-30 (273 days) - $36B (10 + 12 + 14)
        {"form": "10-Q", "fy": 2024, "fp": "Q3", "start": "2024-01-01", "end": "2024-09-30", "val": 36_000_000_000, "filed": "2024-10-15", "accn": "0001-24-03"},
        # FY 2024 Full Year: 2024-01-01 to 2024-12-31 (365 days) - $52B -> Derived Q4 should be $16B (52B - 36B)
        {"form": "10-K", "fy": 2024, "fp": "FY", "start": "2024-01-01", "end": "2024-12-31", "val": 52_000_000_000, "filed": "2025-01-30", "accn": "0001-25-01"},

        # FY 2025
        # Q1 2025: 2025-01-01 to 2025-03-31 (89 days) - $15B (Initial filing)
        {"form": "10-Q", "frame": "CY2025Q1", "fy": 2025, "fp": "Q1", "start": "2025-01-01", "end": "2025-03-31", "val": 14_500_000_000, "filed": "2025-04-10", "accn": "0001-25-02"},
        # Q1 2025 Restated/Amended: filed later with $15B
        {"form": "10-Q", "frame": "CY2025Q1", "fy": 2025, "fp": "Q1", "start": "2025-01-01", "end": "2025-03-31", "val": 15_000_000_000, "filed": "2025-04-25", "accn": "0001-25-03"},
        # Q2 2025: 2025-04-01 to 2025-06-30 (90 days) - $18B
        {"form": "10-Q", "frame": "CY2025Q2", "fy": 2025, "fp": "Q2", "start": "2025-04-01", "end": "2025-06-30", "val": 18_000_000_000, "filed": "2025-07-15", "accn": "0001-25-04"},
        # Q3 2025 discrete: 2025-07-01 to 2025-09-30 (91 days) - $21B
        {"form": "10-Q", "frame": "CY2025Q3", "fy": 2025, "fp": "Q3", "start": "2025-07-01", "end": "2025-09-30", "val": 21_000_000_000, "filed": "2025-10-15", "accn": "0001-25-05"},
        # Q3 2025 9M cumulative: 2025-01-01 to 2025-09-30 (272 days) - $54B (15 + 18 + 21)
        {"form": "10-Q", "fy": 2025, "fp": "Q3", "start": "2025-01-01", "end": "2025-09-30", "val": 54_000_000_000, "filed": "2025-10-15", "accn": "0001-25-05"},
        # FY 2025 Full Year: 2025-01-01 to 2025-12-31 (364 days) - $78B -> Derived Q4 should be $24B (78B - 54B)
        {"form": "10-K", "fy": 2025, "fp": "FY", "start": "2025-01-01", "end": "2025-12-31", "val": 78_000_000_000, "filed": "2026-01-30", "accn": "0001-26-01"},
    ]

    return {
        "entityName": "Acme Corp",
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": usd_entries
                    }
                }
            }
        }
    }


def test_normalizer_extracts_8_quarters_and_derives_q4():
    facts = build_synthetic_sec_facts()
    normalizer = RevenueNormalizer()
    df = normalizer.normalize(facts, count=8)

    assert len(df) == 8
    assert list(df["quarter"]) == [
        "Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024",
        "Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025"
    ]

    # Verify deduplication selected the newer filing for Q1 2025 ($15B instead of $14.5B)
    q1_2025_row = df[df["quarter"] == "Q1 2025"].iloc[0]
    assert q1_2025_row["revenue_billions"] == 15.0
    assert q1_2025_row["filed_date"] == "2025-04-25"

    # Verify Q4 2024 was derived (52B - 36B = 16B)
    q4_2024_row = df[df["quarter"] == "Q4 2024"].iloc[0]
    assert q4_2024_row["revenue_billions"] == 16.0
    assert bool(q4_2024_row["is_derived_q4"]) is True
    assert q4_2024_row["form"] == "10-K"

    # Verify Q4 2025 was derived (78B - 54B = 24B)
    q4_2025_row = df[df["quarter"] == "Q4 2025"].iloc[0]
    assert q4_2025_row["revenue_billions"] == 24.0
    assert bool(q4_2025_row["is_derived_q4"]) is True

    # Verify YoY growth for Q1 2025 vs Q1 2024: (15.0 - 10.0) / 10.0 * 100 = 50.0%
    assert pytest.approx(q1_2025_row["yoy_growth_pct"], rel=1e-3) == 50.0

    # Verify QoQ growth for Q2 2024 vs Q1 2024: (12.0 - 10.0) / 10.0 * 100 = 20.0%
    q2_2024_row = df[df["quarter"] == "Q2 2024"].iloc[0]
    assert pytest.approx(q2_2024_row["qoq_growth_pct"], rel=1e-3) == 20.0


def test_normalizer_falls_back_to_alternative_concepts():
    facts = {
        "entityName": "Contract Corp",
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {
                        "USD": build_synthetic_sec_facts()["facts"]["us-gaap"]["Revenues"]["units"]["USD"]
                    }
                }
            }
        }
    }
    normalizer = RevenueNormalizer()
    df = normalizer.normalize(facts)
    assert len(df) == 8


def test_normalizer_raises_error_if_no_concept():
    facts = {"entityName": "Empty Corp", "facts": {"us-gaap": {}}}
    normalizer = RevenueNormalizer()
    with pytest.raises(ValueError, match="No suitable revenue concept found"):
        normalizer.normalize(facts)


def test_normalizer_raises_error_if_insufficient_quarters():
    facts = build_synthetic_sec_facts()
    # Trim to 4 quarters
    facts["facts"]["us-gaap"]["Revenues"]["units"]["USD"] = facts["facts"]["us-gaap"]["Revenues"]["units"]["USD"][:4]
    normalizer = RevenueNormalizer()
    with pytest.raises(RuntimeError, match="Found only"):
        normalizer.normalize(facts, count=8)


def test_concept_selection_prefers_latest_period():
    """Verify that when multiple concepts are present, the concept with the latest end date is selected (e.g. AAPL post-2018)."""
    facts = {
        "entityName": "MultiConcept Corp",
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {"end": "2018-09-30", "val": 100_000_000, "form": "10-Q"}
                        ]
                    }
                },
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {
                        "USD": [
                            {"end": "2026-06-30", "val": 200_000_000, "form": "10-Q"}
                        ]
                    }
                }
            }
        }
    }
    normalizer = RevenueNormalizer()
    concept = normalizer.identify_revenue_concept(facts["facts"]["us-gaap"])
    assert concept == "RevenueFromContractWithCustomerExcludingAssessedTax"


def test_concept_explicit_override():
    facts = {
        "entityName": "Override Corp",
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [{"end": "2026-06-30", "val": 100_000_000, "form": "10-Q"}]
                    }
                },
                "SalesRevenueNet": {
                    "units": {
                        "USD": [{"end": "2026-06-30", "val": 90_000_000, "form": "10-Q"}]
                    }
                }
            }
        }
    }
    normalizer = RevenueNormalizer(concept="SalesRevenueNet")
    concept = normalizer.identify_revenue_concept(facts["facts"]["us-gaap"])
    assert concept == "SalesRevenueNet"

