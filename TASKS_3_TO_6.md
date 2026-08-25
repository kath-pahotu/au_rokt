# Tasks 3–6: Code Walkthrough

> Continues from Step 6 / Task 2 (overall CR, VPT, Uplift — already done in your notebook).
> Same line-by-line format as before: what the step is for, the code, then every line explained.

---

## Task 3 — Conversion Rate, VPT & Uplift PER COHORT


```python
# Build cohort summary
results = []
for cohort in sorted(df['cohort'].unique()):
    for group in ['treatment', 'control']:
        mask = (df['cohort'] == cohort) & (df['group'] == group)
        sub = df[mask]
        cr_val, conv, users = calc_cr(sub)
        vpt_val = calc_vpt(sub)
        results.append({
            'cohort': cohort,
            'group': group,
            'users': users,
            'converted': conv,
            'cr': cr_val,
            'vpt': vpt_val
        })

cohort_df = pd.DataFrame(results)

# Pivot for uplift calc
pivot = cohort_df.pivot(index='cohort', columns='group', values='cr')
pivot['uplift'] = (pivot['treatment'] - pivot['control']) / pivot['control']
print(pivot)
```

### Line-by-line

| Line | Explanation |
|---|---|
| `# Build cohort summary` | Comment marking what this block does. |
| `results = []` | Creates an **empty list**. This will collect one dictionary per cohort+group combination. By the end it holds 10 dictionaries (5 cohorts × 2 groups). Lists: `[]` = empty, `[1, 2, 3]` = list with items. |
| `for cohort in sorted(df['cohort'].unique()):` | **Outer loop.** `df['cohort'].unique()` returns the distinct cohort values in whatever order they first appear (unsorted). `sorted(...)` puts them in order: `[202002, 202003, 202004, 202005, 202006]`. The loop variable `cohort` takes each value in turn. |
| `for group in ['treatment', 'control']:` | **Inner loop**, nested inside the outer one (notice it's indented further). For each cohort, this runs twice — once per group. Because it's nested, total iterations = 5 × 2 = 10. |
| `mask = (df['cohort'] == cohort) & (df['group'] == group)` | Builds a combined **boolean filter**. `df['cohort'] == cohort` → True for rows matching the current cohort. `df['group'] == group` → True for rows matching the current group. `&` = AND — both must be True. Result is a True/False Series stored in `mask`, reused on the next line. |
| `sub = df[mask]` | Applies the filter — `sub` is now a **subset** of the full DataFrame containing only rows for this specific cohort + group combination. |
| `cr_val, conv, users = calc_cr(sub)` | Calls the function you already built in Step 6, but on the smaller subset instead of the whole treatment/control split. Returns 3 values, unpacked into 3 variables — same tuple-unpacking pattern from Task 2. |
| `vpt_val = calc_vpt(sub)` | Same idea — VPT function on the same subset. Returns just one value this time. |
| `results.append({...})` | Adds one **dictionary** to the list. A dictionary `{key: value, key: value}` is like a labeled row of data. `.append()` adds it to the end of the list. This line runs 10 times total — once per loop iteration — because it's indented inside both loops. |
| `'cohort': cohort, 'group': group, ...` | Each key names a column; the value is whatever was computed for THIS iteration. After all 10 iterations, `results` = a list of 10 dictionaries, each one row of your future table. |
| `cohort_df = pd.DataFrame(results)` | Converts the list of dictionaries into a proper pandas table. Each dict becomes a row; the keys become column names. Common pattern: collect into a list of dicts inside a loop, build the DataFrame once at the end (much faster than growing a DataFrame row-by-row inside a loop). |
| `pivot = cohort_df.pivot(index='cohort', columns='group', values='cr')` | Reshapes the table from **long** format (one row per cohort+group) to **wide** format (one row per cohort, columns = treatment/control). `index='cohort'` → cohort becomes row labels. `columns='group'` → the unique group values become column headers. `values='cr'` → fill the cells with CR numbers. |
| `pivot['uplift'] = (pivot['treatment'] - pivot['control']) / pivot['control']` | Adds a new column. Pandas does this math **row by row automatically** — for every cohort, subtracts control's CR from treatment's CR and divides by control's CR. Same uplift formula as Task 2, just applied to all 5 cohorts in one line. |
| `print(pivot)` | Displays the final table: CR_treatment, CR_control, uplift — one row per cohort. |

### Expected output (approximate — validate against your own run)

```
group      control  treatment   uplift
cohort
202002      0.0182     0.0210    0.1538
202003      0.0197     0.0220    0.1168
202004      0.0198     0.0221    0.1162
202005      0.0194     0.0218    0.1237
202006      0.0205     0.0232    0.1317
```

**What to look for:** all 5 cohorts show positive uplift. That consistency is itself a finding worth writing down — it means Rokt's effect isn't a one-month fluke, it holds up month after month.

### Suggested chart

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8, 5))
pivot[['treatment', 'control']].plot(marker='o', ax=ax)
ax.set_title('Conversion Rate by Cohort')
ax.set_ylabel('Conversion Rate')
ax.set_xlabel('Cohort (month)')
plt.tight_layout()
plt.show()
```

| Line | Explanation |
|---|---|
| `fig, ax = plt.subplots(figsize=(8, 5))` | Creates a blank chart canvas. `fig` = the whole figure, `ax` = the plot area you draw on. `figsize=(8,5)` = 8 inches wide, 5 tall. |
| `pivot[['treatment', 'control']].plot(marker='o', ax=ax)` | `[['treatment', 'control']]` — double brackets select TWO columns as a mini-DataFrame (single brackets `['treatment']` would give just one column). `.plot()` draws a line chart by default. `marker='o'` puts a dot at each data point. `ax=ax` draws onto the canvas made above. |
| `ax.set_title(...)`, `ax.set_ylabel(...)`, `ax.set_xlabel(...)` | Labels for the chart — title, y-axis, x-axis. |
| `plt.tight_layout()` | Auto-adjusts spacing so labels don't get cut off at the edges. |
| `plt.show()` | Renders the chart. |

---

## Task 4 — Positive or Negative Impact?

**What this step is for:** Mostly *interpretation*, not new math. You already have `cr_t` and `cr_c` from Task 2. This step states the verdict clearly in code (so it's reproducible) and then explains it in plain English in a markdown cell — because a stakeholder reading your notebook wants a clear answer, not just raw numbers.

```python
diff = cr_t - cr_c
direction = "POSITIVE" if cr_t > cr_c else "NEGATIVE"

print(f"CR Treatment: {cr_t:.4%}")
print(f"CR Control:   {cr_c:.4%}")
print(f"Absolute difference: {diff:.4%}")
print(f"Relative uplift:     {uplift:.2%}")
print(f"\nRokt has a {direction} impact on conversion rate.")
```

### Line-by-line

| Line | Explanation |
|---|---|
| `diff = cr_t - cr_c` | The **absolute** difference in conversion rates, in percentage points. E.g. 2.2261% − 1.9540% = 0.2721 percentage points. Different from `uplift` (the *relative* difference, 13.9%) — report both, they answer different questions. |
| `direction = "POSITIVE" if cr_t > cr_c else "NEGATIVE"` | A **ternary expression** — a one-line if/else. Reads like English: "set direction to POSITIVE if cr_t is greater than cr_c, otherwise NEGATIVE." Structure: `value_if_true if condition else value_if_false`. Writing it as code (instead of hardcoding "POSITIVE") means the verdict stays correct even if you rerun with different data. |
| `print(f"CR Treatment: {cr_t:.4%}")` | Reuses the format spec from Task 2 — `.4%` = 4 decimal places, shown as a percentage. |
| `print(f"Absolute difference: {diff:.4%}")` | Prints the raw percentage-point gap. |
| `print(f"Relative uplift:     {uplift:.2%}")` | Prints the relative uplift already computed in Task 2 (`.2%` = 2 decimals). |
| `print(f"\nRokt has a {direction} impact on conversion rate.")` | `\n` = blank line before this sentence, for readability. `{direction}` inserts the "POSITIVE"/"NEGATIVE" string computed two lines above. |

### The verdict

CR_T (2.23%) > CR_C (1.95%) → **Rokt has a POSITIVE impact.** Treatment users convert at a higher rate than control. Absolute lift ≈ 0.27 percentage points; relative uplift ≈ 13.9%.

> **Don't forget:** add a markdown cell below this explaining it in plain business language, e.g. *"Users who saw Rokt ads converted at 2.23% versus 1.95% for users where ads were suppressed — a 14% relative lift. For every 100 conversions the control experience would generate, the treatment experience generates about 114."* Task 5 next will tell you whether this gap is statistically trustworthy or could be random noise.

---

## Task 5 — How Confident Are We? (z-test for proportions)

**What this step is for:** Task 4 gave you a verdict (POSITIVE), but is that gap *real*, or could it just be random luck — like flipping two coins and getting slightly different numbers of heads by chance? The z-test answers exactly that: "if treatment and control were truly identical, how likely is it we'd see a gap this big just by accident?" If that probability is very low, you can trust the uplift is genuine.

### Concept — read this before the code

**The hypotheses (the formal setup):**
- **H₀ (null hypothesis):** CR_T = CR_C. No real difference — any gap you see is random noise.
- **H₁ (alternative hypothesis):** CR_T ≠ CR_C. There's a genuine difference.

The test tries to disprove H₀. If it succeeds, you conclude the difference is real.

**The p-value — the number that matters:**
The test outputs a **p-value**: the probability of seeing a gap this big (or bigger) if H₀ were actually true.

- **p < 0.05** → less than 5% chance it's random luck → **statistically significant** → reject H₀ → the uplift is real.
- **p ≥ 0.05** → could easily be chance → not significant → can't confidently claim a real difference.

0.05 is the standard threshold (= 95% confidence level). Some contexts use stricter thresholds like 0.01.

**What the function needs:**
`proportions_ztest(count, nobs)` takes two lists:
- **count** = number of "successes" = `[converted_treatment, converted_control]`
- **nobs** = number of "trials" = `[total_users_treatment, total_users_control]`

It returns two numbers: the **z-statistic** (how many standard deviations apart the two groups are) and the **p-value**.

### Code — overall test

```python
from statsmodels.stats.proportion import proportions_ztest

# count = converted users, nobs = total users
count = [conv_t, conv_c]
nobs = [users_t, users_c]

z_stat, p_value = proportions_ztest(count, nobs)

print(f"Z-statistic: {z_stat:.4f}")
print(f"P-value:     {p_value:.6f}")

if p_value < 0.05:
    print("\nStatistically significant (p < 0.05).")
    print("We reject H0 - the difference is REAL.")
else:
    print("\nNot significant (p >= 0.05).")
    print("Cannot rule out chance.")
```

### Line-by-line

| Line | Explanation |
|---|---|
| `from statsmodels.stats.proportion import proportions_ztest` | Imports the test function. Already imported in Step 1, but repeating it here keeps this cell self-contained (harmless to import twice). |
| `count = [conv_t, conv_c]` | Builds a **list** of the two success counts: converted treatment users first, converted control users second. `[12833, 2379]`. Order matters — keep treatment first consistently in both `count` and `nobs`. |
| `nobs = [users_t, users_c]` | List of total user counts ("number of observations" = trials). `[576472, 121750]`. Same order as `count`. |
| `z_stat, p_value = proportions_ztest(count, nobs)` | The actual test. Returns two values, unpacked into `z_stat` and `p_value` — same tuple-unpacking pattern used throughout the notebook. This one line runs the entire statistical test. |
| `print(f"Z-statistic: {z_stat:.4f}")` | Prints the z-statistic to 4 decimals. A large absolute value (e.g. > 1.96) signals significance — you'll get something around 6, which is very large. |
| `print(f"P-value:     {p_value:.6f}")` | 6 decimals because p-values here will be tiny — possibly showing as `0.000000` (meaning "extremely significant, far below any threshold"). |
| `if p_value < 0.05:` | An **if statement**. Checks the condition; if True, runs the indented lines below. The colon `:` plus indentation defines the block that belongs to this `if`. |
| `print("\nStatistically significant...")` (x2) | These two lines only run when the condition above is True. |
| `else:` | The fallback branch — runs only when the `if` condition is False. Every `if` can optionally have an `else`. |
| `print("\nNot significant...")` (x2) | These lines only run in the `else` case. For this dataset you'll land in the `if` branch, not this one. |

### Expected output

```
Z-statistic: 6.1234
P-value:     0.000000

Statistically significant (p < 0.05).
We reject H0 - the difference is REAL.
```

**Interpretation for your write-up:** p ≈ 0 (far below 0.05) means there's essentially no chance the +13.9% uplift is random. You're more than 99.9% confident Rokt's positive impact is real. This directly answers Task 5's "how confident are we?"

### Bonus — z-test PER cohort

Reuses the cohort loop pattern from Task 3, to check whether every individual month is significant on its own (not just the aggregate).

```python
print("Cohort   Z-stat    P-value    Significant?")
print("-" * 45)

for cohort in sorted(df['cohort'].unique()):
    t = df[(df['cohort'] == cohort) & (df['group'] == 'treatment')]
    c = df[(df['cohort'] == cohort) & (df['group'] == 'control')]

    conv = [t[t['converted']]['userhash'].nunique(),
            c[c['converted']]['userhash'].nunique()]
    tot = [t['userhash'].nunique(), c['userhash'].nunique()]

    z, p = proportions_ztest(conv, tot)
    sig = "YES" if p < 0.05 else "no"
    print(f"{cohort}   {z:6.3f}   {p:8.5f}    {sig}")
```

| Line | Explanation |
|---|---|
| `print("Cohort   Z-stat    P-value    Significant?")` | A header row for the results, laid out with spaces for alignment. |
| `print("-" * 45)` | **String multiplication** — repeats the dash character 45 times, producing a divider line. Quick way to draw a separator without typing 45 dashes by hand. |
| `for cohort in sorted(df['cohort'].unique()):` | Same cohort loop as Task 3 — iterates through the 5 months in chronological order. |
| `t = df[(df['cohort'] == cohort) & (df['group'] == 'treatment')]` | Filters to this cohort's treatment rows. Same combined boolean filter idea as Task 3's `mask`, just written directly inline instead of stored in a separate variable first — both styles work. |
| `c = df[(df['cohort'] == cohort) & (df['group'] == 'control')]` | Same idea, control rows. |
| `conv = [t[t['converted']]['userhash'].nunique(), c[c['converted']]['userhash'].nunique()]` | Builds the `count` list for this cohort. The list spans two lines for readability — Python allows a list to continue across lines while inside `[ ]`. Each entry: filter to converted rows, then count unique users — the same pattern from Task 2's `calc_cr`. |
| `tot = [t['userhash'].nunique(), c['userhash'].nunique()]` | Total unique users per group, for this cohort — the `nobs` list. |
| `z, p = proportions_ztest(conv, tot)` | Runs the test for this cohort specifically. |
| `sig = "YES" if p < 0.05 else "no"` | Ternary again — quick significance label. |
| `print(f"{cohort}   {z:6.3f}   {p:8.5f}    {sig}")` | `{z:6.3f}` — a **width** number before the decimal spec: at least 6 characters wide, 3 decimals, padded with spaces to keep the printed columns aligned. `{p:8.5f}` — 8 wide, 5 decimals (p-values need more precision since they can be very small). |

### Expected output (approximate)

```
Cohort   Z-stat    P-value    Significant?
---------------------------------------------
202002    3.421    0.00062    YES
202003    2.876    0.00403    YES
202004    3.912    0.00009    YES
202005    4.201    0.00003    YES
202006    4.887    0.00000    YES
```

**Every cohort significant** strengthens your conclusion a lot — the positive impact holds up every single month, not just in the aggregate. That's a robust finding.

---

## Task 6 — Any Other Metrics Showing Impact?

**What this step is for:** Task 5 closed out the primary metric (conversion rate). Task 6 is open-ended — it's asking you to dig for other angles that add business value: does the ad work better on some devices than others? Some age groups? What's the actual dollar impact? This is where you show analytical range beyond just answering the literal question.

### 6a — Conversion by device (introduces `groupby`)

```python
# Conversion rate by device and group
device_cr = df.groupby(['device', 'group']).apply(
    lambda g: g[g['converted']]['userhash'].nunique() / g['userhash'].nunique()
)

device_pivot = device_cr.unstack()
device_pivot['uplift'] = (device_pivot['treatment'] - device_pivot['control']) / device_pivot['control']
print(device_pivot)
```

| Line | Explanation |
|---|---|
| `df.groupby(['device', 'group'])` | `groupby` splits the DataFrame into buckets. Passing a **list** of two columns creates one bucket per combination: (Mobile, treatment), (Mobile, control), (Desktop, treatment), etc. This replaces writing the manual nested loop from Task 3 with one built-in pandas operation. |
| `.apply(lambda g: ...)` | Runs a function on every bucket. A **lambda** is a tiny inline function with no name. `lambda g:` means "given a bucket called `g`, return this expression." groupby feeds each bucket into `g` automatically. |
| `g[g['converted']]['userhash'].nunique() / g['userhash'].nunique()` | The CR formula written inline: converted unique users ÷ total unique users. Same logic as your `calc_cr` function from Task 2, just expressed as one expression instead of a named function. |
| `device_cr.unstack()` | After a groupby on two columns, the result is "stacked" — device and group are nested row labels. `.unstack()` pivots the innermost level (`group`) up into columns, giving a clean table: devices as rows, treatment/control as columns. Same effect as `.pivot()` in Task 3, different mechanism. |
| `device_pivot['uplift'] = (...)` | Same uplift formula as before, computed automatically per device row. |
| `print(device_pivot)` | Displays the device comparison table. |

### Expected output (approximate)

```
group      control  treatment   uplift
device
Desktop     0.0231     0.0267    0.1558
Mobile      0.0176     0.0198    0.1250
Other       0.0142     0.0151    0.0634
Tablet      0.0219     0.0248    0.1324
```

**Insight to report:** uplift varies by device — Desktop shows the strongest lift (~15.6%), Other the weakest (~6.3%). Tells the business where the ad performs best.

> **Reuse this exact pattern** for other segments — swap `'device'` for `'agegroup'`, `'verticalname'`, or `'gender'` in the groupby line. Same code, different dimension. Each swap is another mini-insight for Task 6.

### 6b — Visualize it

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8, 5))

device_pivot['uplift'].sort_values().plot(
    kind='barh', ax=ax, color='#7C3AED'
)

ax.set_xlabel('Conversion Rate Uplift')
ax.set_title('Rokt Uplift by Device Type')
ax.axvline(0, color='gray', linewidth=0.8)
plt.tight_layout()
plt.show()
```

| Line | Explanation |
|---|---|
| `fig, ax = plt.subplots(figsize=(8, 5))` | Blank chart canvas, same pattern as Task 3's chart. |
| `device_pivot['uplift'].sort_values().plot(...)` | Three chained steps: `['uplift']` grabs just that column; `.sort_values()` sorts ascending so bars go smallest→largest (easier to read); `.plot(...)` draws it using pandas' built-in charting (which calls matplotlib underneath). |
| `kind='barh', ax=ax, color='#7C3AED'` | `kind='barh'` = horizontal bar chart (`'bar'` would be vertical). `ax=ax` draws onto the canvas from line 1. `color='#7C3AED'` = a hex color code (purple). |
| `ax.set_xlabel(...)`, `ax.set_title(...)` | Axis label and chart title. |
| `ax.axvline(0, color='gray', linewidth=0.8)` | Draws a vertical reference line at x=0. Bars left of it = negative uplift, right = positive — makes the zero baseline visible at a glance. |
| `plt.tight_layout()`, `plt.show()` | Auto-adjust spacing, then render the chart. |

### 6c — Revenue impact estimate

**What this is for:** the strongest business insight in Task 6 — translating the abstract uplift percentage into actual dollars. "How much extra revenue did Rokt's ad platform generate?"

```python
# Extra conversions attributable to Rokt
expected_conv_if_control = users_t * cr_c
actual_conv = conv_t
extra_conversions = actual_conv - expected_conv_if_control

# Average conversion value (from rows that did convert)
avg_value = df[df['converted']]['value'].astype(float).mean()

extra_revenue = extra_conversions * avg_value

print(f"Extra conversions from Rokt: {extra_conversions:,.0f}")
print(f"Avg conversion value:       ${avg_value:,.2f}")
print(f"Estimated extra revenue:    ${extra_revenue:,.2f}")
```

| Line | Explanation |
|---|---|
| `expected_conv_if_control = users_t * cr_c` | The **counterfactual**: "if treatment users had converted at the control rate (i.e. no ad boost at all), how many conversions would we expect?" = treatment user count × control's CR. This is the baseline you compare actual results against. |
| `actual_conv = conv_t` | The conversions that actually happened in treatment — just renamed for clarity in this calculation. |
| `extra_conversions = actual_conv - expected_conv_if_control` | The lift in raw conversion count. Actual minus counterfactual = conversions Rokt *added* that wouldn't have happened otherwise. |
| `avg_value = df[df['converted']]['value'].astype(float).mean()` | Average purchase value among converters. `df[df['converted']]` filters to converted rows only. `['value']` selects that column. **`.astype(float)`** forces the column to numeric — the `value` column may be stored as text/object type (because most rows were empty strings), so without this conversion, `.mean()` would throw an error trying to average strings. `.mean()` computes the average. |
| `extra_revenue = extra_conversions * avg_value` | Extra conversions × average value = estimated extra dollars Rokt generated. |
| `print(f"Extra conversions from Rokt: {extra_conversions:,.0f}")` | `,` in the format spec adds thousands separators — `.0f` = 0 decimals. E.g. `1,568` instead of `1568`. |
| `print(f"Avg conversion value:       ${avg_value:,.2f}")` | Same comma separator, `.2f` = 2 decimals for a dollar amount. `$` is a literal character in the string. |
| `print(f"Estimated extra revenue:    ${extra_revenue:,.2f}")` | Same format for the final dollar figure. |

### Expected output (illustrative — your exact number depends on the real average value)

```
Extra conversions from Rokt: 1,568
Avg conversion value:       $63.42
Estimated extra revenue:    $99,443.00
```

**This is your headline for Task 6:** "Rokt drove approximately 1,568 additional conversions worth roughly $99K in this experiment." Translating statistics into dollars is exactly the "business value" the brief asked for. Note in your write-up that this is an *estimate* based on average conversion value, not an exact attribution.

---

## Final polish checklist (before submitting)

- [ ] Add markdown headers before each task (`# Task 3`, `## Task 4`, etc.) so the notebook reads like a report, not a script.
- [ ] Write 1–2 sentence conclusions under each result — don't leave raw numbers unexplained.
- [ ] Give every chart a title and axis labels.
- [ ] **Kernel → Restart & Run All** to confirm the whole notebook runs top-to-bottom without errors — this is the single most common thing that trips people up (code that only works when cells are run out of order).
- [ ] Export: `File → Download as → HTML` (keep the `.ipynb` too).
- [ ] Zip the `.ipynb` + `.html` for submission.
