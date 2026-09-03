"""
In-process module for rendering publication-quality financial charts.
"""

from __future__ import annotations

import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


class RevenueChart:
    """
    Decoupled financial chart renderer for quarterly revenue series.
    Produces in-memory Matplotlib figures and handles file output seams.
    """

    FOOTNOTE_TEXT = (
        "*Note: In US-GAAP reporting, Q4 is derived from annual 10-K less 9M cumulative figures (Q4 = FY - 9M).\n"
        "All values programmatically retrieved from SEC EDGAR API."
    )

    def __init__(self, style_name: str = "seaborn-v0_8-whitegrid"):
        self.style_name = style_name if style_name in plt.style.available else "default"

    def create_figure(self, df: pd.DataFrame, company_name: str, ticker_symbol: str) -> plt.Figure:
        """Render a styled revenue bar and trajectory figure in memory."""
        plt.style.use(self.style_name)

        fig, ax = plt.subplots(figsize=(12, 7), dpi=300)
        fig.patch.set_facecolor("#FFFFFF")
        ax.set_facecolor("#F9FAFC")

        quarters = df["quarter"].tolist()
        revenues = df["revenue_billions"].tolist()
        x = range(len(quarters))

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
            label="Quarterly Revenue ($B)",
        )

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
            label="Quarterly Trajectory",
        )

        max_rev = max(revenues) if revenues else 1.0
        for i, (bar, rev) in enumerate(zip(bars, revenues)):
            height = bar.get_height()
            yoy = df["yoy_growth_pct"].iloc[i] if "yoy_growth_pct" in df.columns else None
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
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#FFFFFF", alpha=0.85, edgecolor="#E2E8F0", linewidth=0.5),
            )

        ax.set_xticks(list(x))
        ax.set_xticklabels(quarters, fontsize=11, fontweight="bold", color="#334155")
        ax.set_ylabel("Revenue in Billions (USD)", fontsize=12, fontweight="bold", color="#1E293B", labelpad=10)
        ax.set_ylim(0, max_rev * 1.25)
        ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("$%.1fB"))

        ax.grid(axis="y", linestyle=":", alpha=0.6, color="#CBD5E1")
        ax.grid(axis="x", visible=False)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_color("#94A3B8")
            ax.spines[spine].set_linewidth(1.0)

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

        fig.text(
            0.08, 0.02,
            self.FOOTNOTE_TEXT,
            fontsize=8.5,
            color="#64748B",
            style="italic",
        )

        ax.legend(loc="upper left", frameon=True, facecolor="#FFFFFF", edgecolor="#E2E8F0", fontsize=9.5)
        plt.tight_layout(rect=[0.02, 0.06, 0.98, 0.95])

        return fig

    def save(self, df: pd.DataFrame, company_name: str, ticker_symbol: str, output_path: str) -> str:
        """Render figure and persist to disk via filesystem seam."""
        fig = self.create_figure(df, company_name, ticker_symbol)
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            fig.savefig(output_path, dpi=300)
            return output_path
        finally:
            plt.close(fig)
