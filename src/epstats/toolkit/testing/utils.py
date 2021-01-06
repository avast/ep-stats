import pandas as pd
from numpy import allclose
from numpy.testing import assert_array_equal, assert_array_almost_equal

from ..experiment import Experiment, Evaluation
from .test_dao import TestDao


def evaluate_experiment_agg(experiment: Experiment, test_dao: TestDao):
    goals = test_dao.get_agg_goals(experiment)
    goals = goals[goals.exp_id == experiment.id]

    target = experiment.evaluate_agg(goals)

    assert_experiment(experiment, target, test_dao)

    return target


def evaluate_experiment_by_unit(experiment: Experiment, test_dao: TestDao):
    goals = test_dao.get_unit_goals(experiment)
    goals = goals[goals.exp_id == experiment.id]

    target = experiment.evaluate_by_unit(goals)

    assert_experiment(experiment, target, test_dao)

    return target


def assert_experiment(experiment: Experiment, target: Evaluation, test_dao: TestDao) -> None:
    metrics = target.metrics
    for m in experiment.metrics:
        assert_metrics(experiment.id, m.id, metrics, test_dao)

    checks = target.checks
    for c in experiment.checks:
        assert_checks(experiment.id, c.id, checks, test_dao)

    assert_exposures(experiment.id, target.exposures, test_dao, unit_type=experiment.unit_type)


def assert_metrics(
    experiment_id: str,
    metric_id: int,
    target: pd.DataFrame,
    test_dao: TestDao,
    precision=3,
) -> None:
    target = target[(target.exp_id == experiment_id) & (target.metric_id == metric_id)]

    expected = test_dao.load_evaluations_metrics(experiment_id)
    expected = expected[expected.metric_id == metric_id]

    assert_array_equal(target.exp_variant_id, expected.exp_variant_id)
    t = target[
        [
            "sum_value",
            "diff",
            "mean",
            "p_value",
            "confidence_interval",
            "confidence_level",
        ]
    ].astype(float)
    atol = 10 ** -precision
    assert allclose(t["sum_value"], expected["sum_value"], atol=atol, equal_nan=True)
    assert allclose(t["diff"], expected["diff"], atol=atol, equal_nan=True)
    assert allclose(t["mean"], expected["mean"], atol=atol, equal_nan=True)
    assert allclose(t["p_value"], expected["p_value"], atol=atol * 10, equal_nan=True)
    assert allclose(t["confidence_interval"], expected["confidence_interval"], atol=atol * 10, equal_nan=True)
    assert allclose(t["confidence_level"], expected["confidence_level"], atol=atol, equal_nan=True)


def assert_checks(
    experiment_id: str,
    check_id: int,
    target: pd.DataFrame,
    test_dao: TestDao,
    precision: int = 4,
) -> None:
    target = target[(target.exp_id == experiment_id) & (target.check_id == check_id)]

    expected = test_dao.load_evaluations_checks(experiment_id)
    expected = expected[expected.check_id == check_id]

    assert_array_equal(target.check_id, expected.check_id)
    assert_array_almost_equal(
        target[target["variable_id"] == "p_value"]["value"],
        expected[expected["variable_id"] == "p_value"]["value"],
        precision,
    )
    assert_array_almost_equal(
        target[target["variable_id"] == "test_stat"]["value"],
        expected[expected["variable_id"] == "test_stat"]["value"],
        precision,
    )
    assert_array_almost_equal(
        target[target["variable_id"] == "confidence_level"]["value"],
        expected[expected["variable_id"] == "confidence_level"]["value"],
        precision,
    )


def assert_exposures(
    experiment_id: str,
    target: pd.DataFrame,
    test_dao: TestDao,
    unit_type: str = "test_unit_type",
    agg_type: str = "global",
) -> None:
    expected = test_dao.load_evaluations_exposures(experiment_id)
    expected = (
        expected[(expected.unit_type == unit_type) & (expected.agg_type == agg_type) & (expected.goal == "exposure")]
        .groupby("exp_variant_id")
        .agg(exposures=("count", "sum"))
        .reset_index()
    )

    assert_array_equal(target.exp_variant_id, expected.exp_variant_id)
    assert_array_equal(target.exposures, expected.exposures)


def check_docstring(doc, indent):
    """
    This function will read through the docstring and grab
    the first python code block. It will try to execute it.
    If it fails, the calling test should raise a flag.
    """
    if not doc:
        return
    start = doc.find("```python\n")
    end = doc.find("```\n")
    if start != -1:
        if end != -1:
            code_part = doc[(start + 10) : end].replace(" " * indent, "")  # noqa: E203
            print(code_part)
            exec(code_part)
