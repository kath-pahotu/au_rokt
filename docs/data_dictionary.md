# Data dictionary

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
