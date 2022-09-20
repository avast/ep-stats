from typing import Set, Optional
import pandas as pd
import numpy as np

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
    ):
        """
        Constructor of the general metric definition.

        Parameters `nominator` and `denominator` specify exactly type of data and aggregation of the metric nominator
        and denominator.

        Parameters `format` and `multiplier` does not play any role in metric evaluation. They are used independently
        after the metric evaluation.

        Arguments:
            id: metric (order) id
            name: metric name
            nominator: definition of nominator
            denominator: definition of denominator
            metric_format: specify format of the metric, e.g. '${:,.1f}' for RPM
            metric_value_multiplier: specify multiplier, e.g. 1000 for RPM

        Usage:

        ```python
        Metric(
            1,
            'Click-through Rate',
            'count(test_unit_type.unit.click)',
            'count(test_unit_type.global.exposure)')
        ```
        """

        self.id = id
        self.name = name
        self.nominator = nominator
        self.denominator = denominator
        self._parser = Parser(nominator, denominator)
        self._goals = self._parser.get_goals()
        self.metric_format = metric_format
        self.metric_value_multiplier = metric_value_multiplier
        self.minimum_effect = minimum_effect

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
        """
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
        return self._parser.evaluate_by_unit(goals)


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

        super().__init__(id, name, num, den, metric_format, metric_value_multiplier, minimum_effect)
