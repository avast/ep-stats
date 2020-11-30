import pandas as pd

from ..dao import Dao
from ..dao import DaoFactory
from ..experiment import Experiment
from ..experiment import Evaluation
from ..experiment import FilterScope
from .test_data import TestData


class TestDao(Dao):
    def __init__(self, test_data: TestData):
        self.metrics = pd.DataFrame({}, columns=Evaluation.metric_columns())
        self.checks = pd.DataFrame({}, columns=Evaluation.check_columns())
        self.test_data = test_data
        self.goals_agg = self.test_data.load_goals_agg()
        self.goals_unit = self.test_data.load_goals_by_unit()

    def get_agg_goals(self, experiment: Experiment) -> pd.DataFrame:
        goals = self.goals_agg[self.goals_agg.exp_id == experiment.id]

        # We can call experiment in 3 ways:
        # 1. provide no `date_from` and `date_to` to evaluate all the experiment data regardless of any date range
        # 2. provide either `date_from` or `date_to` to limit date range from the bottom or from the top
        # 3. provide both `date_from` or `date_to` signaling request for sequential analysis which needs also `date_for`
        # We take min from date_to and date_for in case we evaluate historical experiment where date_for >> date_to
        # already.
        if experiment.date_from is not None and experiment.date_to is not None:
            goals = goals[
                (goals.date >= experiment.date_from.strftime("%Y-%m-%d"))
                & (goals.date <= experiment.date_to.strftime("%Y-%m-%d"))
                & (goals.date <= experiment.date_for.strftime("%Y-%m-%d"))
            ]
        if experiment.date_from is not None:
            goals = goals[goals.date >= experiment.date_from.strftime("%Y-%m-%d")]
        if experiment.date_to is not None:
            goals = goals[goals.date <= experiment.date_to.strftime("%Y-%m-%d")]

        for f in experiment.filters:
            if f.scope == FilterScope.exposure:
                goals = goals[(goals.goal != "exposure") | (goals[f.dimension].isin(f.value))]
            if f.scope == FilterScope.goal:
                goals = goals[(goals.goal == "exposure") | (goals[f.dimension].isin(f.value))]

        return goals

    def get_unit_goals(self, experiment: Experiment) -> pd.DataFrame:
        return self.goals_unit[self.goals_unit.exp_id == experiment.id]

    def load_evaluations_metrics(self, experiment_id: str) -> pd.DataFrame:
        return self.test_data.load_evaluations_metrics(experiment_id)

    def load_evaluations_checks(self, experiment_id: str) -> pd.DataFrame:
        return self.test_data.load_evaluations_checks(experiment_id)

    def load_evaluations_exposures(self, experiment_id: str) -> pd.DataFrame:
        return self.test_data.load_evaluations_exposures(experiment_id)


class TestDaoFactory(DaoFactory):
    def __init__(self, test_data: TestData) -> None:
        self._client = TestDao(test_data)

    def get_dao(self) -> Dao:
        return self._client
