"""
In-process module for normalizing SEC US-GAAP quarterly revenue figures.
"""

from __future__ import annotations

import datetime
from typing import Any
import pandas as pd


class RevenueNormalizer:
    """
    Encapsulates US-GAAP concept identification, period alignment,
    Form 10-K Q4 derivation, and growth time-series calculations.
    """

    DEFAULT_CANDIDATE_CONCEPTS = [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
    ]

    def __init__(
        self,
        candidate_concepts: list[str] | None = None,
        concept: str | None = None,
    ):
        self.candidate_concepts = candidate_concepts or list(self.DEFAULT_CANDIDATE_CONCEPTS)
        self.concept = concept

    def identify_revenue_concept(
        self,
        us_gaap_facts: dict[str, Any],
        concept: str | None = None,
    ) -> str | None:
        """
        Find the primary US-GAAP revenue concept with USD units.
        If an explicit concept is provided or configured, validates and returns it.
        Otherwise, selects the candidate concept with the most recent filing period end date,
        breaking ties by order of preference in candidate_concepts.
        """
        target = concept or self.concept
        if target:
            if target in us_gaap_facts:
                concept_data = us_gaap_facts[target]
                if "units" in concept_data and "USD" in concept_data["units"]:
                    return target
            return None

        best_concept = None
        best_latest_end = ""

        for c in self.candidate_concepts:
            if c in us_gaap_facts:
                concept_data = us_gaap_facts[c]
                if "units" in concept_data and "USD" in concept_data["units"]:
                    entries = concept_data["units"]["USD"]
                    latest_end = max((e.get("end", "") for e in entries), default="")
                    if best_concept is None or latest_end > best_latest_end:
                        best_concept = c
                        best_latest_end = latest_end

        return best_concept

    def normalize(
        self,
        facts: dict[str, Any],
        count: int = 8,
        concept: str | None = None,
    ) -> pd.DataFrame:
        """
        Extract and normalize quarterly revenue from raw SEC XBRL facts.

        Handles standalone Form 10-Q 3-month periods and derives Form 10-K
        fourth-quarter figures where:
            Revenue_Q4 = Revenue_FY - Revenue_9M
        """
        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        entity_name = facts.get("entityName", "Company")

        revenue_concept = self.identify_revenue_concept(us_gaap, concept=concept)
        if not revenue_concept:
            target_str = f"concept '{concept or self.concept}'" if (concept or self.concept) else "suitable revenue concept"
            raise ValueError(f"No {target_str} found in US-GAAP facts for {entity_name}")

        usd_units = us_gaap[revenue_concept]["units"]["USD"]

        discrete_quarters: list[dict[str, Any]] = []
        nine_month_periods: dict[datetime.date, dict[str, Any]] = {}
        full_year_periods: dict[datetime.date, dict[str, Any]] = {}

        for entry in usd_units:
            form = entry.get("form")
            if form not in ("10-Q", "10-K", "10-Q/A", "10-K/A"):
                continue

            start_str = entry.get("start")
            end_str = entry.get("end")
            if not start_str or not end_str:
                continue

            start = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
            end = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
            days = (end - start).days
            fy = entry.get("fy")
            fp = entry.get("fp")

            # 3-month discrete quarter (~70 to 110 days)
            if 70 <= days <= 110:
                discrete_quarters.append({
                    "start": start,
                    "end": end,
                    "fy": fy,
                    "fp": fp,
                    "form": form,
                    "val": entry["val"],
                    "accn": entry.get("accn", ""),
                    "filed": entry.get("filed", ""),
                    "derived": False,
                    "days": days,
                })

            # 9-month cumulative period (~250 to 290 days) reported in Q3 10-Q
            elif 250 <= days <= 290 and fp in ("Q3", "Q3/A"):
                if end not in nine_month_periods or entry.get("filed", "") > nine_month_periods[end].get("filed", ""):
                    nine_month_periods[end] = entry

            # Full Year period (~350 to 380 days) reported in 10-K
            elif 350 <= days <= 380 and (fp in ("FY", "FY/A") or "10-K" in str(form)):
                if end not in full_year_periods or entry.get("filed", "") > full_year_periods[end].get("filed", ""):
                    full_year_periods[end] = entry

        # Deduplicate discrete quarters by period end date, preferring the latest filing
        quarters_by_end: dict[datetime.date, dict[str, Any]] = {}
        for q in discrete_quarters:
            end = q["end"]
            if end not in quarters_by_end or q["filed"] > quarters_by_end[end]["filed"]:
                quarters_by_end[end] = q

        # Derive Q4 for fiscal years with a 10-K and a corresponding 9-month Q3 filing
        for fy_end, fy_entry in full_year_periods.items():
            if fy_end in quarters_by_end:
                continue

            for nm_end, nm_entry in nine_month_periods.items():
                days_diff = (fy_end - nm_end).days
                if 80 <= days_diff <= 100:
                    q4_val = fy_entry["val"] - nm_entry["val"]
                    q4_start = nm_end + datetime.timedelta(days=1)
                    q4_days = (fy_end - q4_start).days
                    quarters_by_end[fy_end] = {
                        "start": q4_start,
                        "end": fy_end,
                        "fy": fy_entry.get("fy"),
                        "fp": "Q4",
                        "form": fy_entry.get("form", "10-K"),
                        "val": q4_val,
                        "accn": fy_entry.get("accn", ""),
                        "filed": fy_entry.get("filed", ""),
                        "derived": True,
                        "days": q4_days,
                    }
                    break

        sorted_quarters = sorted(quarters_by_end.values(), key=lambda x: x["end"])

        if len(sorted_quarters) < count:
            raise RuntimeError(f"Found only {len(sorted_quarters)} quarters, expected at least {count}.")

        records = []
        for q in sorted_quarters:
            month = q["end"].month
            year = q["end"].year
            if month in (3, 4):
                quarter_name = f"Q1 {year}"
            elif month in (6, 7):
                quarter_name = f"Q2 {year}"
            elif month in (9, 10):
                quarter_name = f"Q3 {year}"
            else:
                quarter_name = f"Q4 {year}"

            rev_b = q["val"] / 1e9
            records.append({
                "quarter": quarter_name,
                "period_end": q["end"].strftime("%Y-%m-%d"),
                "period_start": q["start"].strftime("%Y-%m-%d"),
                "revenue_usd": q["val"],
                "revenue_billions": round(rev_b, 3),
                "form": q["form"],
                "sec_accn": q["accn"],
                "filed_date": q["filed"],
                "is_derived_q4": q["derived"],
            })

        df = pd.DataFrame(records)
        # Calculate growth metrics across full historical series before slicing
        df["qoq_growth_pct"] = df["revenue_billions"].pct_change() * 100
        df["yoy_growth_pct"] = df["revenue_billions"].pct_change(4) * 100

        # Return the last `count` quarters
        return df.tail(count).reset_index(drop=True)

