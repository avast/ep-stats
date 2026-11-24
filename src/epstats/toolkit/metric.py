import re
from typing import Dict, Optional, Set

import numpy as np
import pandas as pd

from .parser import Parser


class Metric:
    """
    Definition of a metric to evaluate in an experiment.
    """

    def __init__(
        self,
        id: int,
        name: str,
        nominator: str,
        denominator: str,
        metric_format: str = "{:.2%}",
        metric_value_multiplier: int = 1,
        minimum_effect: Optional[float] = None,
        outlier_upper_percentile: Optional[float] = None,
        outlier_lower_percentile: Optional[float] = None,
        statistic: str = "mean",
    ):
        """
        Constructor of the general metric definition.

        Parameters `nominator` and `denominator` specify exactly type of data and aggregation of the metric nominator
        and denominator.

        Parameters `format` and `multiplier` do not play any role in metric evaluation. They are used independently
        after the metric evaluation.

        Arguments:
            id: metric (order) id
            name: metric name
            nominator: definition of nominator
            denominator: definition of denominator
            metric_format: specify format of the metric, e.g. '${:,.1f}' for RPM
            metric_value_multiplier: specify multiplier, e.g. 1000 for RPM
            minimum_effect: minimum (relative) effect of interest used to estimate the required sample size
            outlier_upper_percentile: percentage (`0`-`50`) of the upper tail to winsorize (cap) before the
                metric is evaluated. E.g. `1` caps every per-unit value above the 99th percentile down to the
                99th percentile value. The threshold is computed once from the pooled per-unit values across
                all variants and applied identically to every variant, so it makes the evaluation robust to
                extreme outliers without biasing the comparison between variants. Unlike trimming, units are
                kept (only their extreme values are capped), so the denominator / sample size is preserved.
                Applies only to [`evaluate_by_unit`][epstats.toolkit.experiment.Experiment.evaluate_by_unit].
                `None` (default) disables upper-tail winsorization.
            outlier_lower_percentile: percentage (`0`-`50`) of the lower tail to winsorize (floor), analogous
                to `outlier_upper_percentile`. Usually left as `None` because heavy-tailed metrics (revenue,
                time spent, ...) typically only have outliers in the upper tail while the lower tail is made of
                legitimate zeros.
            statistic: which statistic of the per-unit nominator values to compare between variants.
                `'mean'` (default) runs the usual Welch's t-test on the relative difference in means.
                `'median'` or `'p<number>'` (e.g. `'p90'`, `'p99.5'`, with the number in `(0, 100)`)
                compares the given quantile instead, with the standard error of the relative difference
                estimated by bootstrap. See [Median and Percentile Metrics](../stats/percentiles.md).
                Quantile statistics need the individual per-unit values, so they are supported only by
                [`evaluate_by_unit`][epstats.toolkit.experiment.Experiment.evaluate_by_unit];
                [`evaluate_agg`][epstats.toolkit.experiment.Experiment.evaluate_agg] raises a `ValueError`.

        Usage:

        ```python
        Metric(
            1,
            'Click-through Rate',
            'count(test_unit_type.unit.click)',
            'count(test_unit_type.global.exposure)')
        ```
        """
        self._validate_outlier_percentile(
            "outlier_upper_percentile", outlier_upper_percentile
        )
        self._validate_outlier_percentile(
            "outlier_lower_percentile", outlier_lower_percentile
        )
        self.statistic, self.quantile = self._parse_statistic(statistic)

        self.id = id
        self.name = name
        self.nominator = nominator
        self.denominator = denominator
        self._parser = Parser(nominator, denominator)
        self._goals = self._parser.get_goals()
        self.metric_format = metric_format
        self.metric_value_multiplier = metric_value_multiplier
        self.minimum_effect = minimum_effect
        self.outlier_upper_percentile = outlier_upper_percentile
        self.outlier_lower_percentile = outlier_lower_percentile
        self._validate_quantile_not_winsorized()

    @staticmethod
    def _validate_outlier_percentile(name: str, percentile: Optional[float]) -> None:
        if percentile is not None and not 0 <= percentile < 50:
            raise ValueError(
                f"`{name}` must be in `[0, 50)` but `{percentile}` received."
            )

    _MEAN_STATISTIC = "mean"
    _MEDIAN_STATISTIC = "median"
    _PERCENTILE_PATTERN = re.compile(r"^p(\d+(?:\.\d+)?)$")

    @classmethod
    def _parse_statistic(cls, statistic: str) -> (str, Optional[float]):
        """
        Normalize the `statistic` argument into a `(statistic, quantile)` pair where `quantile` is
        `None` for the mean and the probability in `(0, 1)` for a quantile statistic.
        """
        if not isinstance(statistic, str):
            raise ValueError(
                f"`statistic` must be a string but `{type(statistic).__name__}` received."
            )

        normalized = statistic.strip().lower()
        if normalized == cls._MEAN_STATISTIC:
            return cls._MEAN_STATISTIC, None
        if normalized == cls._MEDIAN_STATISTIC:
            return cls._MEDIAN_STATISTIC, 0.5

        match = cls._PERCENTILE_PATTERN.match(normalized)
        if match:
            percentile = float(match.group(1))
            if not 0 < percentile < 100:
                raise ValueError(
                    f"Percentile of `statistic` must be in `(0, 100)` but `{statistic}` received."
                )
            return normalized, percentile / 100

        raise ValueError(
            f"`statistic` must be one of `mean`, `median`, `p<number>` (e.g. `p90`) "
            f"but `{statistic}` received."
        )

    def _validate_quantile_not_winsorized(self) -> None:
        """
        Reject metric definitions where the requested quantile lies inside a winsorized tail.

        Winsorization cannot change a quantile strictly inside the retained range, but a quantile
        that falls in a capped tail would be flattened to the cap itself, making the comparison
        between variants meaningless.
        """
        if not self.is_quantile_statistic:
            return

        lower_quantile, upper_quantile = self._get_outlier_quantiles()
        if self.quantile <= lower_quantile or self.quantile >= upper_quantile:
            raise ValueError(
                f"`statistic='{self.statistic}'` (quantile `{self.quantile}`) falls inside a "
                f"winsorized tail `[0, {lower_quantile}] / [{upper_quantile}, 1]`. Winsorization "
                f"would flatten the quantile to the cap. Pick a quantile inside "
                f"`({lower_quantile}, {upper_quantile})` or relax the outlier percentiles."
            )

    @property
    def is_quantile_statistic(self) -> bool:
        """
        `True` when the metric compares a quantile (median / percentile) instead of the mean.
        """
        return self.quantile is not None

    def get_goals(self) -> Set:
        """
        Get all goals needed to evaluate the metric.
        """
        return self._goals

    def get_evaluate_columns_agg(self, goals: pd.DataFrame) -> np.array:
        """
        Get `count`, `sum_value`, `sum_value_sqr` numpy array of shape (variants, metrics) after
        evaluating nominator and denominator expressions from pre-aggregated goals.

        Arguments:
            goals: one row per experiment variant

        See [`Experiment.evaluate_agg`][epstats.toolkit.experiment.Experiment.evaluate_agg] for details
        on `goals` at input.

        Returns:
            numpy array of shape (variants, metrics) where metrics are in order of
            (count, sum_value, sum_sqr_value)

        Raises:
            ValueError: when the metric uses a quantile `statistic`. A quantile cannot be recovered
                from the pre-aggregated `(count, sum_value, sum_sqr_value)` sufficient statistics.
        """
        if self.is_quantile_statistic:
            raise ValueError(
                f"Metric `{self.id}` (`{self.name}`) uses `statistic='{self.statistic}'`, which "
                "cannot be evaluated from pre-aggregated goals because a quantile is not "
                "recoverable from `(count, sum_value, sum_sqr_value)`. Use "
                "`Experiment.evaluate_by_unit` instead."
            )
        return self._parser.evaluate_agg(goals)

    def get_evaluate_columns_by_unit(self, goals: pd.DataFrame) -> np.array:
        """
        Get `count`, `sum_value`, `sum_value_sqr` numpy array of shape (variants, metrics) after
        evaluating nominator and denominator expressions from goals aggregated by unit.

        Arguments:
            goals: one row per experiment variant

        See [`Experiment.evaluate_agg`][epstats.toolkit.experiment.Experiment.evaluate_by_unit] for details
        on `goals` at input.

        Returns:
            numpy array of shape (variants, metrics) where metrics are in order of
            (count, sum_value, sum_sqr_value)
        """
        lower_quantile, upper_quantile = self._get_outlier_quantiles()
        return self._parser.evaluate_by_unit(goals, lower_quantile, upper_quantile)

    def get_unit_values_by_variant(self, goals: pd.DataFrame) -> Dict[str, np.ndarray]:
        """
        Get the (optionally winsorized) per-unit nominator values grouped by experiment variant.

        Needed by statistics that are not recoverable from the pre-aggregated sufficient statistics,
        i.e. quantiles. The values are the per-unit nominator values including the zeros of exposed
        units without the goal.

        Arguments:
            goals: goals aggregated by unit, as passed to
                [`Experiment.evaluate_by_unit`][epstats.toolkit.experiment.Experiment.evaluate_by_unit]

        Returns:
            dictionary mapping `exp_variant_id` to the 1-d numpy array of that variant's per-unit values
        """
        lower_quantile, upper_quantile = self._get_outlier_quantiles()
        value_variants, value = self._parser.evaluate_unit_values(
            goals, lower_quantile, upper_quantile
        )
        values_df = pd.DataFrame(
            {"exp_variant_id": np.asarray(value_variants), "value": np.asarray(value)}
        )
        return {
            variant: group["value"].to_numpy(dtype=float)
            for variant, group in values_df.groupby("exp_variant_id")
        }

    def _get_outlier_quantiles(self) -> (float, float):
        """
        Translate the upper/lower outlier percentiles (percentage winsorized from each tail) into
        the `(lower_quantile, upper_quantile)` pair used to cap per-unit values. Returns `(0.0, 1.0)`
        (no winsorization) when outlier handling is disabled.
        """
        lower_quantile = (self.outlier_lower_percentile or 0) / 100
        upper_quantile = 1 - (self.outlier_upper_percentile or 0) / 100
        return lower_quantile, upper_quantile


class SimpleMetric(Metric):
    """
    Simplified metric definition to evaluate in an experiment.
    """

    def __init__(
        self,
        id: int,
        name: str,
        numerator: str,
        denominator: str,
        unit_type: str = "test_unit_type",
        metric_format: str = "{:.2%}",
        metric_value_multiplier: int = 1,
        minimum_effect: Optional[float] = None,
        outlier_upper_percentile: Optional[float] = None,
        outlier_lower_percentile: Optional[float] = None,
        statistic: str = "mean",
    ):
        """
        Constructor of the simplified metric definition.

        It modifies parameters numerator and denominator in a way that it is in line with general Metric definition.
        It adds all the niceties necessary for proper Metric format. Finally it calls constructor of the parent Metric
        class.

        Arguments:
            id: metric (order) id
            name: metric name
            numerator: value (column) of the numerator
            denominator: value (column) of the denominator
            unit_type: unit type
            metric_format: specify format of the metric, e.g. '${:,.1f}' for RPM
            metric_value_multiplier: specify multiplier, e.g. 1000 for RPM
            statistic: statistic to compare between variants, `'mean'` (default), `'median'` or
                `'p<number>'` -- see [`Metric`][epstats.toolkit.metric.Metric]

        Usage:

        ```python
        SimpleMetric(
            1,
            'Click-through Rate',
            'clicks',
            'views',
            unit_type='test_unit_type',
            metric_format='{:.2%}',
            metric_value_multiplier=1)
        ```
        """
        agg_type = "global"  # technical parameter; it has no impact
        num = "value" + "(" + unit_type + "." + agg_type + "." + numerator + ")"
        den = "value" + "(" + unit_type + "." + agg_type + "." + denominator + ")"

        super().__init__(
            id,
            name,
            num,
            den,
            metric_format,
            metric_value_multiplier,
            minimum_effect,
            outlier_upper_percentile,
            outlier_lower_percentile,
            statistic,
        )
