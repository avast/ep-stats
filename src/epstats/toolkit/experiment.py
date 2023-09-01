import logging
from typing import List, Any
from enum import Enum
import pandas as pd
import numpy as np
from collections import Counter
from typing import Optional
from datetime import datetime
from dataclasses import dataclass

from .metric import Metric, SimpleMetric
from .check import Check
from .utils import get_utc_timestamp, goals_wide_to_long
from .parser import EpGoal, UnitType, AggType, Goal

from .statistics import Statistics, DEFAULT_CONFIDENCE_LEVEL, DEFAULT_POWER
from ..prometheus import get_prometheus_metric, Counter as PrometheusCounter


check_evaluation_errors_metric = get_prometheus_metric("check_evaluation_errors_total", PrometheusCounter)


class Evaluation:
    """
    Results of an experiment evaluation.
    """

    def __init__(self, metrics: pd.DataFrame, checks: pd.DataFrame, exposures: pd.DataFrame):
        self.metrics = metrics
        self.checks = checks
        self.exposures = exposures

    @classmethod
    def metric_columns(cls) -> List[str]:
        """
        `metrics` dataframe with columns:

        1. `timestamp` - timestamp of evaluation
        1. `exp_id` - experiment id
        1. `metric_id` - metric id as in [`Experiment`][epstats.toolkit.experiment.Experiment] definition
        1. `metric_name` - metric name as in [`Experiment`][epstats.toolkit.experiment.Experiment] definition
        1. `exp_variant_id` - variant id
        1. `count` - number of exposures, value of metric denominator
        1. `mean` - `sum_value` / `count`
        1. `std` - sample standard deviation
        1. `sum_value` - value of goals, value of metric nominator
        1. `confidence_level` - current confidence level used to calculate `p_value` and `confidence_interval`
        1. `diff` - relative diff between sample means of this and control variant
        1. `test_stat` - value of test statistic of the relative difference in means
        1. `p_value` - p-value of the test statistic under current `confidence_level`
        1. `confidence_interval` - confidence interval of the `diff` under current `confidence_level`
        1. `standard_error` - standard error of the `diff`
        1. `degrees_of_freedom` - degrees of freedom of this variant mean
        """
        return [
            "timestamp",
            "exp_id",
            "metric_id",
            "metric_name",
            "exp_variant_id",
            "count",
            "mean",
            "std",
            "sum_value",
            "confidence_level",
            "diff",
            "test_stat",
            "p_value",
            "confidence_interval",
            "standard_error",
            "degrees_of_freedom",
            "minimum_effect",
            "sample_size",
            "required_sample_size",
        ]

    @classmethod
    def check_columns(cls) -> List[str]:
        """
        `checks` dataframe with columns:

        1. `timestamp` - timestamp of evaluation
        1. `exp_id` - experiment id
        1. `check_id` - check id as in [`Experiment`][epstats.toolkit.experiment.Experiment] definition
        1. `variable_id` - name of the variable in check evaluation, SRM check has following variables `p_value`,
        `test_stat`, `confidence_level`
        1. `value` - value of the variable
        """
        return ["timestamp", "exp_id", "check_id", "check_name", "variable_id", "value"]

    @classmethod
    def exposure_columns(cls) -> List[str]:
        """
        `exposures` dataframe with columns:

        1. `timestamp` - timestamp of evaluation
        1. `exp_id` - experiment id
        1. `exp_variant_id` - variant id
        1. `exposures` - number of exposures of this variant
        """
        return ["exp_variant_id", "exposures"]


class FilterScope(str, Enum):
    """
    Scope of data where to apply the filter.
    """

    exposure = "exposure"
    goal = "goal"


@dataclass
class Filter:
    """
    Filter specification for data to evaluate.
    """

    dimension: str
    value: List[Any]
    scope: FilterScope


class Experiment:
    """
    Evaluate one experiment described as a list of metrics and checks.

    See [Statistics](../stats/basics.md) for details about statistical method used
    and [`Evaluation`][epstats.toolkit.experiment.Evaluation] for description of output.
    """

    def __init__(
        self,
        id: str,
        control_variant: str,
        metrics: List[Metric],
        checks: List[Check],
        unit_type: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        date_for: Optional[str] = None,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
        variants: Optional[List[str]] = None,
        filters: Optional[List[Filter]] = None,
        query_parameters: dict = {},
    ):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.id = id
        self.control_variant = control_variant
        self.unit_type = unit_type
        self.metrics = metrics
        self._check_metric_ids_unique()
        self.checks = checks
        self.date_from = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from is not None else None
        self.date_to = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to is not None else None
        self.date_for = (
            datetime.strptime(date_for, "%Y-%m-%d").date() if date_for is not None else datetime.today().date()
        )
        self.confidence_level = confidence_level
        self.variants = variants
        self._exposure_goals = [
            EpGoal(
                [
                    "count",
                    "(",
                    UnitType([unit_type]),
                    ".",
                    AggType(["global"]),
                    ".",
                    Goal(["exposure"]),
                    ")",
                ]
            )
        ]
        self._update_dimension_to_value()
        self.filters = filters if filters is not None else []
        self.query_parameters = query_parameters

    def _check_metric_ids_unique(self):
        """
        Raises an exception if `metrics` contain duplicated ids.
        """
        id_counts = Counter(metric.id for metric in self.metrics)
        for id_, count in id_counts.items():
            if count > 1:
                raise ValueError(f"Metric ids must be unique. Id={id_} found more than once.")

    def _update_dimension_to_value(self):
        """
        To every `EpGoal` across all metrics, we need to add missing dimensions
        that are present in every other `EpGoal` instances so the row masking
        can work properly.
        """

        for goal in self.get_goals():
            for dimension in self.get_dimension_columns():
                if dimension not in goal.dimension_to_value:
                    goal.dimension_to_value[dimension] = ""

    def evaluate_agg(self, goals: pd.DataFrame) -> Evaluation:
        """
        Evaluate all metrics and checks in the experiment from already pre-aggregated goals.

        This method is usefull when there are too many units in the experiment to evaluate it
        using [`evaluate_by_unit`][epstats.toolkit.experiment.Experiment.evaluate_by_unit].

        Does best effort to fill in missing goals and variants with zeros.

        Arguments:
            goals: dataframe with one row per goal and aggregated data in columns

        `goals` dataframe columns:

        1. `exp_id` - experiment id
        1. `exp_variant_id` - variant
        1. `unit_type` - randomization unit type
        1. `agg_type` - level of aggregation
        1. `goal` - goal name
        1. any number of dimensional columns, e.g. column `product` containing values `p_1`
        1. `count` - number of observed goals (e.g. conversions)
        1. `sum_sqr_count` - summed squared number of observed goals per unit, it is similar
        to `sum_sqr_value`
        1. `sum_value` - value of observed goals
        1. `sum_sqr_value` - summed squared value per unit.  This is used to calculate
        sample standard deviation from pre-aggregated data (it is a term $\sum x^2$
        in $\hat{\sigma}^2 = \\frac{\sum x^2 - \\frac{(\sum x)^2}{n}}{n-1}$).
        1. `count_unique` - number of units with at least 1 observed goal

        Returns:
            set of dataframes with evaluation

        Usage:

        ```python
        from epstats.toolkit import Experiment, Metric, SrmCheck
        experiment = Experiment(
            'test-conversion',
            'a',
            [Metric(
                1,
                'Click-through Rate',
                'count(test_unit_type.unit.click)',
                'count(test_unit_type.global.exposure)'),
            ],
            [SrmCheck(1, 'SRM', 'count(test_unit_type.global.exposure)')],
            unit_type='test_unit_type')

        # This gets testing data, use other Dao or get aggregated goals in some other way.
        from epstats.toolkit.testing import TestData
        goals = TestData.load_goals_agg(experiment.id)

        # evaluate experiment
        ev = experiment.evaluate_agg(goals)

        # work with results
        print(ev.exposures)
        print(ev.metrics[ev.metrics == 1])
        print(ev.checks[ev.checks == 1])

        # this is to assert that this code sample works correctly
        from epstats.toolkit.testing import TestDao
        assert_experiment(experiment, ev, TestDao(TestData()))
        ```

        Input data frame example:

        ```
        exp_id      exp_variant_id  unit_type           agg_type    goal            product             count   sum_sqr_count   sum_value   sum_sqr_value   count_unique
        test-srm    a               test_unit_type      global      exposure                            100000  100000          100000      100000          100000
        test-srm    b               test_unit_type      global      exposure                            100100  100100          100100      100100          100100
        test-srm    a               test_unit_type      unit        conversion                          1200    1800            32000       66528           900
        test-srm    a               test_unit_type_2    global      conversion      product_1           1000    1700            31000       55000           850
        ```
        """
        g = self._fix_missing_agg(goals)
        return self._evaluate(
            g,
            Experiment._metrics_column_fce_agg,
            Experiment._checks_fce_agg,
            Experiment._exposures_fce_agg,
        )

    def evaluate_wide_agg(self, goals: pd.DataFrame) -> Evaluation:
        """
        This is a simplified version of the method [`evaluate_agg`][epstats.toolkit.experiment.Experiment.evaluate_agg].

        It consumes simple input `goals` dataframe, transfers it into suitable dataframe format and evaluate it using general method [`evaluate_agg`][epstats.toolkit.experiment.Experiment.evaluate_agg].

        It assumes that the first two columns are name of the experiment and variants. Than follows columns with data.

        See usage of the method in the notebook [Ad-hoc A/B test evaluation using Ep-Stats](../user_guide/ab_test_simple_evaluation.html).

        Arguments:
            goals: dataframe with one row per variant and aggregated data in columns

        Possible `goals` dataframe columns (check the input dataframe example):

        1. `exp_id` - experiment id
        1. `exp_variant_id` - variant
        1. `clicks` - sum of clicks
        1. `views` - sum of views
        1. `bookings` - sum of bookings
        1. `bookings_squared` - sum of bookings squared

        Returns:
            set of dataframes with evaluation

        Usage:

        ```python
        from epstats.toolkit import Experiment, SimpleMetric, SimpleSrmCheck
        from epstats.toolkit.results import results_long_to_wide, format_results
        from epstats.toolkit.testing import TestData

        # Load Test Data
        goals = TestData.load_goals_simple_agg()

        # Define the experiment
        unit_type = 'test_unit_type'
        experiment = Experiment(
            'test-simple-metric',
            'a',
            [
                SimpleMetric(1, 'Click-through Rate (CTR)', 'clicks', 'views', unit_type),
                SimpleMetric(2, 'Conversion Rate', 'conversions', 'views', unit_type),
                SimpleMetric(3, 'Revenue per Mille (RPM)', 'bookings', 'views', unit_type, metric_format='${:,.2f}', metric_value_multiplier=1000),
            ],
            [SimpleSrmCheck(1, 'SRM', 'views')],
            unit_type=unit_type)

        # Evaluate the experiment
        ev = experiment.evaluate_wide_agg(goals)

        # Work with results
        print(ev.exposures)
        print(ev.metrics)
        print(ev.checks)

        # Possible formatting of metrics
        ev.metrics.pipe(results_long_to_wide).pipe(format_results, experiment, format_pct='{:.1%}', format_pval='{:.3f}')
        ```

        Input dataframe example:
        ```
        experiment_id   variant_id  views   clicks  conversions     bookings    bookings_squared
        my-exp          a           473661  48194   413             17152       803105
        my-exp          b           471485  47184   360             14503       677178
        my-exp          c           477159  48841   406             15892       711661
        my-exp          d           474934  49090   289             11995       566700
        ```
        """
        g = goals_wide_to_long(goals, self.unit_type)
        return self.evaluate_agg(g)

    def evaluate_by_unit(self, goals: pd.DataFrame) -> Evaluation:
        """
        Evaluate all metrics and checks in the experiment from goals grouped by `unit_id`.

        This method is usefull when there are not many (<1M) units in the experiment to evaluate it.
        If there many units exposed to the experiment, pre-aggregate data and use [`evaluate_agg`][epstats.toolkit.experiment.Experiment.evaluate_agg].

        Does best effort to fill in missing goals and variants with zeros.

        Arguments:
            goals: dataframe with one row per goal and aggregated data in columns

        `goals` dataframe columns:

        1. `exp_id` - experiment id
        1. `exp_variant_id` - variant
        1. `unit_type` - randomization unit type
        1. `unit_id` - (randomization) unit id
        1. `agg_type` - level of aggregation
        1. `goal` - goal name
        1. any number of dimensional columns, e.g. column `product` containing values `p_1`
        1. `count` - number of observed goals
        1. `sum_value` - value of observed goals

        Returns:
            set of dataframes with evaluation

        Usage:

        ```python
        from epstats.toolkit import Experiment, Metric, SrmCheck
        experiment = Experiment(
            'test-real-valued',
            'a',
            [Metric(
                2,
                'Average Bookings',
                'value(test_unit_type.unit.conversion)',
                'count(test_unit_type.unit.exposure)')
            ],
            [],
            unit_type='test_unit_type')

        # This gets testing data, use other Dao or get aggregated goals in some other way.
        from epstats.toolkit.testing import TestData
        goals = TestData.load_goals_by_unit(experiment.id)

        # evaluate experiment
        ev = experiment.evaluate_by_unit(goals)

        # work with results
        print(ev.exposures)
        print(ev.metrics[ev.metrics == 1])
        print(ev.checks[ev.checks == 1])

        # this is to assert that this code sample works correctly
        from epstats.toolkit.testing import TestDao
        assert_experiment(experiment, ev, TestDao(TestData()))
        ```

        Input data frame example:

        ```
        exp_id      exp_variant_id  unit_type       unit_id             agg_type    goal              product             count   sum_value
        test-srm    a               test_unit_type  test_unit_type_1    unit        exposure                              1       1
        test-srm    a               test_unit_type  test_unit_type_1    unit        conversion        product_1           2       75
        test-srm    b               test_unit_type  test_unit_type_2    unit        exposure                              1       1
        test-srm    b               test_unit_type  test_unit_type_3    unit        exposure                              1       1
        test-srm    b               test_unit_type  test_unit_type_3    unit        conversion        product_2           1       1
        ```
        """
        g = self._fix_missing_by_unit(goals)

        # We need to pivot table to get all goals per `unit_id` on the same row in the data frame.
        # This is needed to be able to vector-evaluate compound metrics
        # eg. `value(test_unit_type.unit.conversion) - value(test_unit_type.unit.refund)`
        g = (
            pd.pivot_table(
                g,
                values=["count", "sum_value"],
                index=[
                    "exp_id",
                    "exp_variant_id",
                    "unit_type",
                    "agg_type",
                    "unit_id",
                ]
                + self.get_dimension_columns(),
                columns="goal",
                aggfunc=np.sum,
                fill_value=0,
            )
            .swaplevel(axis=1)
            .reset_index()
        )

        return self._evaluate(
            g,
            Experiment._metrics_column_fce_by_unit,
            Experiment._checks_fce_by_unit,
            Experiment._exposures_fce_by_unit,
        )

    def get_goals(self) -> List[EpGoal]:
        """
        List of all goals needed to evaluate all metrics and checks in the experiment.

        Returns:
            list of parsed structured goals
        """
        res = set()
        for m in self.metrics:
            res = res.union(m.get_goals())
        for c in self.checks:
            res = res.union(c.get_goals())
        res = res.union(self._exposure_goals)
        return list(res)

    @staticmethod
    def _metrics_column_fce_agg(m: Metric, goals: pd.DataFrame):
        """
        Gets count, sum_value, sum_sqr_value columns by expression from already aggregated goals.
        """
        return m.get_evaluate_columns_agg(goals)

    @staticmethod
    def _metrics_column_fce_by_unit(m: Metric, goals: pd.DataFrame):
        """
        Gets count, sum_value, sum_sqr_value columns by expression from goals grouped by `unit_id`.
        """
        return m.get_evaluate_columns_by_unit(goals)

    @staticmethod
    def _checks_fce_agg(c: Check, goals: pd.DataFrame, control_variant: str):
        """
        Evaluates checks from already aggregated goals.
        """
        return c.evaluate_agg(goals, control_variant)

    @staticmethod
    def _checks_fce_by_unit(c: Check, goals: pd.DataFrame, control_variant: str):
        """
        Evaluates checks from goals grouped by `unit_id`.
        """
        return c.evaluate_by_unit(goals, control_variant)

    @staticmethod
    def _exposures_fce_agg(goals: pd.DataFrame, exp_id: str, unit_type: str):
        """
        Evaluates checks from already aggregated goals.
        """
        df = (
            goals[(goals["unit_type"] == unit_type) & (goals["agg_type"] == "global") & (goals["goal"] == "exposure")]
            .groupby("exp_variant_id")
            .agg(exposures=("count", "sum"))
            .reset_index()
        )
        df["exp_id"] = exp_id
        return df

    @staticmethod
    def _exposures_fce_by_unit(goals: pd.DataFrame, exp_id: str, unit_type: str):
        """
        Evaluates checks from already aggregated goals.
        """
        df = goals[(goals["unit_type"] == unit_type) & (goals["agg_type"] == "unit")][
            [("exp_variant_id", ""), ("exposure", "count")]
        ]
        df = df.droplevel(0, axis=1)
        df.columns = ["exp_variant_id", "exposures"]
        d = df.groupby("exp_variant_id").agg(exposures=("exposures", "sum")).reset_index()
        d["exp_id"] = exp_id
        return d

    def _evaluate(self, goals: pd.DataFrame, metrics_column_fce, checks_fce, exposures_fce):
        metrics = self._evaluate_metrics(goals, metrics_column_fce)
        checks = self._evaluate_checks(goals, checks_fce)
        exposures = self._evaluate_exposures(goals, exposures_fce)
        return Evaluation(metrics, checks, exposures)

    def _evaluate_exposures(self, goals: pd.DataFrame, exposures_fce) -> pd.DataFrame:
        return exposures_fce(goals, self.id, self.unit_type)

    def _evaluate_checks(self, goals: pd.DataFrame, check_fce) -> pd.DataFrame:
        res = []
        for c in self.checks:
            try:
                r = check_fce(c, goals, self.control_variant)
                r["exp_id"] = self.id
                res.append(r)
            except Exception as e:
                self._logger.warning(f"Cannot evaluate check [{c.id} in experiment [{self.id}] because of {e}")
                check_evaluation_errors_metric.inc()

        c = pd.concat(res, axis=0) if res != [] else pd.DataFrame([], columns=Evaluation.check_columns())
        c["timestamp"] = round(get_utc_timestamp(datetime.now()).timestamp())
        return c[Evaluation.check_columns()]

    def get_dimension_columns(self) -> List[str]:
        """
        Returns a list of all dimensions used in all metrics in the experiment.
        """
        return list({d for g in self.get_goals() for d in g.dimension_to_value.keys()})

    def _set_variants(self, goals):
        # what variants and goals there should be from all the goals needed to evaluate all metrics
        self.variants = (
            self.variants
            if self.variants is not None
            else np.unique(np.append(goals["exp_variant_id"], self.control_variant))
        )

    def _fix_missing_agg(self, goals: pd.DataFrame) -> pd.DataFrame:
        """
        Adds zero values for missing goals and variants that are needed for metric evaluation.

        Does that in the best effort - fills in `count`, `sum_sqr_count`, `sum_value`, `sum_sqr_value` and `count_unique` with zeros.
        """
        # what variants and goals there should be from all the goals needed to evaluate all metrics
        self._set_variants(goals)
        g = goals[goals.exp_variant_id.isin(self.variants)]
        nvs = self.variants
        ngs = self.get_goals()

        # variants * goals is the number of variant x goals combinations we expect in the data
        lnvs = len(nvs)
        lngs = len(ngs)

        # create zero data frame for all variants and goals
        empty_df = pd.DataFrame(
            {
                "exp_id": self.id,
                "exp_variant_id": np.tile(nvs, lngs),
                "unit_type": np.repeat([g.unit_type for g in ngs], lnvs),
                "agg_type": np.repeat([g.agg_type for g in ngs], lnvs),
                "goal": np.repeat([g.goal for g in ngs], lnvs),
                "count": 0,
                "sum_sqr_count": 0,
                "sum_value": 0,
                "sum_sqr_value": 0,
                "count_unique": 0,
            }
        )

        for dimension in self.get_dimension_columns():
            empty_df[dimension] = np.repeat([g.dimension_to_value.get(dimension, "") for g in ngs], lnvs)

        # join to existing data and use zeros for only missing variants and goals
        m = (
            pd.concat([g, empty_df], axis=0)
            .fillna({d: "" for d in self.get_dimension_columns()})
            .groupby(
                [
                    "exp_id",
                    "exp_variant_id",
                    "unit_type",
                    "agg_type",
                    "goal",
                ]
                + self.get_dimension_columns(),
                # dropna=False,
            )
            .sum()
            .reset_index()
        )
        return m

    def _fix_missing_by_unit(self, goals: pd.DataFrame) -> pd.DataFrame:
        """
        Adds zero values for missing goals and variants that are needed for metric evaluation.

        Does that in the best effort - fills in `count`, `sum_value` with zeros.
        """
        # what variants and goals there should be from all the goals needed to evaluate all metrics
        self._set_variants(goals)
        g = goals[goals.exp_variant_id.isin(self.variants)]
        nvs = self.variants
        ngs = self.get_goals()

        # variants * goals is the number of variant x goals combinations we expect in the data
        lnvs = len(nvs)
        lngs = len(ngs)

        # create zero data frame for all variants and goals
        empty_df = pd.DataFrame(
            {
                "exp_id": self.id,
                "exp_variant_id": np.tile(nvs, lngs),
                "unit_type": np.repeat([g.unit_type for g in ngs], lnvs),
                "agg_type": np.repeat([g.agg_type for g in ngs], lnvs),
                "goal": np.repeat([g.goal for g in ngs], lnvs),
                "unit_id": np.nan,
                "count": 0,
                "sum_value": 0,
            }
        )

        for dimension in self.get_dimension_columns():
            empty_df[dimension] = np.repeat([g.dimension_to_value.get(dimension, "") for g in ngs], lnvs)

        # join to existing data and use zeros for only missing variants and goals
        m = pd.concat([g, empty_df], axis=0).fillna({d: "" for d in self.get_dimension_columns()})
        return m[
            [
                "exp_id",
                "exp_variant_id",
                "unit_type",
                "agg_type",
                "goal",
                "unit_id",
                "count",
                "sum_value",
            ]
            + self.get_dimension_columns()
        ]

    def _get_required_sample_size(
        self,
        metric_row: pd.Series,
        controls: dict,
        minimum_effects: dict,
        metrics_with_value_denominator: set,
        n_variants: int,
    ) -> pd.Series:

        metric_id = metric_row["metric_id"]
        minimum_effect = minimum_effects[metric_id]
        index = ["minimum_effect", "sample_size", "required_sample_size"]

        # Right now, metric with value() denominator would return count that is not equal
        # to the sample size. In such case we do not evaluate the required sample size.
        # TODO: add suport for value() denominator metrics,
        # parser will return an additional column equal to count or count_unique.
        sample_size = metric_row["count"] if metric_id not in metrics_with_value_denominator else np.nan

        if metric_row["exp_variant_id"] == self.control_variant or pd.isnull(minimum_effect):
            return pd.Series([np.nan, sample_size, np.nan], index)

        metric_id = metric_row["metric_id"]
        return pd.Series(
            [
                minimum_effect,
                sample_size,
                Statistics.required_sample_size_per_variant(
                    n_variants=n_variants,
                    minimum_effect=minimum_effect,
                    mean=controls[metric_id]["mean"],
                    std=controls[metric_id]["std"],
                    std_2=metric_row["std"],
                    confidence_level=metric_row["confidence_level"],
                    power=DEFAULT_POWER,
                ),
            ],
            index,
        )

    def _get_required_sample_sizes(self, metrics: pd.DataFrame, n_variants: int) -> pd.DataFrame:

        controls = {
            r["metric_id"]: {"mean": r["mean"], "std": r["std"]}
            for _, r in metrics.iterrows()
            if r["exp_variant_id"] == self.control_variant
        }

        minimum_effects = {m.id: m.minimum_effect for m in self.metrics}
        metrics_with_value_denominator = {
            m.id for m in self.metrics if m.denominator.startswith("value(") and not isinstance(m, SimpleMetric)
        }

        return metrics.apply(
            lambda metric_row: self._get_required_sample_size(
                metric_row=metric_row,
                controls=controls,
                minimum_effects=minimum_effects,
                metrics_with_value_denominator=metrics_with_value_denominator,
                n_variants=n_variants,
            ),
            axis=1,
        )

    def _evaluate_metrics(self, goals: pd.DataFrame, column_fce) -> pd.DataFrame:
        if not self.metrics:
            return pd.DataFrame([], columns=Evaluation.metric_columns())

        sts = []
        for m in self.metrics:
            count, sum_value, sum_sqr_value = column_fce(m, goals)
            sts.append([count, sum_value, sum_sqr_value])
        stats = np.array(sts).transpose(0, 2, 1)
        metrics = stats.shape[0]
        n_variants = stats.shape[1]

        count = stats[:, :, 0]
        sum_value = stats[:, :, 1]
        sum_sqr_value = stats[:, :, 2]
        with np.errstate(divide="ignore", invalid="ignore"):
            # We fill in zeros, when goal data are missing for some variant.
            # There could be division by zero here which is expected as we return
            # nan or inf values to the caller.
            mean = sum_value / count
            std = np.sqrt((sum_sqr_value - sum_value * sum_value / count) / (count - 1))

        # sequential testing correction
        if self.date_from is not None and self.date_to is not None:
            # Parameters
            test_length = (self.date_to - self.date_from).days + 1  # test length in days
            actual_day = (self.date_for - self.date_from).days + 1  # day(s) since beginning of the test
            actual_day = min(actual_day, test_length)  # actual day of evaluation must be in interval [1, test_length]

            # confidence level adjustment - applied when actual_day < test_length (test is still running)
            confidence_level = Statistics.obf_alpha_spending_function(self.confidence_level, test_length, actual_day)
        else:
            confidence_level = self.confidence_level  # no change

        stats = np.dstack((count, mean, std, sum_value, np.ones(count.shape) * confidence_level))
        stats = np.dstack(
            (
                np.repeat([m.id for m in self.metrics], n_variants).reshape(metrics, n_variants, -1),
                np.repeat([m.name for m in self.metrics], n_variants).reshape(metrics, n_variants, -1),
                np.tile(goals["exp_variant_id"].unique(), metrics).reshape(metrics, n_variants, -1),
                stats,
            )
        )

        # dimensions of `stats` array: (metrics, variants, stats)
        # elements of `stats` array: metrics_id, exp_variant_id, count, mean, std, sum_value, confidence_level
        # hypothesis evaluation (standard way using t-test)
        c = Statistics.ttest_evaluation(stats, self.control_variant)

        # multiple variants (comparisons) correction - applied when we have multiple treatment variants
        if n_variants > 2:
            c = Statistics.multiple_comparisons_correction(c, n_variants, metrics, confidence_level)

        c["exp_id"] = self.id
        c["timestamp"] = round(get_utc_timestamp(datetime.now()).timestamp())
        c[["minimum_effect", "sample_size", "required_sample_size"]] = self._get_required_sample_sizes(c, n_variants)
        return c[Evaluation.metric_columns()]
