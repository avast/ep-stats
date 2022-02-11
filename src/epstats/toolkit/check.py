from typing import List
import pandas as pd
import numpy as np
from scipy.stats import chisquare

from .parser import Parser


class Check:
    """
    Perform data quality check that accompanies metric evaluation in the experiment.

    See [Data Quality Checks](../stats/basics.md#data-quality-checks) for details about
    data quality checks and [`Evaluation`][epstats.toolkit.experiment.Evaluation] for description of output.
    """

    def __init__(self, id: int, name: str, denominator: str, **unused_kwargs):
        self.id = id
        self.name = name
        self.denominator = denominator
        self._denominator_parser = Parser(denominator, denominator)
        self._goals = self._denominator_parser.get_goals()

    def get_goals(self) -> List:
        """
        List of all goals needed to evaluate the check in the experiment.

        Returns:
            list of parsed structured goals
        """
        return self._goals

    def evaluate_agg(self, goals: pd.DataFrame, default_exp_variant_id: str) -> pd.DataFrame:
        """
        Evaluate this check from pre-aggregated goals.

        Arguments:
            goals: one row per experiment variant
            default_exp_variant_id: default variant

        See [`Experiment.evaluate_agg`][epstats.toolkit.experiment.Experiment.evaluate_agg] for details
        on `goals` at input.

        Returns:
            `checks` dataframe with columns:

        `checks` dataframe with columns:

        1. `timestamp` - timestamp of evaluation
        1. `exp_id` - experiment id
        1. `check_id` - check id as in [`Experiment`][epstats.toolkit.experiment.Experiment] definition
        1. `variable_id` - name of the variable in check evaluation, SRM check has following variables `p_value`,
        `test_stat`, `confidence_level`
        1. `value` - value of the variable
        """
        raise NotImplementedError()

    def evaluate_by_unit(self, goals: pd.DataFrame, default_exp_variant_id: str) -> pd.DataFrame:
        """
        Evaluate this check from goals aggregated by unit.

        Arguments:
            goals: ne row per experiment variant
            default_exp_variant_id: default variant

        See [`Experiment.evaluate_by_unit`][epstats.toolkit.experiment.Experiment.evaluate_by_unit] for details
        on `goals` at input.

        Returns:
            `checks` dataframe with columns:

        `checks` dataframe with columns:

        1. `timestamp` - timestamp of evaluation
        1. `exp_id` - experiment id
        1. `check_id` - check id as in [`Experiment`][epstats.toolkit.experiment.Experiment] definition
        1. `variable_id` - name of the variable in check evaluation, SRM check has following variables `p_value`,
        `test_stat`, `confidence_level`
        1. `value` - value of the variable
        """
        raise NotImplementedError()


class SrmCheck(Check):
    """
    [Sample ratio mismatch check](../stats/basics.md#sample-ratio-mismatch-check) checking randomization
    of units to variants using [Chi-square test](https://en.wikipedia.org/wiki/Chi-squared_test).
    """

    def __init__(
        self,
        id: int,
        name: str,
        denominator: str,
        confidence_level: float = 0.999,
        **unused_kwargs,
    ):
        """
        Constructor of the SRM check.

        Arguments:
            id: check (order) id
            name: check name
            denominator: values to check
            confidence_level: confidence level of the statistical test

        Usage:
        ```python
        SrmCheck(1, 'SRM', 'count(test_unit_type.global.exposure)')
        ```
        """
        super().__init__(id, name, denominator)
        self.confidence_level = confidence_level

    def evaluate_agg(self, goals: pd.DataFrame, default_exp_variant_id: str) -> pd.DataFrame:
        """
        See [`Check.evaluate_agg`][epstats.toolkit.check.Check.evaluate_agg].
        """
        # input example:
        # test - srm, a, global.exposure, 10000, 10010, 10010, 0.0, 0.0
        # test - srm, b, global.exposure, 10010, 10010, 10010, 0.0, 0.0
        # test - srm, c, global.exposure, 10040, 10040, 10040, 0.0, 0.0

        # output example:
        # test - srm, 1, SRM, p_value, 0.20438
        # test - srm, 1, SRM, test_stat, 3.17552
        # test - srm, 1, SRM, confidence_level, 0.999

        # prepare data - we only need exposures
        exposures, _, _ = self._denominator_parser.evaluate_agg(goals)

        # chi-square test
        with np.errstate(divide="ignore", invalid="ignore"):
            # we fill in zeros, when goal data are missing for some variant.
            # There could be division by zero here which is expected as we return
            # nan or inf values to the caller.
            stat, pval = chisquare(exposures)

        r = pd.DataFrame(
            {
                "check_id": [self.id, self.id, self.id],
                "check_name": [self.name, self.name, self.name],
                "variable_id": ["p_value", "test_stat", "confidence_level"],
                "value": [pval, stat, self.confidence_level],
            }
        )
        return r

    def evaluate_by_unit(self, goals: pd.DataFrame, default_exp_variant_id: str) -> pd.DataFrame:
        """
        See [`Check.evaluate_by_unit`][epstats.toolkit.check.Check.evaluate_by_unit].
        """

        exposures, _, _ = self._denominator_parser.evaluate_by_unit(goals)

        # chi-square test
        stat, pval = chisquare(exposures)

        r = pd.DataFrame(
            {
                "check_id": [self.id, self.id, self.id],
                "check_name": [self.name, self.name, self.name],
                "variable_id": ["p_value", "test_stat", "confidence_level"],
                "value": [pval, stat, self.confidence_level],
            }
        )
        return r


class SimpleSrmCheck(SrmCheck):
    """Simplified definition of SRM check."""

    def __init__(
        self,
        id: int,
        name: str,
        denominator: str,
        confidence_level: float = 0.999,
        unit_type: str = "test_unit_type",
    ):
        """
        Constructor of the simplified SRM check.

        It modifies parameter denominator in a way that it is in line with general SRM Check definition. It adds all
        the niceties necessary for proper SrmCheck format. Finaly it calls constructor of the parent SrmCheck class.

        Arguments:
            id: check (order) id
            name: check name
            denominator: value (column) of the denominator
            confidence_level: confidence level of the statistical test
            unit_type: unit type

        Usage:
        ```python
        SimpleSrmCheck(1, 'SRM', 'exposures')
        ```
        """
        agg_type = "global"
        den = "value" + "(" + unit_type + "." + agg_type + "." + denominator + ")"
        super().__init__(id, name, den, confidence_level)


class SumRatioCheck(Check):
    """
    Computes the ratio of `nominator`, `denominator` goal counts summed across all variants.

    [Max ratio check](../stats/basics.md#sum-ratio-check).
    """

    def __init__(
        self,
        id: int,
        name: str,
        nominator: str,
        denominator: str,
        max_sum_ratio: float = 0.01,
        confidence_level: float = 0.999,
        **unused_kwargs,
    ):
        """
        Constructor of the check.

        Arguments:
            id: check (order) id
            name: check name
            nominator:  goal in the ratio numerator
            denominator: goal in the ratio denominitaor
            max_sum_ratio: maximum allowed sum_ratio value
            confidence_level: confidence level of the statistical test

        Usage:
        ```python
        SumRatioCheck(
            1,
            "SumRatio",
            "count(test_unit_type.global.inconsistent_exposure)",
            "count(test_unit_type.global.exposure)"
        )
        ```
        """
        super().__init__(id, name, denominator)
        self.max_sum_ratio = max_sum_ratio
        self.confidence_level = confidence_level
        self._nominator = nominator
        self._nominator_parser = Parser(nominator, nominator)
        self._goals = self._goals.union(self._nominator_parser.get_goals())

    def evaluate_agg(self, goals: pd.DataFrame, default_exp_variant_id: str) -> pd.DataFrame:
        """
        See [`Check.evaluate_agg`][epstats.toolkit.check.Check.evaluate_agg].
        """

        denominator_counts, _, _ = self._denominator_parser.evaluate_agg(goals)
        nominator_counts, _, _ = self._nominator_parser.evaluate_agg(goals)

        # chi-square test
        with np.errstate(divide="ignore", invalid="ignore"):
            sum_ratio = nominator_counts.sum() / denominator_counts.sum()

            stat, pval = chisquare([denominator_counts.sum(), denominator_counts.sum() - nominator_counts.sum()])

        r = pd.DataFrame(
            {
                "check_id": self.id,
                "check_name": self.name,
                "variable_id": [
                    "sum_ratio",
                    "max_sum_ratio",
                    "p_value",
                    "test_stat",
                    "confidence_level",
                ],
                "value": [
                    sum_ratio,
                    self.max_sum_ratio,
                    pval,
                    stat,
                    self.confidence_level,
                ],
            }
        )
        return r
