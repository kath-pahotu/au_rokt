# Methodology

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

The primary brief-defined result is **+13.93% uplift**.

## Statistical test

The main analysis uses a two-sided pooled two-proportion z-test and reports 95% confidence intervals for absolute lift and the risk ratio. The conventional result is `z = 5.910`, `p = 3.422e-09`.

## Assignment-unit audit

The dataset contains **26,426 users who appear in both groups across months**, but only **92 user-cohort pairs** appear in both groups within the same cohort. This suggests monthly reassignment is plausible, while the supplied brief does not explicitly identify the randomization unit.

Therefore the project reports three views:

| Analysis unit | Treatment CR | Control CR | Relative uplift | p-value |
|---|---|---|---|---|
| Brief-defined unique users | 2.23% | 1.95% | 13.9% | 3.42e-09 |
| User-cohort | 1.99% | 1.89% | 5.5% | 0.0162 |
| Session | 1.98% | 1.88% | 5.6% | 0.0142 |

The user-cohort and session views are sensitivity analyses rather than replacements for the requested KPI.

## Conversion-value estimate

`Estimated extra conversions × average value among converted records` gives **$239,887**. This is an illustrative incremental conversion-value estimate. It is not verified revenue, profit, or causal financial impact.

## Limitations

- The randomization unit is not explicit.
- Repeated users create dependence across months.
- Segment results are exploratory and unadjusted for multiple testing.
- Exact duplicates are treated as ingestion duplicates; this assumption should be confirmed with the data owner.
- The raw source and proprietary assignment screenshots are deliberately excluded from the public repository.

## What the intervals assume

The published intervals and p-values are conventional two-proportion calculations under independent group observations. Cross-group user overlap and repeated users across months can violate that assumption. The user-cohort and session views test the metric definition; they are not a cluster-adjusted analysis and do not establish independent assignment.

The decision-changing check is the original assignment and reassignment policy, followed by confirmation that exact duplicate rows are ingestion duplicates rather than legitimate repeated events. Until those are verified, keep the positive direction as a provisional signal and do not use the conventional interval or illustrative conversion value as a rollout guarantee. No cluster-adjusted inference or new experiment is claimed here.
