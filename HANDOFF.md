# Rokt A/B Test — Project Handoff

> **For the next Claude:** This document is a full context transfer. The user is doing a data science take-home test and moving between computers. Read this top-to-bottom, then continue helping from **Step 6 / Task 4 onward**. The user is a **beginner in Python and statistics** — explain concepts and syntax clearly, not just code. They prefer line-by-line explanation of what each step does and why.

---

## 1. What this project is

A **data science take-home test for Rokt** (an ad-tech company). Rokt shows personalized ads during e-commerce checkout. They ran a **holdout A/B experiment** to measure whether their ads actually drive conversions.

- **Treatment group** (~85% of users): saw Rokt ads normally.
- **Control group** (~15% of users): ads were **suppressed** (should have seen ads, didn't).
- Comparing the two isolates the ad's true incremental effect.
- Experiment ran **Feb 2020 – Jun 2020** (5 monthly cohorts).

Time budget stated in brief: 2–4 hours. Deliverable: a notebook, zipped, presented at interview.

### The 6 required tasks
1. Download, load, **clean** the dataset.
2. Calculate overall **Conversion Rate (CR)**, **Value Per Transaction (VPT)**, **Uplift**.
3. Same metrics **per cohort**.
4. Positive or negative impact? (CR as primary metric)
5. How **confident** are we? (statistical significance)
6. Any **other metrics/insights** showing impact?

---

## 2. Project folder layout

```
C:\Users\Khanh\project_Thu\au_rokt\
├── notebook.ipynb          # THE main working notebook (Python 3.13 kernel)
├── rokt_data.csv           # clean copy of the data (also in raw_data/)
├── GUIDE.md                # quick-reference: metrics, formulas, checklist
├── HANDOFF.md              # THIS file
└── raw_data/
    └── [AU] Rokt /         # NOTE: trailing space in folder name
        ├── rokt_hKllMfFFdA.csv    # original data (889,091 rows)
        ├── Test_description_01.jpg # brief page 1 (task list + columns)
        └── Test_description_02.jpg # brief page 2 (columns + formulas)
```

**Environment:** VS Code + Jupyter. Kernel = **Python 3.13.0** (Global Env at `~\AppData\Local\Programs\Python\Python313\`). Libraries installed via `%pip install pandas numpy scipy statsmodels matplotlib seaborn`. If on a new machine, re-run that install once.

---

## 3. The data — dictionary & key facts

**889,091 rows × 11 columns.** One row = one campaign event. Users/sessions have multiple rows.

| Column | Meaning |
|--------|---------|
| `agegroup` | Age bracket string (18-25, 26-30, ... 65+) |
| `bidprice_usd` | What the advertiser paid Rokt for the ad **engagement** event |
| `campaigntimestamp` | When user interacted with Rokt |
| `cohort` | Month id YYYYMM (derived from timestamp) |
| `device` | Mobile / Desktop / Tablet / Other |
| `gender` | m / f / blank |
| `group` | **treatment** (saw ad) or **control** (ad suppressed) |
| `sessionid` | Unique session id (events in same session share it) |
| `userhash` | Unique user id (hashed) |
| `value` | Purchase/conversion value. **Empty = no conversion.** |
| `verticalname` | Industry of the ad (Media & Ent, Retail, etc.) |

### Verified numbers (use to validate calculations)
| Metric | Treatment | Control |
|--------|-----------|---------|
| Unique users | 576,472 | 121,750 |
| Converted users | 12,833 | 2,379 |
| **Conversion Rate** | **2.2261%** | **1.9540%** |
| Unique sessions | 647,058 | 126,605 |
| Sum bidprice_usd | $51,496.11 | $0.00 |
| **VPT** | **$0.0796** | **$0.0000** |

- **CR Uplift = (CR_T − CR_C) / CR_C ≈ +13.9%**
- Converted rows overall: ~15,935. Non-zero bidprice rows: 66,519.
- Control bidprice = $0 everywhere (ads suppressed → no bids).

### Data quality issues (all handled in cleaning, Step 4)
1. **Device casing**: `mobile` (110,537) vs `Mobile` (470,187) → normalize with `.str.title()`.
2. **Empty device**: 122 rows → "Unknown".
3. **Empty gender**: 90,630 rows (~10%) → "unknown" (don't drop, too many).
4. **Invalid cohort**: 1 row = `203902` (year 2039) → drop it.
5. **85/15 split**: not a bug, normal for holdout tests.
6. **Control bidprice = 0**: expected, not a bug.

---

## 4. Key formulas (from the brief)

```
CR_treatment = unique converted users (treatment) / unique users (treatment)
CR_control   = unique converted users (control)   / unique users (control)
Uplift       = (CR_T − CR_C) / CR_C
VPT          = sum(bidprice_usd) / count(unique sessionid)      ← per group
```

**CRITICAL GOTCHA:** VPT uses **`bidprice_usd`**, NOT the `value` column. Both look monetary — easy to confuse. `bidprice_usd` = advertiser's payment to Rokt. `value` = shopper's purchase amount. Different things.

---

## 5. Two conceptual questions the user asked (both resolved)

### Q: Why does control have conversions (`conv_c > 0`) if they saw no ad?
**A (confirmed correct):** Control users still convert **naturally** — organic traffic, brand awareness, direct visits, other channels. Control measures the **baseline** conversion that happens WITHOUT the ad. Treatment measures conversion WITH the ad. The **difference (uplift)** is the incremental effect attributable to Rokt. You do NOT credit all of treatment's 2.23% to the ad — only the gap above control's 1.95%. This is the entire point of a holdout control group.

### Q: Why are there rows with `bidprice_usd > 0` but `value = NaN`?
**A:** They track **two different events**. `bidprice_usd > 0` = user **engaged** with the ad (advertiser charged). `value = NaN` = user did **not** complete a tracked purchase. A user can click an offer without buying. Ad engagement ≠ purchase conversion.

### Q: What's the actual flow — when does the ad appear, and what does "conversion" mean for a control user who never saw an ad?

**A: Rokt ads appear on the confirmation page, right AFTER a first purchase.**

```
User buys a flight on Expedia
   │
   ▼
Hits "Confirm Purchase" → payment done
   │
   ▼
Confirmation page loads ("Thanks for your order!")
   │
   ▼
  ← Rokt places an ad HERE (e.g. "Get 3 months of Audible free")
   │
   ▼
User clicks the offer + signs up → THIS is the tracked conversion
```

**The 1st purchase (the flight) is NOT the conversion being measured.** It's just the trigger that puts the user on a confirmation page where Rokt can act. The conversion Rokt tracks is whether the user takes the **advertiser's offer** shown to them (or assigned to them).

**Key mechanic: Rokt decides the offer for EVERY user before checking treatment/control.**

```
User finishes 1st purchase → confirmation page
   │
   ▼
Rokt system: "This user qualifies for the Audible offer"   ← decided for EVERYONE
   │
   ├── TREATMENT → actually displays the Audible ad
   └── CONTROL   → offer assigned, but NOT displayed (suppressed)
```

So a control user still has a **designated offer** sitting in the system — they just never see it rendered on screen. Proof in the data: every row, treatment AND control, has a `verticalname` (Ticketing, Media & Entertainment, etc.) — that's the industry of the assigned offer, present even for control rows.

**Conversion for control = did they take that SAME assigned offer anyway, through any other channel** (TV ad, Google search, direct visit, brand loyalty, already a customer):

```
CONTROL user assigned the Audible offer (not shown)
   │
   ▼
Do they sign up for Audible anyway via some other channel?
   │
   ├── Yes → value filled in → counts as conversion (organic)
   └── No  → value empty → no conversion
```

**Side-by-side:**

| | Assigned offer | Ad displayed? | What's measured |
|---|---|---|---|
| Treatment | Audible | ✅ Yes | Took Audible (organic + ad-driven combined) |
| Control | Audible | ❌ Suppressed | Took Audible anyway (organic only — the baseline) |

**Why this makes it a clean experiment:** offer assignment happens *before* the treatment/control split, so both groups are statistically identical in which offer they'd get. The *only* systematic difference is whether the ad was displayed. So any gap in conversion rate between groups is attributable to the ad, not to different offers or different users.

**Caveat to carry forward:** the dataset schema doesn't spell out this exact mechanism — the brief only says `value` = "conversion value attributed to the event." The flow above is the standard Rokt business model (ads on post-purchase confirmation pages) and is consistent with everything observable in the data (verticalname present on all rows, control conversions being nonzero but lower than treatment). Treat it as the explanatory model, not a literal engineering spec.

---

## 6. Notebook state — DONE so far (Steps 1–6 built)

The notebook has 21 cells. Some steps have a "#Retype" duplicate cell where the user re-typed the code themselves to practice — that's intentional, leave them.

| Cells | Step | Status |
|-------|------|--------|
| 0–1 | Install libraries | Done |
| 2–4 | **Step 1**: imports (pandas, numpy, scipy, statsmodels, matplotlib, seaborn) + display settings | Done |
| 5–7 | **Step 2**: load CSV, check shape/dtypes/nulls | Done |
| 8–10 | Extra: inspect bidprice > 0 vs = 0 rows (user's own exploration) | Done |
| 11–12 | **Step 3**: explore unique values before cleaning | Done |
| 13–15 | **Step 4**: clean the 6 issues, create `converted` flag, parse timestamp | Done |
| 16–17 | **Step 5**: validate cleaning worked | Done |
| 18–19 | **Step 6**: `calc_cr()` and `calc_vpt()` functions, overall CR/VPT/Uplift | Done |
| 20 | (empty) | Next work goes here |

**Cleaning code in place (cell 14):** device title-case, empty device→Unknown, empty gender→unknown, drop cohort 203902, `df['converted'] = df['value'].notna() & (df['value'] != '')`, `pd.to_datetime`.

**Step 6 functions in place (cell 19):**
```python
def calc_cr(group_df):
    users = group_df['userhash'].nunique()
    converted = group_df[group_df['converted']]['userhash'].nunique()
    return converted/users, converted, users

def calc_vpt(group_df):
    bid_sum = group_df['bidprice_usd'].sum()
    sessions = group_df['sessionid'].nunique()
    return bid_sum / sessions
```
`cr_t, conv_t, users_t`, `cr_c, conv_c, users_c`, `uplift`, `vpt_t`, `vpt_c` are all computed and available for reuse downstream.

---

## 7. TODO — remaining work (Steps 7 onward / Tasks 3–6)

Continue from cell 20. Recommended order:

### Step 7 — Per-cohort metrics (Task 3)
Loop over `sorted(df['cohort'].unique())` × `['treatment','control']`, call `calc_cr`/`calc_vpt` on each subset, collect into a list of dicts → `pd.DataFrame` → `.pivot(index='cohort', columns='group', values='cr')`, add uplift column. Then line chart (CR over time) + bar chart (uplift by cohort).

### Task 4 — Impact verdict
CR_T (2.23%) > CR_C (1.95%) → **POSITIVE**. Add a markdown cell explaining in business terms: ~14% relative lift. Show absolute diff (~0.27pp) and relative uplift.

### Task 5 — Statistical significance (z-test for proportions) ← NEW STAT, EXPLAIN CAREFULLY
```python
from statsmodels.stats.proportion import proportions_ztest
count = [conv_t, conv_c]     # converted users
nobs  = [users_t, users_c]   # total users
z_stat, p_value = proportions_ztest(count, nobs)
```
- H0: CR_T = CR_C (no difference). H1: they differ.
- p < 0.05 → significant → reject H0 → uplift is real.
- Expected: p ≈ 0 (very significant). Also run per-cohort to show robustness.
- **Explain the concept first** — user is new to hypothesis testing. p-value = probability of seeing this gap by chance if there were truly no difference.

### Task 6 — Additional insights
- CR + uplift by **device** (`groupby(['device','group'])` + lambda for CR, `.unstack()`).
- Repeat for **agegroup**, **verticalname**, **gender**.
- Bar chart of uplift by segment.
- **Revenue impact estimate**: `extra_conversions = conv_t − (users_t * cr_c)`; `avg_value = df[df['converted']]['value'].astype(float).mean()`; `extra_revenue = extra_conversions * avg_value`. (Note `value` may be text — needs `.astype(float)`.)

### Final polish
- Markdown headers before each task, 1–2 sentence conclusions under each result.
- Titles + axis labels on every chart.
- **Kernel → Restart & Run All** to confirm top-to-bottom reproducibility.
- Export `File → Download as → HTML`. Zip `.ipynb` + `.html` for submission.

---

## 8. How to work with this user
- Beginner in Python + stats. **Explain syntax line by line** and the *why*, not just working code.
- They practice by re-typing code (the "#Retype" cells) — encourage this.
- They like visual reference guides. Prior Claude built HTML artifact walkthroughs of the code — you can continue giving clear inline explanations.
- Caveman terse style is a session hook on the user's machine — don't be thrown by it. Match whatever their current setup does; substance matters more than tone.
- Confirm understanding of stats concepts before moving on.

---

## 9. Reference artifacts already produced (previous sessions, view-only)
The prior Claude published 3 HTML guide artifacts (requirements breakdown, Steps 1–7 line-by-line, Tasks 4–6 line-by-line). These live on claude.ai and aren't in the zip. The essential content from them is captured in this HANDOFF.md and GUIDE.md, so you don't need them — but if the user references "the guide artifact," that's what they mean.

---

*End of handoff. Next action: open `notebook.ipynb`, confirm cells 1–19 ran clean, then build Step 7 (cohort metrics) in cell 20.*
