# Executive summary: Rokt holdout experiment

## Decision statement

The experiment shows a positive conversion signal. Under the assignment's unique-user KPI, treatment conversion was **2.23%** versus **1.95%** for control, a **+13.9% relative uplift**.

## Evidence

- Absolute lift: **0.272 percentage points**.
- Conventional significance: **p = 3.42e-09**.
- Positive uplift in all five monthly cohorts.
- Estimated **1,569 additional conversions** under the simple control-rate counterfactual.
- Desktop had the highest descriptive device uplift at **29.1%**.

## Important caveat

Users can change groups across months. The user-cohort sensitivity view estimates **+5.5% uplift (p = 0.016)**. Confirm the randomization unit before using the result for rollout sizing or financial forecasting.

## Recommendation

Treat the experiment as a positive signal, validate assignment logic, and investigate the conversion decline across cohorts. Use the device result to define a follow-up hypothesis, not as a final targeting rule.

## Data controls

The public portfolio excludes raw campaign data, identifiers, assignment screenshots, passwords, and internal handoff notes. All published tables are aggregate-only.

## Inference boundary

The reported significance uses a conventional independence assumption that the assignment audit leaves unresolved. Sensitivity views are not a substitute for confirming assignment and dependence. The financial estimate remains illustrative; no realized revenue or profit is demonstrated.
