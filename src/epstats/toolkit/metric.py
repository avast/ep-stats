from typing import Set
import pandas as pd

from .parser import Parser


class Metric:
    """
    Definition of a metric to evaluate in an experiment.
    """

    id: int
    name: str
    nominator: str
    denominator: str

    def __init__(self, id: int, name: str, nominator: str, denominator: str):
        super().__init__()

        self.id = id
        self.name = name
        self.nominator = nominator
        self.denominator = denominator
        self._parser = Parser(nominator, denominator)
        self._goals = self._parser.get_goals()

    def get_goals(self) -> Set:
        """
        Get all goals needed to evaluate the metric.
        """
        return self._goals

    def get_evaluate_columns_agg(self, goals: pd.DataFrame):
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
        """
        return self._parser.evaluate_agg(goals)

    def get_evaluate_columns_by_unit(self, goals: pd.DataFrame):
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
        return self._parser.evaluate_by_unit(goals)
