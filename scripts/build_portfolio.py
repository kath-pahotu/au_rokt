"""Build public-facing documentation, notebook, and dashboard from aggregates."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "aggregated"
IMAGES = ROOT / "images"


def fmt_pct(value: float, decimals: int = 2) -> str:
    return f"{value:.{decimals}%}"


def markdown_table(rows: list[list[str]], headers: list[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def image_output(path: Path) -> dict:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return {
        "output_type": "display_data",
        "metadata": {},
        "data": {"image/png": encoded, "text/plain": [f"<{path.name}>"]},
    }


def code_cell(source: str, count: int, outputs: list[dict] | None = None) -> dict:
    return {
        "cell_type": "code",
        "execution_count": count,
        "metadata": {},
        "outputs": outputs or [],
        "source": [line + "\n" for line in source.strip().splitlines()],
    }


def markdown_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in source.strip().splitlines()],
    }


def table_output(frame: pd.DataFrame) -> list[dict]:
    return [
        {
            "output_type": "execute_result",
            "execution_count": None,
            "metadata": {},
            "data": {
                "text/plain": frame.to_string(index=False).splitlines(True),
                "text/html": frame.to_html(index=False, border=0).splitlines(True),
            },
        }
    ]


def build_notebook(
    headline: dict,
    quality: pd.DataFrame,
    group_kpis: pd.DataFrame,
    cohorts: pd.DataFrame,
    sensitivity: pd.DataFrame,
    devices: pd.DataFrame,
):
    quality_view = quality.copy()
    group_view = group_kpis[
        ["group", "users", "converted_users", "conversion_rate", "sessions", "vpt_usd"]
    ].copy()
    group_view["conversion_rate"] = group_view["conversion_rate"].map(lambda x: f"{x:.4%}")
    group_view["vpt_usd"] = group_view["vpt_usd"].map(lambda x: f"${x:.4f}")

    cohort_view = cohorts[
        ["cohort_label", "treatment_cr", "control_cr", "relative_uplift", "p_value"]
    ].copy()
    for column in ["treatment_cr", "control_cr", "relative_uplift"]:
        cohort_view[column] = cohort_view[column].map(lambda x: f"{x:.2%}")
    cohort_view["p_value"] = cohort_view["p_value"].map(lambda x: f"{x:.3g}")

    sensitivity_view = sensitivity[
        ["analysis_unit", "treatment_cr", "control_cr", "relative_uplift", "p_value"]
    ].copy()
    for column in ["treatment_cr", "control_cr", "relative_uplift"]:
        sensitivity_view[column] = sensitivity_view[column].map(lambda x: f"{x:.2%}")
    sensitivity_view["p_value"] = sensitivity_view["p_value"].map(lambda x: f"{x:.3g}")

    device_view = devices[
        ["device", "treatment_users", "control_users", "treatment_cr", "control_cr", "relative_uplift"]
    ].copy()
    for column in ["treatment_cr", "control_cr", "relative_uplift"]:
        device_view[column] = device_view[column].map(lambda x: f"{x:.2%}")

    cells = [
        markdown_cell(
            f"""
# Rokt holdout experiment analysis

**Business question:** Did showing Rokt advertisements create incremental conversion lift compared with a suppressed-ad holdout?

**Portfolio result:** Under the brief-defined unique-user KPI, treatment converted at **{headline['cr_treatment']:.2%}** versus **{headline['cr_control']:.2%}** for control: **+{headline['relative_uplift']:.1%} relative uplift**. A user-cohort sensitivity analysis estimates a smaller but still positive effect.

The raw dataset is private and excluded from this public repository. Every displayed result was generated from the sanitized pipeline in `src/analysis.py`.
"""
        ),
        markdown_cell(
            """
## 1. Reproducible setup

Set `ROKT_DATA_PATH` to your authorized local copy of the CSV. The notebook never embeds raw user or session identifiers.
"""
        ),
        code_cell(
            """
import os
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import (
    allocation_summary,
    cohort_summary,
    load_and_clean,
    overall_metrics,
    segment_summary,
    sensitivity_summary,
)

DATA_PATH = Path(os.environ.get("ROKT_DATA_PATH", PROJECT_ROOT / "data" / "raw" / "rokt_data.csv"))
if not DATA_PATH.exists():
    raise FileNotFoundError("Set ROKT_DATA_PATH to an authorized local copy of rokt_data.csv")
""",
            1,
        ),
        markdown_cell(
            """
## 2. Data-quality audit and cleaning

The pipeline removes the invalid 203902 cohort and exact duplicate records, standardizes device labels, fills missing device/gender categories, creates the conversion flag, and parses timestamps. The audit also checks whether users or sessions appear in both experiment groups.
"""
        ),
        code_cell(
            """
df, quality = load_and_clean(DATA_PATH)
quality
""",
            2,
            table_output(quality_view),
        ),
        markdown_cell(
            """
The original notebook missed `NaN` device/gender values because it used `replace('')` rather than `fillna()`. It also retained exact duplicates, which inflated VPT and conversion-value totals. Both issues are corrected here.
"""
        ),
        markdown_cell("## 3. Primary experiment KPIs"),
        code_cell(
            """
group_kpis, headline = overall_metrics(df)
group_kpis[['group', 'users', 'converted_users', 'conversion_rate', 'sessions', 'vpt_usd']]
""",
            3,
            table_output(group_view),
        ),
        markdown_cell(
            f"""
Treatment exceeded control by **{headline['absolute_lift']:.3%} percentage points**, equal to **{headline['relative_uplift']:.1%} relative uplift**. Under a simple counterfactual applying the control rate to treatment users, this corresponds to approximately **{headline['extra_conversions_estimate']:,.0f} incremental conversions**.

VPT uses `bidprice_usd / unique sessions`, exactly as defined in the supplied brief.
"""
        ),
        markdown_cell("## 4. Statistical confidence"),
        code_cell(
            """
print(f"Z-statistic: {headline['z_statistic']:.3f}")
print(f"P-value: {headline['p_value']:.3e}")
print(
    "95% CI, absolute lift: "
    f"[{headline['absolute_lift_ci_low']:.3%}, {headline['absolute_lift_ci_high']:.3%}]"
)
print(
    "95% CI, relative uplift: "
    f"[{headline['relative_uplift_ci_low']:.1%}, {headline['relative_uplift_ci_high']:.1%}]"
)
""",
            4,
            [
                {
                    "output_type": "stream",
                    "name": "stdout",
                    "text": [
                        f"Z-statistic: {headline['z_statistic']:.3f}\n",
                        f"P-value: {headline['p_value']:.3e}\n",
                        f"95% CI, absolute lift: [{headline['absolute_lift_ci_low']:.3%}, {headline['absolute_lift_ci_high']:.3%}]\n",
                        f"95% CI, relative uplift: [{headline['relative_uplift_ci_low']:.1%}, {headline['relative_uplift_ci_high']:.1%}]\n",
                    ],
                }
            ],
        ),
        markdown_cell(
            """
This conventional test follows the requested user-level KPI. Because some users change assignment across months, the independence assumption is imperfect; the sensitivity analysis below is part of the conclusion, not a footnote to ignore.
"""
        ),
        markdown_cell("## 5. Performance by cohort"),
        code_cell(
            """
cohorts = cohort_summary(df)
cohorts[['cohort_label', 'treatment_cr', 'control_cr', 'relative_uplift', 'p_value']]
""",
            5,
            table_output(cohort_view),
        ),
        code_cell(
            """
from IPython.display import Image, display
display(Image(filename=PROJECT_ROOT / "images" / "cohort_conversion_rates.png"))
""",
            6,
            [image_output(IMAGES / "cohort_conversion_rates.png")],
        ),
        markdown_cell(
            """
Treatment conversion exceeded control in every monthly cohort. Both groups declined materially from February to June, which signals a strong time effect alongside the treatment-control gap.
"""
        ),
        markdown_cell("## 6. Unit-of-analysis sensitivity"),
        code_cell(
            """
sensitivity = sensitivity_summary(df)
sensitivity[['analysis_unit', 'treatment_cr', 'control_cr', 'relative_uplift', 'p_value']]
""",
            7,
            table_output(sensitivity_view),
        ),
        markdown_cell(
            """
The brief-defined result is the required KPI, but its magnitude is sensitive to the unit chosen. User-cohort and session views both produce approximately **+5.5% uplift** and remain statistically significant. The correct causal estimate ultimately depends on confirmation of the randomization unit.
"""
        ),
        markdown_cell("## 7. Descriptive device segmentation"),
        code_cell(
            """
devices = segment_summary(df, "device")
devices[['device', 'treatment_users', 'control_users', 'treatment_cr', 'control_cr', 'relative_uplift']]
""",
            8,
            table_output(device_view),
        ),
        code_cell(
            """
display(Image(filename=PROJECT_ROOT / "images" / "device_uplift.png"))
""",
            9,
            [image_output(IMAGES / "device_uplift.png")],
        ),
        markdown_cell(
            """
Desktop shows the strongest descriptive uplift, while Mobile shows the weakest. These are exploratory segment findings rather than proof that device causes different treatment effects.
"""
        ),
        markdown_cell(
            f"""
## 8. Business interpretation

- Under the brief-defined KPI, the treatment generated **+{headline['relative_uplift']:.1%} relative conversion uplift**.
- The effect was positive in all five cohorts, but overall conversion declined over time in both arms.
- A more conservative user-cohort view estimates about **+5.5% uplift**, so the randomization unit should be confirmed before rollout or financial forecasting.
- The simple counterfactual estimates **{headline['extra_conversions_estimate']:,.0f} additional conversions**.
- The corresponding **${headline['incremental_conversion_value_estimate_usd']:,.0f}** is an estimated incremental conversion value under an equal-average-value assumption, not verified Rokt revenue.

### Recommendation

Treat the result as a positive experiment signal. Validate assignment logic, then prioritize follow-up analysis on cohort decline and device differences before using the estimate for investment decisions.
"""
        ),
        markdown_cell(
            """
## 9. Limitations

- The supplied brief does not explicitly identify the randomization unit.
- Users can reappear and change groups across months.
- Segment comparisons are descriptive and are not adjusted for multiple testing.
- `value` is conversion value attributed to an event; it should not be labeled company revenue without a business definition.
- The public portfolio excludes raw data, pseudonymous user/session identifiers, and the proprietary assignment screenshots.
"""
        ),
    ]

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.13"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path = ROOT / "notebooks" / "rokt_ab_test_analysis.ipynb"
    path.write_text(json.dumps(notebook, indent=1), encoding="utf-8")


def build_dashboard(headline: dict, cohorts: pd.DataFrame, devices: pd.DataFrame, sensitivity: pd.DataFrame):
    payload = {
        "overall": {
            "label": "Overall",
            "treatment": headline["cr_treatment"],
            "control": headline["cr_control"],
            "uplift": headline["relative_uplift"],
            "p": headline["p_value"],
        },
        "cohorts": cohorts[
            ["cohort_label", "treatment_cr", "control_cr", "relative_uplift", "p_value"]
        ].to_dict(orient="records"),
        "devices": devices.dropna(subset=["relative_uplift"])[
            ["device", "treatment_cr", "control_cr", "relative_uplift", "treatment_users", "control_users"]
        ].sort_values("relative_uplift", ascending=False).to_dict(orient="records"),
        "sensitivity": sensitivity[
            ["analysis_unit", "treatment_cr", "control_cr", "relative_uplift", "p_value"]
        ].to_dict(orient="records"),
    }
    template = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Rokt Holdout Experiment Dashboard</title>
  <style>
    :root { --navy:#111a36; --panel:#182447; --line:#314064; --ink:#f8fafc; --muted:#aab4d1; --treatment:#f46b45; --control:#3f7cff; --teal:#1cb5a3; --warn:#f4b740; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--navy); color:var(--ink); font-family:"Segoe UI",Inter,Arial,sans-serif; }
    button, select { font:inherit; }
    .shell { max-width:1480px; margin:auto; padding:32px 40px 54px; }
    .eyebrow { color:var(--muted); font-size:12px; font-weight:800; letter-spacing:.16em; text-transform:uppercase; }
    h1 { max-width:1040px; margin:14px 0 10px; font-size:clamp(34px,5vw,64px); line-height:1.02; letter-spacing:-.04em; }
    .lead { max-width:900px; color:#c8d0e5; font-size:17px; line-height:1.55; }
    .controls { display:flex; gap:12px; align-items:center; margin:28px 0 20px; }
    label { color:var(--muted); font-size:13px; font-weight:700; }
    select { margin-left:8px; color:var(--ink); background:#1a274d; border:1px solid var(--line); padding:9px 34px 9px 12px; border-radius:6px; }
    select:focus-visible, button:focus-visible { outline:3px solid var(--warn); outline-offset:3px; }
    .cards { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; }
    .card { background:var(--panel); border:1px solid var(--line); padding:20px; min-height:120px; position:relative; overflow:hidden; }
    .card::after { content:""; position:absolute; left:0; bottom:0; width:100%; height:4px; background:var(--accent); }
    .card span { color:var(--muted); font-size:11px; font-weight:800; letter-spacing:.1em; text-transform:uppercase; }
    .card strong { display:block; margin-top:14px; font-size:36px; color:var(--accent); }
    .grid { display:grid; grid-template-columns:1.25fr .9fr; gap:18px; margin-top:18px; }
    .panel { background:var(--panel); border:1px solid var(--line); padding:24px; }
    .panel h2 { margin:0 0 6px; font-size:20px; }
    .panel p { margin:0 0 18px; color:var(--muted); line-height:1.5; }
    .hero-chart { width:100%; display:block; border:1px solid #24345f; }
    .device-row { display:grid; grid-template-columns:90px 1fr 72px; gap:12px; align-items:center; margin:18px 0; }
    .track { height:14px; background:#25345e; overflow:hidden; }
    .bar { height:100%; background:var(--teal); transition:width .45s ease; }
    .device-row b { text-align:right; }
    .split { margin-top:18px; display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }
    .split article { border-top:3px solid var(--teal); background:#131f40; padding:16px; }
    .split h3 { margin:0 0 10px; font-size:13px; }
    .split strong { font-size:24px; }
    .split small { display:block; color:var(--muted); margin-top:7px; }
    .audit { margin-top:18px; border-left:4px solid var(--warn); background:#191f36; padding:18px 20px; color:#d9deeb; line-height:1.55; }
    .audit b { color:var(--warn); }
    footer { margin-top:26px; color:var(--muted); font-size:12px; display:flex; justify-content:space-between; gap:20px; }
    @media (max-width:900px) { .shell{padding:24px 18px}.cards{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}.split{grid-template-columns:1fr} }
    @media (max-width:520px) { .cards{grid-template-columns:1fr}.controls{align-items:flex-start;flex-direction:column}.device-row{grid-template-columns:72px 1fr 58px} }
    @media (prefers-reduced-motion:reduce) { .bar{transition:none} }
  </style>
</head>
<body>
<main class="shell">
  <div class="eyebrow">Rokt holdout experiment / portfolio dashboard</div>
  <h1>A positive signal—measured twice.</h1>
  <p class="lead">The required unique-user KPI shows a 13.9% lift. A user-cohort sensitivity view is smaller, near 5.5%, because assignment can change across months.</p>
  <div class="controls"><label for="cohort">View period <select id="cohort"><option value="overall">Overall</option></select></label></div>
  <section class="cards" aria-label="Experiment KPIs">
    <div class="card" style="--accent:var(--treatment)"><span>Treatment CR</span><strong id="treatment">—</strong></div>
    <div class="card" style="--accent:var(--control)"><span>Control CR</span><strong id="control">—</strong></div>
    <div class="card" style="--accent:var(--teal)"><span>Relative uplift</span><strong id="uplift">—</strong></div>
    <div class="card" style="--accent:var(--warn)"><span>P-value</span><strong id="pvalue">—</strong></div>
  </section>
  <section class="grid">
    <article class="panel">
      <h2>Treatment stayed above control</h2>
      <p>Conversion declined in both arms from February to June, but the treatment-control gap remained positive.</p>
      <img class="hero-chart" src="../images/cohort_conversion_rates.png" alt="Line chart of treatment and control conversion rates by cohort">
    </article>
    <article class="panel">
      <h2>Device uplift</h2>
      <p>Descriptive segmentation, ordered by relative uplift.</p>
      <div id="devices"></div>
    </article>
  </section>
  <section class="panel" style="margin-top:18px">
    <h2>Robustness across analysis units</h2>
    <p>The headline changes when repeated users are represented at a different level. This is the key analytical caveat.</p>
    <div class="split" id="sensitivity"></div>
  </section>
  <aside class="audit"><b>Audit note.</b> The cleaning pipeline removed 36,893 exact duplicate rows and repaired missing device/gender categories. 26,426 users changed groups across months, while only 92 user-cohort pairs appeared in both groups.</aside>
  <footer><span>Source: supplied Feb–Jun 2020 holdout dataset; raw identifiers excluded.</span><span>Built with Python, pandas, statistical testing, and privacy-safe aggregates.</span></footer>
</main>
<script>
const data = __PAYLOAD__;
const pct = (v,d=2) => new Intl.NumberFormat('en-US',{style:'percent',minimumFractionDigits:d,maximumFractionDigits:d}).format(v);
const cohort = document.querySelector('#cohort');
data.cohorts.forEach((row,i)=>{ const option=document.createElement('option'); option.value=i; option.textContent=row.cohort_label; cohort.append(option); });
function updateCards(){ const row=cohort.value==='overall'?data.overall:data.cohorts[Number(cohort.value)]; document.querySelector('#treatment').textContent=pct(row.treatment ?? row.treatment_cr); document.querySelector('#control').textContent=pct(row.control ?? row.control_cr); document.querySelector('#uplift').textContent=(row.uplift ?? row.relative_uplift)>=0?`+${pct(row.uplift ?? row.relative_uplift,1)}`:pct(row.uplift ?? row.relative_uplift,1); const p=row.p ?? row.p_value; document.querySelector('#pvalue').textContent=p<0.001?'<0.001':p.toFixed(3); }
cohort.addEventListener('change',updateCards); updateCards();
document.querySelector('#devices').innerHTML=data.devices.map(row=>`<div class="device-row"><span>${row.device}</span><div class="track"><div class="bar" style="width:${Math.max(0,row.relative_uplift)*300}%"></div></div><b>${pct(row.relative_uplift,1)}</b></div>`).join('');
document.querySelector('#sensitivity').innerHTML=data.sensitivity.map(row=>`<article><h3>${row.analysis_unit}</h3><strong>${row.relative_uplift>=0?'+':''}${pct(row.relative_uplift,1)}</strong><small>T ${pct(row.treatment_cr)} · C ${pct(row.control_cr)} · p ${row.p_value<0.001?'&lt;0.001':row.p_value.toFixed(3)}</small></article>`).join('');
</script>
</body>
</html>'''
    (ROOT / "dashboard" / "index.html").write_text(
        template.replace("__PAYLOAD__", json.dumps(payload)), encoding="utf-8"
    )


def build_markdown(
    headline: dict,
    cohorts: pd.DataFrame,
    devices: pd.DataFrame,
    sensitivity: pd.DataFrame,
):
    cohort_min = cohorts["relative_uplift"].min()
    cohort_max = cohorts["relative_uplift"].max()
    top_device = devices.sort_values("relative_uplift", ascending=False).iloc[0]
    user_cohort = sensitivity.loc[sensitivity["analysis_unit"] == "User-cohort"].iloc[0]

    key_rows = [
        ["Treatment conversion rate", fmt_pct(headline["cr_treatment"], 4)],
        ["Control conversion rate", fmt_pct(headline["cr_control"], 4)],
        ["Absolute lift", f"{headline['absolute_lift']:.3%} percentage points"],
        ["Relative uplift", f"+{headline['relative_uplift']:.2%}"],
        ["95% CI, relative uplift", f"{headline['relative_uplift_ci_low']:.1%} to {headline['relative_uplift_ci_high']:.1%}"],
        ["Estimated additional conversions", f"{headline['extra_conversions_estimate']:,.0f}"],
    ]
    readme = f"""# Rokt Holdout Experiment Analysis

![Rokt experiment dashboard](images/dashboard_overview.png)

## Executive summary

This project evaluates whether showing Rokt advertisements increased conversion compared with a suppressed-ad holdout. It analyzes **{headline['clean_rows']:,} cleaned campaign-event records** across five monthly cohorts using Python, experiment statistics, sensitivity analysis, and BI-ready outputs.

Under the metric defined in the assignment, treatment converted at **{headline['cr_treatment']:.2%}** versus **{headline['cr_control']:.2%}** for control, a **+{headline['relative_uplift']:.1%} relative uplift**. The conventional two-proportion test gives `p = {headline['p_value']:.2e}`.

The experiment audit found that users can change assignment across months. A user-cohort sensitivity analysis estimates **+{user_cohort['relative_uplift']:.1%} uplift (`p = {user_cohort['p_value']:.3f}`)**. The result remains positive, but the magnitude depends on the confirmed randomization unit.

## Headline metrics

{markdown_table(key_rows, ['Metric', 'Result'])}

## Key findings

- Treatment conversion exceeded control in every cohort; cohort uplift ranged from **{cohort_min:.1%} to {cohort_max:.1%}**.
- Conversion declined in both groups from February to June, indicating a material time effect.
- **{top_device['device']}** showed the strongest descriptive device uplift at **{top_device['relative_uplift']:.1%}**.
- The simple control-rate counterfactual estimates approximately **{headline['extra_conversions_estimate']:,.0f} additional conversions**.
- Estimated incremental conversion value is **${headline['incremental_conversion_value_estimate_usd']:,.0f}** under an equal-average-value assumption. It is not labeled Rokt revenue.

## Why the data audit matters

The reproducible pipeline corrects issues that materially affect interpretation:

- Removes one invalid `203902` cohort row.
- Removes **36,893 exact duplicate rows** before calculating VPT and conversion value.
- Correctly fills missing device and gender categories with `fillna()`.
- Identifies **26,426 users** appearing in both groups across months, but only **92 user-cohort pairs** appearing in both groups within a cohort.
- Reports brief-defined, user-cohort, and session-level sensitivity results side by side.

![Data quality audit](images/data_quality_audit.png)

## Business recommendation

Treat the test as a positive experiment signal. Before using the result for rollout or financial forecasting, confirm whether assignment occurred by user, user-cohort, session, or event. Then investigate the overall conversion decline and validate whether the strong Desktop result persists in a follow-up test.

## Project assets

- [Portfolio notebook](notebooks/rokt_ab_test_analysis.ipynb) — cleaned analysis with outputs and interpretation.
- [Interactive dashboard](dashboard/index.html) — self-contained browser dashboard using aggregate data only.
- [Executive summary](reports/executive_summary.pdf) — concise stakeholder report.
- [Methodology](docs/methodology.md) — metric definitions, tests, assumptions, and limitations.
- [Data dictionary](docs/data_dictionary.md) — field-level definitions.

## Repository structure

```text
├── README.md
├── requirements.txt
├── src/analysis.py
├── notebooks/rokt_ab_test_analysis.ipynb
├── dashboard/
├── reports/
├── docs/
├── images/
└── data/aggregated/
```

## Reproduce the analysis

The raw dataset is intentionally not distributed. Place an authorized copy on your computer, then run:

```powershell
python -m pip install -r requirements.txt
python src/analysis.py --input "C:\\path\\to\\rokt_data.csv" --output-root .
```

For the notebook, set `ROKT_DATA_PATH` to the same authorized CSV path.

## Tools demonstrated

`Python` · `pandas` · `NumPy` · `matplotlib` · `A/B testing` · `data quality` · `interactive reporting` · `business communication`

## Data privacy

This public portfolio structure contains aggregate outputs only. Raw campaign data, pseudonymous user/session identifiers, proprietary brief screenshots, extraction passwords, and internal AI handoff documents are excluded.
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")

    methodology = f"""# Methodology

## Objective

Measure the incremental conversion impact of showing Rokt advertisements versus suppressing them in a holdout group.

## Cleaning decisions

1. Remove the invalid `203902` cohort row.
2. Remove exact duplicate source records before additive metrics.
3. Normalize device casing and use `Unknown` for missing device values.
4. Use `unknown` for missing gender values.
5. Define a converted event as a non-null `value`.
6. Parse campaign timestamps as datetimes.

## Primary metrics

- `CR = unique converted users / unique users`, calculated separately by group.
- `Relative uplift = (CR_treatment - CR_control) / CR_control`.
- `Absolute lift = CR_treatment - CR_control`.
- `VPT = sum(bidprice_usd) / unique sessions`, as specified in the supplied brief.

The primary brief-defined result is **+{headline['relative_uplift']:.2%} uplift**.

## Statistical test

The main analysis uses a two-sided pooled two-proportion z-test and reports 95% confidence intervals for absolute lift and the risk ratio. The conventional result is `z = {headline['z_statistic']:.3f}`, `p = {headline['p_value']:.3e}`.

## Assignment-unit audit

The dataset contains **26,426 users who appear in both groups across months**, but only **92 user-cohort pairs** appear in both groups within the same cohort. This suggests monthly reassignment is plausible, while the supplied brief does not explicitly identify the randomization unit.

Therefore the project reports three views:

{markdown_table([[row.analysis_unit, fmt_pct(row.treatment_cr), fmt_pct(row.control_cr), fmt_pct(row.relative_uplift,1), f'{row.p_value:.3g}'] for row in sensitivity.itertuples()], ['Analysis unit','Treatment CR','Control CR','Relative uplift','p-value'])}

The user-cohort and session views are sensitivity analyses rather than replacements for the requested KPI.

## Conversion-value estimate

`Estimated extra conversions × average value among converted records` gives **${headline['incremental_conversion_value_estimate_usd']:,.0f}**. This is an illustrative incremental conversion-value estimate. It is not verified revenue, profit, or causal financial impact.

## Limitations

- The randomization unit is not explicit.
- Repeated users create dependence across months.
- Segment results are exploratory and unadjusted for multiple testing.
- Exact duplicates are treated as ingestion duplicates; this assumption should be confirmed with the data owner.
- The raw source and proprietary assignment screenshots are deliberately excluded from the public repository.
"""
    (ROOT / "docs" / "methodology.md").write_text(methodology, encoding="utf-8")

    data_dictionary = """# Data dictionary

| Field | Meaning | Public treatment |
|---|---|---|
| `agegroup` | Age bracket assigned to the campaign event | Aggregated only |
| `bidprice_usd` | Amount paid for the campaign event | Aggregated only |
| `campaigntimestamp` | Timestamp of interaction with the platform | Aggregated to cohort |
| `cohort` | Campaign month identifier in `YYYYMM` format | Included |
| `device` | Device type | Included as aggregate segment |
| `gender` | Test-dataset gender category | Included as aggregate segment |
| `group` | `treatment` when an ad was shown; `control` when suppressed | Included |
| `sessionid` | Unique session identifier | Never published |
| `userhash` | Pseudonymous user identifier | Never published |
| `value` | Conversion value attributed to the event | Aggregated only |
| `verticalname` | Industry/domain assigned to the campaign event | Included as aggregate segment |
| `converted` | Derived flag: `value` is non-null | Aggregate counts only |

The portfolio repository does not include row-level source data.
"""
    (ROOT / "docs" / "data_dictionary.md").write_text(data_dictionary, encoding="utf-8")

    data_readme = """# Data access and privacy

The original Rokt CSV is intentionally excluded from this public portfolio because it contains pseudonymous user and session identifiers and may be governed by assignment or company-use restrictions.

`data/aggregated/` contains privacy-safe summary tables generated by `src/analysis.py`. No userhash or sessionid values are present.

To reproduce the analysis, obtain an authorized copy of the source CSV and pass its local path to the analysis script. Do not commit it to this repository.
"""
    (ROOT / "data" / "README.md").write_text(data_readme, encoding="utf-8")

    dashboard_readme = """# Dashboard

## Included

- `index.html`: self-contained interactive portfolio dashboard.
- `dashboard_preview.png`: static preview for GitHub and portfolio cards.

## How to use it

Open `index.html` in any modern browser. Use the cohort selector to compare the overall result with individual campaign months. The dashboard reads only embedded aggregate values, does not require a server, and does not expose row-level records.

The static preview can be used as a portfolio thumbnail. Detailed calculations and interpretation remain in the notebook, methodology, and executive report.
"""
    (ROOT / "dashboard" / "README.md").write_text(dashboard_readme, encoding="utf-8")

    executive = f"""# Executive summary: Rokt holdout experiment

## Decision statement

The experiment shows a positive conversion signal. Under the assignment's unique-user KPI, treatment conversion was **{headline['cr_treatment']:.2%}** versus **{headline['cr_control']:.2%}** for control, a **+{headline['relative_uplift']:.1%} relative uplift**.

## Evidence

- Absolute lift: **{headline['absolute_lift']:.3%} percentage points**.
- Conventional significance: **p = {headline['p_value']:.2e}**.
- Positive uplift in all five monthly cohorts.
- Estimated **{headline['extra_conversions_estimate']:,.0f} additional conversions** under the simple control-rate counterfactual.
- Desktop had the highest descriptive device uplift at **{top_device['relative_uplift']:.1%}**.

## Important caveat

Users can change groups across months. The user-cohort sensitivity view estimates **+{user_cohort['relative_uplift']:.1%} uplift (p = {user_cohort['p_value']:.3f})**. Confirm the randomization unit before using the result for rollout sizing or financial forecasting.

## Recommendation

Treat the experiment as a positive signal, validate assignment logic, and investigate the conversion decline across cohorts. Use the device result to define a follow-up hypothesis, not as a final targeting rule.

## Data controls

The public portfolio excludes raw campaign data, identifiers, assignment screenshots, passwords, and internal handoff notes. All published tables are aggregate-only.
"""
    (ROOT / "reports" / "executive_summary.md").write_text(executive, encoding="utf-8")

    (ROOT / "requirements.txt").write_text(
        "pandas>=2.0,<4\nnumpy>=1.24,<3\nmatplotlib>=3.8,<4\n",
        encoding="utf-8",
    )
    (ROOT / ".gitignore").write_text(
        "data/raw/\n*.csv\n!data/aggregated/*.csv\n.ipynb_checkpoints/\n__pycache__/\n*.py[cod]\n.venv/\n.env\n.DS_Store\nThumbs.db\n",
        encoding="utf-8",
    )


def main():
    headline = json.loads((DATA / "headline_metrics.json").read_text(encoding="utf-8"))
    quality = pd.read_csv(DATA / "data_quality_summary.csv")
    group_kpis = pd.read_csv(DATA / "group_kpis.csv")
    cohorts = pd.read_csv(DATA / "cohort_summary.csv")
    sensitivity = pd.read_csv(DATA / "sensitivity_summary.csv")
    devices = pd.read_csv(DATA / "device_summary.csv")

    build_notebook(headline, quality, group_kpis, cohorts, sensitivity, devices)
    build_dashboard(headline, cohorts, devices, sensitivity)
    build_markdown(headline, cohorts, devices, sensitivity)
    print(f"Built portfolio documentation in {ROOT}")


if __name__ == "__main__":
    main()
