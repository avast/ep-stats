# Outlier Winsorization

Some metrics are heavy-tailed: revenue, time spent, number of actions per user, etc. A handful of
extreme units (e.g. a single user who spends 1000× the typical amount) can dominate the per-variant
mean and, even more so, the variance. When such outliers are concentrated in one variant, the
[by-unit evaluation][epstats.toolkit.experiment.Experiment.evaluate_by_unit] of that metric becomes
unreliable — the test loses power and the estimated effect is distorted.

Ep-Stats can make the evaluation robust to these outliers by **winsorizing** the per-unit values
before the metric is aggregated.

## What winsorization does

Winsorization **caps** (clips) extreme per-unit values to a percentile threshold instead of letting
them through unchanged. For example, capping the upper `1%` replaces every per-unit value above the
99th percentile with the 99th-percentile value.

Two design choices make this safe for experiment evaluation:

1. **The threshold is computed once from the pooled data across all variants and applied
   identically to every variant.** Because the very same absolute cap is used in every arm,
   winsorization is a single fixed transformation of the metric — it cannot, on its own, introduce a
   difference between variants. Computing the threshold *separately per variant* would cut the tail
   of each arm at a different absolute value and could bias (or even create) the measured effect, so
   Ep-Stats deliberately does **not** do that.

2. **Units are capped, not removed.** Unlike trimming, the units stay in the sample, so the
   denominator and the sample size are preserved. This keeps more information and avoids removing a
   different number of units from each arm.

## Upper vs. lower tail

Heavy-tailed metrics typically only have outliers in the **upper** tail; the lower tail is usually a
pile of legitimate zeros (most users do not convert). Winsorizing the lower tail of such a metric
would floor those real zeros and bias the mean upward. For that reason upper-tail winsorization is
the common case and lower-tail winsorization is opt-in and off by default.

## Configuration

Winsorization is configured per [`Metric`][epstats.toolkit.metric.Metric] through two optional
parameters, each expressed as a percentage (`0`–`50`) of the tail to cap:

- `outlier_upper_percentile` — cap the upper tail. `1` caps everything above the 99th pooled
  percentile down to the 99th-percentile value.
- `outlier_lower_percentile` — cap the lower tail (analogous, off by default).

```python
from epstats.toolkit import Metric

Metric(
    1,
    'Revenue per User',
    'value(test_unit_type.unit.revenue)',
    'count(test_unit_type.unit.exposure)',
    # cap the most extreme 1% of users to the pooled 99th percentile
    outlier_upper_percentile=1,
)
```

Over the HTTP API the same parameters are available on the metric definition as
`outlier_upper_percentile` and `outlier_lower_percentile`.

## Scope and caveats

- Winsorization only applies to [`evaluate_by_unit`][epstats.toolkit.experiment.Experiment.evaluate_by_unit],
  because it needs the individual per-unit values. The pre-aggregated
  [`evaluate_agg`][epstats.toolkit.experiment.Experiment.evaluate_agg] path has no per-unit data and
  is unaffected.
- Winsorization changes the estimand slightly: you are estimating the mean of the *capped* metric
  rather than of the raw metric. This is the intended trade-off — a small, controlled bias in
  exchange for robustness to extreme values. Keep the capped fraction small (typically `≤ 1%`).
- The standard deviation reported after winsorization is the ordinary (capped) sample standard
  deviation. With large samples and a small capped fraction the difference from a dedicated
  winsorized-variance estimator is negligible.
