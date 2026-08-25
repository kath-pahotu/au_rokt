"""Portfolio release checks: reproducibility, privacy, links, and metric reconciliation."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def main():
    required = [
        "README.md",
        "requirements.txt",
        "src/analysis.py",
        "notebooks/rokt_ab_test_analysis.ipynb",
        "dashboard/index.html",
        "dashboard/dashboard_preview.png",
        "reports/executive_summary.pdf",
        "docs/methodology.md",
        "docs/data_dictionary.md",
        "data/aggregated/headline_metrics.json",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    if missing:
        raise AssertionError(f"Missing required files: {missing}")

    notebook = json.loads((ROOT / "notebooks" / "rokt_ab_test_analysis.ipynb").read_text(encoding="utf-8"))
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), f"notebook-cell-{index}", "exec")

    text_suffixes = {".md", ".py", ".html", ".json", ".txt"}
    forbidden = [re.compile(r"ghp_[A-Za-z0-9]+"), re.compile(r"C:\\Users\\", re.I)]
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in text_suffixes:
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden:
                if pattern.search(text):
                    raise AssertionError(f"Forbidden private value in {path.relative_to(ROOT)}")

    for csv_path in (ROOT / "data" / "aggregated").glob("*.csv"):
        columns = {column.lower() for column in pd.read_csv(csv_path, nrows=1).columns}
        if {"userhash", "sessionid"} & columns:
            raise AssertionError(f"Identifier column found in {csv_path.name}")

    raw_csvs = [
        path
        for path in ROOT.rglob("*.csv")
        if "data\\aggregated" not in str(path.parent).replace("/", "\\")
    ]
    if raw_csvs:
        raise AssertionError(f"Unexpected CSV files: {raw_csvs}")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    linked_paths = re.findall(r"!?(?:\[[^\]]*\])\(([^)]+)\)", readme)
    missing_links = [link for link in linked_paths if not link.startswith("http") and not (ROOT / link).exists()]
    if missing_links:
        raise AssertionError(f"Broken README links: {missing_links}")

    headline = json.loads((ROOT / "data" / "aggregated" / "headline_metrics.json").read_text(encoding="utf-8"))
    groups = pd.read_csv(ROOT / "data" / "aggregated" / "group_kpis.csv").set_index("group")
    assert abs(headline["cr_treatment"] - groups.loc["treatment", "conversion_rate"]) < 1e-12
    assert abs(headline["cr_control"] - groups.loc["control", "conversion_rate"]) < 1e-12

    oversized = [
        (path.relative_to(ROOT), path.stat().st_size)
        for path in ROOT.rglob("*")
        if path.is_file() and path.stat().st_size > 50 * 1024 * 1024
    ]
    if oversized:
        raise AssertionError(f"Unexpected oversized public files: {oversized}")

    print(
        json.dumps(
            {
                "status": "PASS",
                "files": sum(1 for path in ROOT.rglob("*") if path.is_file()),
                "notebook_cells": len(notebook["cells"]),
                "readme_links_checked": len(linked_paths),
                "aggregate_csvs": len(list((ROOT / "data" / "aggregated").glob("*.csv"))),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
