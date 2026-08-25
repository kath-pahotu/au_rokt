"""Reproducible, privacy-safe analysis for the Rokt holdout experiment.

The raw file is intentionally supplied at runtime and is never copied to the
portfolio repository. This script writes aggregate CSVs, chart assets, and a
machine-readable results file that power every public-facing deliverable.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter

matplotlib.use("Agg")
import matplotlib.pyplot as plt


COLORS = {
    "ink": "#101828",
    "navy": "#111A36",
    "treatment": "#F46B45",
    "control": "#3F7CFF",
    "teal": "#1CB5A3",
    "paper": "#F5F7FB",
    "muted": "#667085",
    "line": "#D8DEE9",
    "white": "#FFFFFF",
    "warn": "#F4B740",
}


def _json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    raise TypeError(f"Cannot serialize {type(value)!r}")


def two_proportion_ztest(x_t: int, n_t: int, x_c: int, n_c: int) -> tuple[float, float]:
    """Return a two-sided pooled two-proportion z-test."""
    if n_t == 0 or n_c == 0:
        return math.nan, math.nan
    pooled = (x_t + x_c) / (n_t + n_c)
    if pooled in (0, 1):
        return math.nan, math.nan
    standard_error = math.sqrt(pooled * (1 - pooled) * ((1 / n_t) + (1 / n_c)))
    z_stat = ((x_t / n_t) - (x_c / n_c)) / standard_error
    p_value = math.erfc(abs(z_stat) / math.sqrt(2))
    return z_stat, p_value


def confidence_intervals(
    x_t: int, n_t: int, x_c: int, n_c: int
) -> dict[str, float]:
    """Wald CI for absolute lift and log-risk-ratio CI for relative lift."""
    p_t = x_t / n_t
    p_c = x_c / n_c
    diff = p_t - p_c
    se_diff = math.sqrt((p_t * (1 - p_t) / n_t) + (p_c * (1 - p_c) / n_c))
    rr = p_t / p_c
    se_log_rr = math.sqrt(((1 - p_t) / (n_t * p_t)) + ((1 - p_c) / (n_c * p_c)))
    return {
        "absolute_low": diff - 1.96 * se_diff,
        "absolute_high": diff + 1.96 * se_diff,
        "risk_ratio": rr,
        "relative_uplift_low": math.exp(math.log(rr) - 1.96 * se_log_rr) - 1,
        "relative_uplift_high": math.exp(math.log(rr) + 1.96 * se_log_rr) - 1,
    }


def load_and_clean(input_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(input_path)
    required = {
        "agegroup",
        "bidprice_usd",
        "campaigntimestamp",
        "cohort",
        "device",
        "gender",
        "group",
        "sessionid",
        "userhash",
        "value",
        "verticalname",
    }
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    invalid_cohort_rows = int((raw["cohort"] == 203902).sum())
    working = raw.loc[raw["cohort"] != 203902].copy()
    duplicate_rows = int(working.duplicated().sum())
    working = working.drop_duplicates().copy()

    missing_device = int(working["device"].isna().sum())
    missing_gender = int(working["gender"].isna().sum())

    working["device"] = (
        working["device"].astype("string").str.strip().str.title().fillna("Unknown")
    )
    working["gender"] = (
        working["gender"].astype("string").str.strip().str.lower().fillna("unknown")
    )
    working["converted"] = working["value"].notna()
    working["campaigntimestamp"] = pd.to_datetime(
        working["campaigntimestamp"], errors="raise"
    )

    user_group_counts = working.groupby("userhash")["group"].nunique()
    user_cohort_group_counts = working.groupby(["cohort", "userhash"])["group"].nunique()
    session_group_counts = working.groupby("sessionid")["group"].nunique()

    quality = pd.DataFrame(
        [
            ("Raw rows", len(raw), "Input"),
            ("Invalid cohort rows removed", invalid_cohort_rows, "Removed"),
            ("Exact duplicate rows removed", duplicate_rows, "Removed"),
            ("Clean analysis rows", len(working), "Output"),
            ("Missing device values filled", missing_device, "Repaired"),
            ("Missing gender values filled", missing_gender, "Repaired"),
            ("Unique users", working["userhash"].nunique(), "Context"),
            ("Unique sessions", working["sessionid"].nunique(), "Context"),
            (
                "Users appearing in both groups across months",
                int((user_group_counts > 1).sum()),
                "Caution",
            ),
            (
                "User-cohort pairs appearing in both groups",
                int((user_cohort_group_counts > 1).sum()),
                "Caution",
            ),
            (
                "Sessions appearing in both groups",
                int((session_group_counts > 1).sum()),
                "Caution",
            ),
        ],
        columns=["check", "count", "status"],
    )
    return working, quality


def summarize_group(group_df: pd.DataFrame, group: str) -> dict[str, float | int | str]:
    users = int(group_df["userhash"].nunique())
    converted_users = int(group_df.loc[group_df["converted"], "userhash"].nunique())
    sessions = int(group_df["sessionid"].nunique())
    converted_sessions = int(
        group_df.loc[group_df["converted"], "sessionid"].nunique()
    )
    bid_sum = float(group_df["bidprice_usd"].sum())
    value_sum = float(group_df["value"].sum())
    return {
        "group": group,
        "rows": int(len(group_df)),
        "users": users,
        "converted_users": converted_users,
        "conversion_rate": converted_users / users,
        "sessions": sessions,
        "converted_sessions": converted_sessions,
        "session_conversion_rate": converted_sessions / sessions,
        "bidprice_sum_usd": bid_sum,
        "vpt_usd": bid_sum / sessions,
        "conversion_value_sum_usd": value_sum,
        "conversion_value_per_user_usd": value_sum / users,
    }


def overall_metrics(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    summary = pd.DataFrame(
        [summarize_group(df.loc[df["group"] == group], group) for group in ["treatment", "control"]]
    )
    t = summary.set_index("group").loc["treatment"]
    c = summary.set_index("group").loc["control"]
    cr_t = float(t["conversion_rate"])
    cr_c = float(c["conversion_rate"])
    z_stat, p_value = two_proportion_ztest(
        int(t["converted_users"]), int(t["users"]), int(c["converted_users"]), int(c["users"])
    )
    cis = confidence_intervals(
        int(t["converted_users"]), int(t["users"]), int(c["converted_users"]), int(c["users"])
    )
    extra_conversions = float(t["converted_users"] - (t["users"] * cr_c))
    converted_rows = df.loc[df["converted"], "value"]
    average_conversion_value = float(converted_rows.mean())
    headline = {
        "cr_treatment": cr_t,
        "cr_control": cr_c,
        "absolute_lift": cr_t - cr_c,
        "relative_uplift": (cr_t - cr_c) / cr_c,
        "z_statistic": z_stat,
        "p_value": p_value,
        "absolute_lift_ci_low": cis["absolute_low"],
        "absolute_lift_ci_high": cis["absolute_high"],
        "relative_uplift_ci_low": cis["relative_uplift_low"],
        "relative_uplift_ci_high": cis["relative_uplift_high"],
        "extra_conversions_estimate": extra_conversions,
        "average_conversion_value_usd": average_conversion_value,
        "incremental_conversion_value_estimate_usd": extra_conversions
        * average_conversion_value,
        "clean_rows": int(len(df)),
        "unique_users": int(df["userhash"].nunique()),
        "unique_sessions": int(df["sessionid"].nunique()),
    }
    return summary, headline


def segment_summary(df: pd.DataFrame, segment: str) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for value in sorted(df[segment].dropna().unique(), key=lambda item: str(item)):
        subsets = {}
        for group in ["treatment", "control"]:
            subset = df.loc[(df[segment] == value) & (df["group"] == group)]
            users = int(subset["userhash"].nunique())
            converted = int(subset.loc[subset["converted"], "userhash"].nunique())
            subsets[group] = {
                "users": users,
                "converted": converted,
                "cr": converted / users if users else np.nan,
            }
        t = subsets["treatment"]
        c = subsets["control"]
        z_stat, p_value = two_proportion_ztest(
            t["converted"], t["users"], c["converted"], c["users"]
        )
        rows.append(
            {
                segment: value,
                "treatment_users": t["users"],
                "control_users": c["users"],
                "treatment_converted_users": t["converted"],
                "control_converted_users": c["converted"],
                "treatment_cr": t["cr"],
                "control_cr": c["cr"],
                "absolute_lift": t["cr"] - c["cr"],
                "relative_uplift": (t["cr"] - c["cr"]) / c["cr"] if c["cr"] else np.nan,
                "z_statistic": z_stat,
                "p_value": p_value,
            }
        )
    return pd.DataFrame(rows)


def cohort_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cohort in sorted(df["cohort"].unique()):
        t = df.loc[(df["cohort"] == cohort) & (df["group"] == "treatment")]
        c = df.loc[(df["cohort"] == cohort) & (df["group"] == "control")]
        ts = summarize_group(t, "treatment")
        cs = summarize_group(c, "control")
        z_stat, p_value = two_proportion_ztest(
            ts["converted_users"], ts["users"], cs["converted_users"], cs["users"]
        )
        rows.append(
            {
                "cohort": int(cohort),
                "cohort_label": pd.to_datetime(str(cohort), format="%Y%m").strftime("%b %Y"),
                "treatment_users": ts["users"],
                "control_users": cs["users"],
                "treatment_converted_users": ts["converted_users"],
                "control_converted_users": cs["converted_users"],
                "treatment_cr": ts["conversion_rate"],
                "control_cr": cs["conversion_rate"],
                "absolute_lift": ts["conversion_rate"] - cs["conversion_rate"],
                "relative_uplift": (
                    (ts["conversion_rate"] - cs["conversion_rate"]) / cs["conversion_rate"]
                ),
                "treatment_vpt_usd": ts["vpt_usd"],
                "control_vpt_usd": cs["vpt_usd"],
                "z_statistic": z_stat,
                "p_value": p_value,
                "significant_05": p_value < 0.05,
            }
        )
    return pd.DataFrame(rows)


def sensitivity_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    def add_row(name: str, t_success: int, t_n: int, c_success: int, c_n: int, note: str):
        cr_t = t_success / t_n
        cr_c = c_success / c_n
        z_stat, p_value = two_proportion_ztest(t_success, t_n, c_success, c_n)
        rows.append(
            {
                "analysis_unit": name,
                "treatment_n": t_n,
                "control_n": c_n,
                "treatment_converted": t_success,
                "control_converted": c_success,
                "treatment_cr": cr_t,
                "control_cr": cr_c,
                "relative_uplift": (cr_t - cr_c) / cr_c,
                "z_statistic": z_stat,
                "p_value": p_value,
                "interpretation": note,
            }
        )

    t = df.loc[df["group"] == "treatment"]
    c = df.loc[df["group"] == "control"]
    add_row(
        "Brief-defined unique users",
        int(t.loc[t["converted"], "userhash"].nunique()),
        int(t["userhash"].nunique()),
        int(c.loc[c["converted"], "userhash"].nunique()),
        int(c["userhash"].nunique()),
        "Required KPI; users can appear in both groups across months.",
    )

    user_cohort = (
        df.groupby(["cohort", "userhash", "group"], as_index=False)
        .agg(converted=("converted", "max"))
    )
    ambiguous_user_cohorts = (
        user_cohort.groupby(["cohort", "userhash"])["group"].nunique().loc[lambda s: s > 1].index
    )
    ambiguous_keys = set(ambiguous_user_cohorts)
    user_cohort["key"] = list(zip(user_cohort["cohort"], user_cohort["userhash"]))
    user_cohort = user_cohort.loc[~user_cohort["key"].isin(ambiguous_keys)]
    uct = user_cohort.loc[user_cohort["group"] == "treatment"]
    ucc = user_cohort.loc[user_cohort["group"] == "control"]
    add_row(
        "User-cohort",
        int(uct["converted"].sum()),
        int(len(uct)),
        int(ucc["converted"].sum()),
        int(len(ucc)),
        "Preferred sensitivity view for monthly re-assignment; 92 ambiguous user-cohorts excluded.",
    )

    session_groups = df.groupby("sessionid")["group"].nunique()
    ambiguous_sessions = set(session_groups.loc[session_groups > 1].index)
    session = (
        df.loc[~df["sessionid"].isin(ambiguous_sessions)]
        .groupby(["sessionid", "group"], as_index=False)
        .agg(converted=("converted", "max"))
    )
    st = session.loc[session["group"] == "treatment"]
    sc = session.loc[session["group"] == "control"]
    add_row(
        "Session",
        int(st["converted"].sum()),
        int(st["sessionid"].nunique()),
        int(sc["converted"].sum()),
        int(sc["sessionid"].nunique()),
        "Session-level sensitivity view; six ambiguous sessions excluded.",
    )
    return pd.DataFrame(rows)


def allocation_summary(df: pd.DataFrame) -> pd.DataFrame:
    table = pd.crosstab(df["cohort"], df["group"]).reset_index()
    table["cohort_label"] = pd.to_datetime(table["cohort"].astype(str), format="%Y%m").dt.strftime(
        "%b %Y"
    )
    table["treatment_share"] = table["treatment"] / (table["treatment"] + table["control"])
    return table[["cohort", "cohort_label", "treatment", "control", "treatment_share"]]


def configure_plotting():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 15,
            "axes.titleweight": "bold",
            "axes.labelcolor": COLORS["muted"],
            "axes.edgecolor": COLORS["line"],
            "axes.facecolor": COLORS["white"],
            "figure.facecolor": COLORS["paper"],
            "xtick.color": COLORS["muted"],
            "ytick.color": COLORS["muted"],
            "grid.color": COLORS["line"],
            "grid.alpha": 0.55,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def save_figure(fig: plt.Figure, image_dir: Path, stem: str):
    fig.savefig(image_dir / f"{stem}.png", dpi=190, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(image_dir / f"{stem}.svg", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def make_charts(
    headline: dict[str, float],
    cohorts: pd.DataFrame,
    devices: pd.DataFrame,
    quality: pd.DataFrame,
    allocation: pd.DataFrame,
    image_dir: Path,
):
    configure_plotting()
    image_dir.mkdir(parents=True, exist_ok=True)

    x = np.arange(len(cohorts))
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(x, cohorts["treatment_cr"], color=COLORS["treatment"], marker="o", linewidth=2.8, label="Treatment")
    ax.plot(x, cohorts["control_cr"], color=COLORS["control"], marker="o", linewidth=2.8, label="Control")
    ax.set_xticks(x, cohorts["cohort_label"])
    ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=1))
    ax.set_ylabel("Conversion rate")
    ax.set_title("Treatment converted better in every monthly cohort", loc="left")
    ax.grid(axis="y")
    ax.legend(frameon=False, ncol=2, loc="upper right")
    ax.text(0, -0.20, "Brief-defined unique-user conversion rate; exact duplicate rows removed.", transform=ax.transAxes, color=COLORS["muted"], fontsize=9)
    save_figure(fig, image_dir, "cohort_conversion_rates")

    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.bar(x, cohorts["relative_uplift"], color=COLORS["treatment"], width=0.62)
    ax.axhline(headline["relative_uplift"], color=COLORS["navy"], linestyle="--", linewidth=1.4, label="Overall brief-defined uplift")
    ax.set_xticks(x, cohorts["cohort_label"])
    ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.set_ylabel("Relative uplift")
    ax.set_title("Positive uplift persisted across all five cohorts", loc="left")
    ax.grid(axis="y")
    ax.legend(frameon=False, loc="upper right")
    for bar, value in zip(bars, cohorts["relative_uplift"]):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.008, f"{value:.1%}", ha="center", va="bottom", color=COLORS["ink"], fontsize=9, fontweight="bold")
    save_figure(fig, image_dir, "cohort_uplift")

    display_devices = devices.sort_values("relative_uplift")
    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.barh(display_devices["device"], display_devices["relative_uplift"], color=COLORS["teal"], height=0.58)
    ax.axvline(0, color=COLORS["muted"], linewidth=0.8)
    ax.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.set_xlabel("Relative conversion-rate uplift")
    ax.set_title("Desktop showed the strongest descriptive uplift", loc="left")
    ax.grid(axis="x")
    for bar, value in zip(bars, display_devices["relative_uplift"]):
        ax.text(value + 0.006, bar.get_y() + bar.get_height() / 2, f"{value:.1%}", va="center", color=COLORS["ink"], fontsize=10, fontweight="bold")
    ax.text(0, -0.20, "Segment results are descriptive; sample size and assignment-unit caveats still apply.", transform=ax.transAxes, color=COLORS["muted"], fontsize=9)
    save_figure(fig, image_dir, "device_uplift")

    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.bar(x, allocation["treatment_share"], color=COLORS["navy"], width=0.62)
    ax.set_xticks(x, allocation["cohort_label"])
    ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.set_ylim(0.65, 0.95)
    ax.set_ylabel("Treatment share of cleaned events")
    ax.set_title("The treatment allocation increased materially over time", loc="left")
    ax.grid(axis="y")
    for bar, value in zip(bars, allocation["treatment_share"]):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.008, f"{value:.1%}", ha="center", fontweight="bold", color=COLORS["ink"])
    save_figure(fig, image_dir, "allocation_by_cohort")

    quality_focus = quality.loc[
        quality["check"].isin(
            [
                "Exact duplicate rows removed",
                "Missing device values filled",
                "Missing gender values filled",
                "Users appearing in both groups across months",
                "User-cohort pairs appearing in both groups",
            ]
        )
    ].copy()
    fig, ax = plt.subplots(figsize=(11, 5.8))
    y = np.arange(len(quality_focus))
    bars = ax.barh(y, quality_focus["count"], color=[COLORS["warn"], COLORS["control"], COLORS["control"], COLORS["treatment"], COLORS["treatment"]])
    ax.set_yticks(y, quality_focus["check"])
    ax.invert_yaxis()
    ax.set_xlabel("Rows or entities affected")
    ax.set_title("The audit found repairable quality issues and an assignment caveat", loc="left")
    ax.grid(axis="x")
    for bar, value in zip(bars, quality_focus["count"]):
        ax.text(value + max(quality_focus["count"]) * 0.012, bar.get_y() + bar.get_height() / 2, f"{int(value):,}", va="center", fontweight="bold", color=COLORS["ink"])
    ax.set_xlim(0, max(quality_focus["count"]) * 1.18)
    save_figure(fig, image_dir, "data_quality_audit")

    fig = plt.figure(figsize=(12, 4.2))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.04, 0.88, "HOLDOUT EXPERIMENT", fontsize=10, color=COLORS["muted"], fontweight="bold")
    ax.text(0.04, 0.70, "Eligible campaign event", fontsize=20, color=COLORS["ink"], fontweight="bold")
    ax.annotate("", xy=(0.38, 0.62), xytext=(0.24, 0.62), arrowprops=dict(arrowstyle="->", color=COLORS["muted"], lw=1.8))
    ax.text(0.41, 0.70, "Assignment", fontsize=15, color=COLORS["ink"], fontweight="bold", ha="center")
    ax.plot([0.42, 0.42], [0.56, 0.34], color=COLORS["line"], lw=2)
    ax.plot([0.42, 0.60], [0.44, 0.70], color=COLORS["treatment"], lw=3)
    ax.plot([0.42, 0.60], [0.44, 0.20], color=COLORS["control"], lw=3)
    ax.text(0.63, 0.72, "Treatment", fontsize=15, color=COLORS["treatment"], fontweight="bold")
    ax.text(0.63, 0.63, "Advertisement shown", fontsize=11, color=COLORS["muted"])
    ax.text(0.63, 0.22, "Control", fontsize=15, color=COLORS["control"], fontweight="bold")
    ax.text(0.63, 0.13, "Advertisement suppressed", fontsize=11, color=COLORS["muted"])
    ax.annotate("", xy=(0.93, 0.46), xytext=(0.82, 0.67), arrowprops=dict(arrowstyle="->", color=COLORS["treatment"], lw=1.8))
    ax.annotate("", xy=(0.93, 0.46), xytext=(0.82, 0.22), arrowprops=dict(arrowstyle="->", color=COLORS["control"], lw=1.8))
    ax.text(0.95, 0.50, "Compare\nconversion", fontsize=14, color=COLORS["ink"], fontweight="bold", ha="center", va="center")
    save_figure(fig, image_dir, "experiment_design")

    fig = plt.figure(figsize=(16, 9), facecolor=COLORS["navy"])
    gs = fig.add_gridspec(12, 24, left=0.045, right=0.97, top=0.94, bottom=0.07, hspace=1.5, wspace=1.3)
    fig.text(0.048, 0.93, "ROKT HOLDOUT EXPERIMENT", color="#AAB4D1", fontsize=10, fontweight="bold")
    fig.text(0.048, 0.875, "A positive signal, with an important unit-of-analysis caveat", color=COLORS["white"], fontsize=25, fontweight="bold")
    fig.text(0.048, 0.83, "Primary brief-defined result | Feb-Jun 2020 | exact duplicate rows removed", color="#C8D0E5", fontsize=11)

    cards = [
        ("Treatment CR", f"{headline['cr_treatment']:.2%}", COLORS["treatment"]),
        ("Control CR", f"{headline['cr_control']:.2%}", COLORS["control"]),
        ("Relative uplift", f"+{headline['relative_uplift']:.1%}", COLORS["teal"]),
        ("Extra conversions", f"{headline['extra_conversions_estimate']:,.0f}", COLORS["warn"]),
    ]
    for index, (label, value, color) in enumerate(cards):
        left = 0.048 + index * 0.235
        rect = plt.Rectangle((left, 0.67), 0.205, 0.115, transform=fig.transFigure, facecolor="#192548", edgecolor="#314064", linewidth=1)
        fig.add_artist(rect)
        fig.text(left + 0.018, 0.747, label.upper(), color="#AAB4D1", fontsize=8.5, fontweight="bold")
        fig.text(left + 0.018, 0.695, value, color=color, fontsize=24, fontweight="bold")

    ax1 = fig.add_subplot(gs[5:11, 0:12])
    ax1.set_facecolor("#162142")
    ax1.plot(x, cohorts["treatment_cr"], color=COLORS["treatment"], marker="o", lw=2.4, label="Treatment")
    ax1.plot(x, cohorts["control_cr"], color=COLORS["control"], marker="o", lw=2.4, label="Control")
    ax1.set_xticks(x, [label.replace(" 2020", "") for label in cohorts["cohort_label"]])
    ax1.yaxis.set_major_formatter(PercentFormatter(1, decimals=1))
    ax1.set_title("Conversion rate by cohort", loc="left", color=COLORS["white"], fontsize=13)
    ax1.tick_params(colors="#C8D0E5")
    ax1.grid(axis="y", color="#314064", alpha=0.65)
    for spine in ax1.spines.values():
        spine.set_visible(False)
    ax1.legend(frameon=False, labelcolor="#C8D0E5", ncol=2, loc="upper right")

    ax2 = fig.add_subplot(gs[5:11, 13:24])
    ax2.set_facecolor("#162142")
    display = devices.sort_values("relative_uplift")
    ax2.barh(display["device"], display["relative_uplift"], color=COLORS["teal"], height=0.55)
    ax2.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax2.set_title("Descriptive uplift by device", loc="left", color=COLORS["white"], fontsize=13)
    ax2.tick_params(colors="#C8D0E5")
    ax2.grid(axis="x", color="#314064", alpha=0.65)
    for spine in ax2.spines.values():
        spine.set_visible(False)
    for y_pos, value in enumerate(display["relative_uplift"]):
        ax2.text(value + 0.006, y_pos, f"{value:.1%}", va="center", color=COLORS["white"], fontsize=9, fontweight="bold")

    fig.text(0.048, 0.055, "AUDIT NOTE", color=COLORS["warn"], fontsize=9, fontweight="bold")
    fig.text(0.125, 0.055, "26,426 users changed group across months; the user-cohort sensitivity estimate is +5.5% (p=0.016).", color="#C8D0E5", fontsize=9.5)
    save_figure(fig, image_dir, "dashboard_overview")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="Path to the private raw CSV")
    parser.add_argument("--output-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    output_root = args.output_root.resolve()
    aggregate_dir = output_root / "data" / "aggregated"
    image_dir = output_root / "images"
    aggregate_dir.mkdir(parents=True, exist_ok=True)

    df, quality = load_and_clean(args.input.resolve())
    group_kpis, headline = overall_metrics(df)
    cohorts = cohort_summary(df)
    devices = segment_summary(df, "device")
    ages = segment_summary(df, "agegroup")
    verticals = segment_summary(df, "verticalname")
    genders = segment_summary(df, "gender")
    sensitivity = sensitivity_summary(df)
    allocation = allocation_summary(df)

    outputs = {
        "group_kpis.csv": group_kpis,
        "cohort_summary.csv": cohorts,
        "device_summary.csv": devices,
        "agegroup_summary.csv": ages,
        "vertical_summary.csv": verticals,
        "gender_summary.csv": genders,
        "sensitivity_summary.csv": sensitivity,
        "allocation_summary.csv": allocation,
        "data_quality_summary.csv": quality,
    }
    for filename, table in outputs.items():
        table.to_csv(aggregate_dir / filename, index=False)

    with (aggregate_dir / "headline_metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(headline, handle, indent=2, default=_json_default)

    make_charts(headline, cohorts, devices, quality, allocation, image_dir)
    print(json.dumps({"headline": headline, "output_root": str(output_root)}, indent=2, default=_json_default))


if __name__ == "__main__":
    main()
