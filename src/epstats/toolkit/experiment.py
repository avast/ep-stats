import logging
from typing import List, Any
from enum import Enum
import pandas as pd
import numpy as np
from datetime import datetime
from statsd import StatsClient
from dataclasses import dataclass

from .metric import Metric
from .check import Check
from .utils import get_utc_timestamp
from .parser import EpGoal, UnitType, AggType, Goal

from .statistics import Statistics


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
        date_from: str = None,
        date_to: str = None,
        date_for: str = None,
        confidence_level: float = 0.95,
        variants: List[str] = None,
        statsd: StatsClient = StatsClient(),
        filters: List[Filter] = None,
    ):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.id = id
        self.control_variant = control_variant
        self.unit_type = unit_type
        self.metrics = metrics
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
        self.statsd = statsd
        self.filters = filters if filters is not None else []

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
        1. `dimension` - name of the dimension, e.g. `product`
        1. `dimension_value` - value of the dimension, e.g. `p_1`
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
        exp_id      exp_variant_id  unit_type           agg_type    goal            dimension       dimension_value     count   sum_sqr_count   sum_value   sum_sqr_value   count_unique
        test-srm    a               test_unit_type      global      exposure                                            100000  100000          100000      100000          100000
        test-srm    b               test_unit_type      global      exposure                                            100100  100100          100100      100100          100100
        test-srm    a               test_unit_type      unit        conversion                                            1200    1800            32000       66528           900
        test-srm    a               test_unit_type_2    global      conversion      product         product_1           1000    1700            31000       55000           850
        ```
        """
        g = self._fix_missing_agg(goals)
        return self._evaluate(
            g,
            Experiment._metrics_column_fce_agg,
            Experiment._checks_fce_agg,
            Experiment._exposures_fce_agg,
        )

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
        1. `dimension` - name of the dimension, e.g. `product`
        1. `dimension_value` - value of the dimension, e.g. `p_1`
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
        exp_id      exp_variant_id  unit_type       unit_id             agg_type    goal              dimension         dimension_value     count   sum_value
        test-srm    a               test_unit_type  test_unit_type_1    unit        exposure                                                1       1
        test-srm    a               test_unit_type  test_unit_type_1    unit        conversion        product           product_1           2       75
        test-srm    b               test_unit_type  test_unit_type_2    unit        exposure                                                1       1
        test-srm    b               test_unit_type  test_unit_type_3    unit        exposure                                                1       1
        test-srm    b               test_unit_type  test_unit_type_3    unit        conversion        product           product_2           1       1
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
                    "dimension",
                    "dimension_value",
                ],
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
                self.statsd.incr("errors.check")

        c = pd.concat(res, axis=1) if res != [] else pd.DataFrame([], columns=Evaluation.check_columns())
        c["timestamp"] = round(get_utc_timestamp(datetime.now()).timestamp())
        return c[Evaluation.check_columns()]

    def _fix_missing_agg(self, goals: pd.DataFrame) -> pd.DataFrame:
        """
        Adds zero values for missing goals and variants that are needed for metric evaluation.

        Does that in the best effort - fills in `count`, `sum_sqr_count`, `sum_value`, `sum_sqr_value` and `count_unique` with zeros.
        """
        # what variants and goals there should be from all the goals needed to evaluate all metrics
        self.variants = (
            self.variants
            if self.variants is not None
            else np.unique(np.append(goals["exp_variant_id"], self.control_variant))
        )
        g = goals[goals.exp_variant_id.isin(self.variants)]
        nvs = self.variants
        ngs = self.get_goals()

        # variants * goals is the number of variant x goals combinations we expect in the data
        lnvs = len(nvs)
        lngs = len(ngs)
        ln = lnvs * lngs

        # create zero data frame for all variants and goals
        empty_df = pd.DataFrame(
            {
                "exp_variant_id": np.tile(nvs, lngs),
                "unit_type": np.repeat([g.unit_type for g in ngs], lnvs),
                "agg_type": np.repeat([g.agg_type for g in ngs], lnvs),
                "goal": np.repeat([g.goal for g in ngs], lnvs),
                "dimension": np.repeat([g.dimension for g in ngs], lnvs),
                "dimension_value": np.repeat([g.dimension_value for g in ngs], lnvs),
                "count": np.zeros(ln),
                "sum_sqr_count": np.zeros(ln),
                "sum_value": np.zeros(ln),
                "sum_sqr_value": np.zeros(ln),
                "count_unique": np.zeros(ln),
            }
        )

        # join to existing data and use zeros for only missing variants and goals
        m = (
            pd.concat([g, empty_df], axis=0)
            .groupby(
                [
                    "exp_variant_id",
                    "unit_type",
                    "agg_type",
                    "dimension",
                    "dimension_value",
                    "goal",
                ]
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
        self.variants = (
            self.variants
            if self.variants is not None
            else np.unique(np.append(goals["exp_variant_id"], self.control_variant))
        )
        g = goals[goals.exp_variant_id.isin(self.variants)]
        nvs = self.variants
        ngs = self.get_goals()

        # variants * goals is the number of variant x goals combinations we expect in the data
        lnvs = len(nvs)
        lngs = len(ngs)
        ln = lnvs * lngs

        # create zero data frame for all variants and goals
        empty_df = pd.DataFrame(
            {
                "exp_id": np.repeat(self.id, ln),
                "exp_variant_id": np.tile(nvs, lngs),
                "unit_type": np.repeat([g.unit_type for g in ngs], lnvs),
                "agg_type": np.repeat([g.agg_type for g in ngs], lnvs),
                "goal": np.repeat([g.goal for g in ngs], lnvs),
                "dimension": np.repeat([g.dimension for g in ngs], lnvs),
                "dimension_value": np.repeat([g.dimension_value for g in ngs], lnvs),
                "unit_id": np.repeat("fillna", ln),
                "count": np.zeros(ln),
                "sum_value": np.zeros(ln),
            }
        )

        # join to existing data and use zeros for only missing variants and goals
        m = pd.concat([g, empty_df], axis=0)
        return m[
            [
                "exp_id",
                "exp_variant_id",
                "unit_type",
                "agg_type",
                "dimension",
                "dimension_value",
                "goal",
                "unit_id",
                "count",
                "sum_value",
            ]
        ]

    def _evaluate_metrics(self, goals: pd.DataFrame, column_fce) -> pd.DataFrame:
        if not self.metrics:
            return pd.DataFrame([], columns=Evaluation.metric_columns())

        sts = []
        for m in self.metrics:
            count, sum_value, sum_sqr_value = column_fce(m, goals)
            sts.append([count, sum_value, sum_sqr_value])
        stats = np.array(sts).transpose(0, 2, 1)
        metrics = stats.shape[0]
        variants = stats.shape[1]

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
                np.repeat([m.id for m in self.metrics], variants).reshape(metrics, variants, -1),
                np.repeat([m.name for m in self.metrics], variants).reshape(metrics, variants, -1),
                np.tile(goals["exp_variant_id"].unique(), metrics).reshape(metrics, variants, -1),
                stats,
            )
        )

        # dimensions of `stats` array: (metrics, variants, stats)
        # elements of `stats` array: metrics_id, exp_variant_id, count, mean, std, sum_value, confidence_level
        # hypothesis evaluation (standard way using t-test)
        c = Statistics.ttest_evaluation(stats)

        # multiple variants (comparisons) correction - applied when we have multiple treatment variants
        if variants > 2:
            c = Statistics.multiple_comparisons_correction(c, variants, metrics, confidence_level)

        c["exp_id"] = self.id
        c["timestamp"] = round(get_utc_timestamp(datetime.now()).timestamp())
        return c[Evaluation.metric_columns()]
