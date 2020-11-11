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

    id: int
    name: str
    denominator: str

    def __init__(self, id: int, name: str, denominator: str):
        super().__init__()

        self.id = id
        self.name = name
        self.denominator = denominator
        self._parser = Parser(denominator, denominator)
        self._goals = self._parser.get_goals()

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
    ):
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
        exposures, _, _ = self._parser.evaluate_agg(goals)

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

        exposures, _, _ = self._parser.evaluate_by_unit(goals)

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
