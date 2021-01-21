import pandas as pd

import importlib_resources as pkg_resources
from . import resources  # relative-import the *package* containing the templates


class TestData:
    """
    Utility methods to load sample (test) data that are used in unit tests through this
    project.
    """

    @classmethod
    def load_goals_agg(cls, exp_id: str = None) -> pd.DataFrame:
        """
        Load sample of aggregated test data to evaluate metrics. We use this dataset
        in unit testing and we are making it available here for other possible use-cases too.

        See `load_evaluations` set of functions to load corresponding evaluation results.

        Arguments:
            exp_id: experiment id
        """
        df = pd.read_csv(pkg_resources.open_text(resources, "goals_agg.csv"), sep="\t").fillna(
            {"dimension": "", "dimension_value": ""}
        )
        return df[df.exp_id == exp_id] if exp_id is not None else df

    @classmethod
    def load_goals_by_unit(cls, exp_id: str = None) -> pd.DataFrame:
        """
        Load sample of test data by unit to evaluate metrics. We use this dataset
        in unit testing and we are making it available here for other possible use-cases too.

        See `load_evaluations` set of functions to load corresponding evaluation results.

        Arguments:
            exp_id: experiment id
        """
        df = pd.read_csv(pkg_resources.open_text(resources, "goals_by_unit.csv"), sep="\t").fillna(
            {"dimension": "", "dimension_value": ""}
        )
        return df[df.exp_id == exp_id] if exp_id is not None else df

    @classmethod
    def load_evaluations_checks(cls, exp_id: str = None) -> pd.DataFrame:
        """
        Load checks (SRM) evaluations results. This data can be used to do asserts against
        after running evaluation on [pre-aggregated][epstats.toolkit.testing.test_data.TestData.load_goals_agg]
        or [by-unit][epstats.toolkit.testing.test_data.TestData.load_goals_by_unit] test data.

        Arguments:
            exp_id: experiment id
        """
        df = pd.read_csv(pkg_resources.open_text(resources, "evaluations_checks.csv"), sep="\t")
        return df[df.exp_id == exp_id] if exp_id is not None else df

    @classmethod
    def load_evaluations_exposures(cls, exp_id: str = None) -> pd.DataFrame:
        """
        Load exposures evaluations results. This data can be used to do asserts against
        after running evaluation on [pre-aggregated][epstats.toolkit.testing.test_data.TestData.load_goals_agg]
        or [by-unit][epstats.toolkit.testing.test_data.TestData.load_goals_by_unit] test data.

        Arguments:
            exp_id: experiment id
        """
        df = pd.read_csv(pkg_resources.open_text(resources, "evaluations_exposures.csv"), sep="\t")
        return df[df.exp_id == exp_id] if exp_id is not None else df

    @classmethod
    def load_evaluations_metrics(cls, exp_id: str = None) -> pd.DataFrame:
        """
        Load metric evaluations results. This data can be used to do asserts against
        after running evaluation on [pre-aggregated][epstats.toolkit.testing.test_data.TestData.load_goals_agg]
        or [by-unit][epstats.toolkit.testing.test_data.TestData.load_goals_by_unit] test data.

        Arguments:
            exp_id: experiment id
        """
        df = pd.read_csv(pkg_resources.open_text(resources, "evaluations_metrics.csv"), sep="\t")
        return df[df.exp_id == exp_id] if exp_id is not None else df
