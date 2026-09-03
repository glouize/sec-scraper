"""
SEC EDGAR Revenue Scraper & Financial Chart Generator
======================================================
Pulls quarterly revenue figures directly from official SEC EDGAR XBRL filings
programmatically, normalizes Form 10-Q standalone periods and Form 10-K Q4 derived figures,
and generates a publication-ready financial chart.
"""

import argparse
import datetime
import json
import os
import urllib.request
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Default user-agent complying with SEC Fair Access guidelines
DEFAULT_USER_AGENT = "FinancialResearch/1.0 (academic_research@example.com)"

# Known CIK mappings for major US-listed companies
TICKER_TO_CIK = {
    "TSLA": "0001318605",
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "NVDA": "0001045810",
    "GOOGL": "0001652044",
    "AMZN": "0001018724",
    "META": "0001326801",
}


def resolve_cik(ticker_or_cik: str, user_agent: str = DEFAULT_USER_AGENT) -> tuple[str, str]:
    """Resolve a ticker symbol to a 10-digit zero-padded CIK and company name."""
    clean_symbol = ticker_or_cik.strip().upper()
    if clean_symbol in TICKER_TO_CIK:
        return TICKER_TO_CIK[clean_symbol], clean_symbol

    if clean_symbol.isdigit():
        return clean_symbol.zfill(10), clean_symbol

    # Query SEC company_tickers.json
    url = "https://www.sec.gov/files/company_tickers.json"
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for entry in data.values():
                if entry.get("ticker") == clean_symbol:
                    cik = str(entry["cik_str"]).zfill(10)
                    return cik, entry.get("title", clean_symbol)
    except Exception as exc:
        print(f"[Warning] Failed to query SEC company ticker directory: {exc}")

    raise ValueError(f"Could not resolve CIK for symbol: {ticker_or_cik}")


def fetch_sec_company_facts(cik: str, user_agent: str = DEFAULT_USER_AGENT) -> dict:
    """Fetch structured XBRL company facts directly from SEC EDGAR API."""
    padded_cik = cik.zfill(10)
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{padded_cik}.json"
    headers = {"User-Agent": user_agent, "Accept": "application/json"}

    print(f"[1/4] Scraping SEC EDGAR facts from: {url} ...")
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_quarterly_revenue(facts: dict) -> pd.DataFrame:
    """
    Extract quarterly revenue from SEC facts.
    Accurately handles Form 10-Q standalone 3-month filings and derives
    Form 10-K 4th quarter figures where Q4 = FY - 9M.
    """
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    entity_name = facts.get("entityName", "Company")

    # Priority order for revenue concepts under US-GAAP
    candidate_concepts = [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
    ]

    revenue_concept = None
    for concept in candidate_concepts:
        if concept in us_gaap and "units" in us_gaap[concept] and "USD" in us_gaap[concept]["units"]:
            revenue_concept = concept
            break

    if not revenue_concept:
        raise ValueError(f"No suitable revenue concept found in US-GAAP facts for {entity_name}")

    print(f"[2/4] Identified US-GAAP accounting concept: '{revenue_concept}'")
    usd_units = us_gaap[revenue_concept]["units"]["USD"]

    # Separate into discrete 3-month (quarterly) and cumulative periods
    discrete_quarters = []
    nine_month_periods = {}  # key: end_date -> entry
    full_year_periods = {}   # key: end_date -> entry

    for entry in usd_units:
        form = entry.get("form")
        if form not in ("10-Q", "10-K"):
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
        elif 250 <= days <= 290 and fp == "Q3":
            if end not in nine_month_periods or entry.get("filed", "") > nine_month_periods[end].get("filed", ""):
                nine_month_periods[end] = entry

        # Full Year period (~350 to 380 days) reported in 10-K
        elif 350 <= days <= 380 and (fp == "FY" or form == "10-K"):
            if end not in full_year_periods or entry.get("filed", "") > full_year_periods[end].get("filed", ""):
                full_year_periods[end] = entry

    # Deduplicate discrete quarters by period end date, preferring the latest filing
    quarters_by_end = {}
    for q in discrete_quarters:
        end = q["end"]
        if end not in quarters_by_end or q["filed"] > quarters_by_end[end]["filed"]:
            quarters_by_end[end] = q

    # Derive Q4 for fiscal years that have a 10-K and a corresponding 9-month Q3 filing
    for fy_end, fy_entry in full_year_periods.items():
        if fy_end in quarters_by_end:
            continue

        # Look for corresponding 9M period ending ~90 days before fy_end
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
                    "form": "10-K",
                    "val": q4_val,
                    "accn": fy_entry.get("accn", ""),
                    "filed": fy_entry.get("filed", ""),
                    "derived": True,
                    "days": q4_days,
                }
                break

    # Sort all resolved quarters chronologically
    sorted_quarters = sorted(quarters_by_end.values(), key=lambda x: x["end"])

    if len(sorted_quarters) < 8:
        raise RuntimeError(f"Found only {len(sorted_quarters)} quarters, expected at least 8.")

    # Select the last 8 quarters
    last_8 = sorted_quarters[-8:]

    records = []
    for q in last_8:
        # Determine quarter label by end month
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
    # Calculate Quarter-over-Quarter (QoQ) and Year-over-Year (YoY) growth
    df["qoq_growth_pct"] = df["revenue_billions"].pct_change() * 100
    df["yoy_growth_pct"] = df["revenue_billions"].pct_change(4) * 100

    return df


def generate_revenue_chart(df: pd.DataFrame, company_name: str, ticker_symbol: str, output_path: str):
    """Generate a clean, high-resolution financial chart."""
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    fig, ax = plt.subplots(figsize=(12, 7), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#F9FAFC")

    quarters = df["quarter"].tolist()
    revenues = df["revenue_billions"].tolist()
    x = range(len(quarters))

    # Corporate color styling (Tesla Red & deep charcoal accents)
    bar_color = "#E82127" if ticker_symbol.upper() == "TSLA" else "#1F77B4"
    accent_color = "#111111"

    bars = ax.bar(
        x,
        revenues,
        width=0.55,
        color=bar_color,
        edgecolor=accent_color,
        linewidth=0.8,
        zorder=3,
        alpha=0.92,
        label="Quarterly Revenue ($B)"
    )

    # Secondary trendline
    ax.plot(
        x,
        revenues,
        color="#222222",
        linestyle="--",
        linewidth=1.8,
        marker="o",
        markersize=6,
        markerfacecolor="#FFFFFF",
        markeredgecolor=accent_color,
        markeredgewidth=1.8,
        zorder=4,
        label="Quarterly Trajectory"
    )

    # Data value labels atop bars
    max_rev = max(revenues)
    for i, (bar, rev) in enumerate(zip(bars, revenues)):
        height = bar.get_height()
        yoy = df.loc[i, "yoy_growth_pct"]
        yoy_str = f"({'+' if yoy > 0 else ''}{yoy:.1f}% YoY)" if pd.notnull(yoy) else ""
        label_text = f"${rev:.2f}B\n{yoy_str}".strip()

        ax.annotate(
            label_text,
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 9),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color="#1E293B",
            zorder=6,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#FFFFFF", alpha=0.85, edgecolor="#E2E8F0", linewidth=0.5)
        )

    # Configure axes and limits
    ax.set_xticks(list(x))
    ax.set_xticklabels(quarters, fontsize=11, fontweight="bold", color="#334155")
    ax.set_ylabel("Revenue in Billions (USD)", fontsize=12, fontweight="bold", color="#1E293B", labelpad=10)
    ax.set_ylim(0, max_rev * 1.25)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("$%.1fB"))

    # Gridlines and spines
    ax.grid(axis="y", linestyle=":", alpha=0.6, color="#CBD5E1")
    ax.grid(axis="x", visible=False)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    for spine in ["left", "bottom"]:
        ax.spines[spine].set_color("#94A3B8")
        ax.spines[spine].set_linewidth(1.0)

    # Title and subtitles
    fig.suptitle(
        f"{company_name} ({ticker_symbol.upper()}) \u2014 Last 8 Quarters Revenue",
        fontsize=16,
        fontweight="bold",
        x=0.08,
        y=0.98,
        ha="left",
        color="#0F172A",
    )
    ax.set_title(
        "Source: Official SEC EDGAR Filings (Form 10-Q & Form 10-K) | US-GAAP Reported Figures",
        fontsize=10,
        color="#64748B",
        loc="left",
        pad=14,
    )

    # Footnote about Q4 10-K accounting methodology
    footnote = (
        "*Note: In US-GAAP reporting, Q4 is derived from annual 10-K less 9M cumulative figures (Q4 = FY - 9M).\n"
        "All values programmatically retrieved from SEC EDGAR API."
    )
    fig.text(
        0.08, 0.02,
        footnote,
        fontsize=8.5,
        color="#64748B",
        style="italic",
    )

    ax.legend(loc="upper left", frameon=True, facecolor="#FFFFFF", edgecolor="#E2E8F0", fontsize=9.5)

    plt.tight_layout(rect=[0.02, 0.06, 0.98, 0.95])
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"[4/4] Chart successfully rendered and saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Scrape last 8 quarters revenue from SEC EDGAR and generate chart.")
    parser.add_argument("--ticker", type=str, default="TSLA", help="Company ticker symbol (default: TSLA)")
    parser.add_argument("--user-agent", type=str, default=DEFAULT_USER_AGENT, help="SEC-compliant User-Agent header")
    parser.add_argument("--output-csv", type=str, default="data/tesla_revenue_last_8_quarters.csv", help="CSV output path")
    parser.add_argument("--output-chart", type=str, default="charts/tesla_revenue_last_8_quarters.png", help="Chart PNG output path")
    args = parser.parse_args()

    cik, display_name = resolve_cik(args.ticker, args.user_agent)
    print(f"Target Company: {display_name} (Ticker: {args.ticker.upper()}, CIK: {cik})")

    # 1. Fetch SEC XBRL facts
    facts = fetch_sec_company_facts(cik, args.user_agent)
    company_name = facts.get("entityName", display_name)

    # 2. Extract and normalize the last 8 quarters
    df = parse_quarterly_revenue(facts)

    print("\n" + "=" * 70)
    print(f" {company_name} ({args.ticker.upper()}) — Last 8 Quarters Revenue ")
    print("=" * 70)
    summary_cols = ["quarter", "period_end", "form", "revenue_billions", "qoq_growth_pct", "yoy_growth_pct"]
    print(df[summary_cols].to_string(index=False, justify="center"))
    print("=" * 70 + "\n")

    # 3. Export CSV
    os.makedirs(os.path.dirname(os.path.abspath(args.output_csv)), exist_ok=True)
    df.to_csv(args.output_csv, index=False)
    print(f"[3/4] Data exported to: {args.output_csv}")

    # 4. Generate Chart
    generate_revenue_chart(df, company_name, args.ticker, args.output_chart)
    print("\nPipeline completed successfully!")


if __name__ == "__main__":
    main()
