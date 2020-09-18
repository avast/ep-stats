import pandas as pd

from .experiment import Experiment


class Dao:
    """
    Abstract class interfacing any kind of underlying data source.
    """

    def get_unit_goals(self, experiment: Experiment) -> pd.DataFrame:
        """
        Get goals data pre-aggregated by columns `exp_variant_id`, `unit_type`, `agg_type`, `goal`,
        `dimension`, `dimension_value` and `unit_id`.

        See [`Experiment.evaluate_by_unit`][epstats.toolkit.experiment.Experiment.evaluate_by_unit] for column
        descriptions and example result.
        """
        pass

    def get_agg_goals(self, experiment: Experiment) -> pd.DataFrame:
        """
        Get goals data pre-aggregated by columns `exp_variant_id`, `unit_type`, `agg_type`, `goal`,
        `dimension`, `dimension_value`.

        See [`Experiment.evaluate_agg`][epstats.toolkit.experiment.Experiment.evaluate_agg] for column
        descriptions and example result.
        """
        pass

    def close(self) -> None:
        """
        Close underlying data source connection and frees resources (if any).
        """
        pass


class DaoFactory:
    """
    Factory creating instances of [`Dao`][epstats.toolkit.dao.Dao] classes.

    It is used in API server to get dao for every request.
    """

    def get_dao(self) -> Dao:
        """
        Create new instance of [`Dao`][epstats.toolkit.dao.Dao] to serve the request.
        """
        pass
