# Rokt A/B Test — Project Guide

## Quick Reference

| Metric | Treatment | Control | Uplift |
|--------|-----------|---------|--------|
| Unique Users | 576,472 | 121,750 | — |
| Converted Users | 12,833 | 2,379 | — |
| Conversion Rate | 2.2261% | 1.9540% | +13.9% |
| Unique Sessions | 647,058 | 126,605 | — |
| VPT | $0.0796 | $0.0000 | — |

## Files

- `rokt_data.csv` — cleaned copy of raw CSV (889,091 rows × 11 columns)
- `raw_data/` — original extracted files + test description images

## Data Cleaning Checklist

- [ ] Normalize device casing (`mobile` → `Mobile`)
- [ ] Handle empty device (122 rows) → "Unknown"
- [ ] Handle empty gender (90,630 rows) → "unknown"
- [ ] Remove invalid cohort `203902` (1 row)
- [ ] Create `converted` boolean column (non-empty `value`)
- [ ] Parse `campaigntimestamp` as datetime

## Key Formulas

**CR** = Unique Converted Users / Unique Users (per group)
**Uplift** = (CR_T - CR_C) / CR_C
**VPT** = sum(bidprice_usd) / count(unique sessionid) ← NOT the value column!

## 6 Tasks

1. Load & clean data
2. Overall CR, VPT, Uplift
3. Same metrics per cohort (202002–202006)
4. Positive or negative impact? (interpret results)
5. Statistical confidence (z-test for proportions, p < 0.05)
6. Additional insights (segment by device/age/vertical/gender)

## Cohorts

| Cohort | Rows |
|--------|------|
| 202002 | 115,940 |
| 202003 | 93,444 |
| 202004 | 162,761 |
| 202005 | 214,188 |
| 202006 | 302,757 |
