import pytest

from src.epstats.toolkit.check import SrmCheck, SumRatioCheck
from src.epstats.toolkit.experiment import Experiment
from src.epstats.toolkit.testing import TestDao, TestData, evaluate_experiment_agg


@pytest.fixture(scope="module")
def dao():
    return TestDao(TestData())


@pytest.fixture(scope="module")
def metrics():
    return []


@pytest.fixture(scope="module")
def srm_check():
    return [SrmCheck(1, "SRM", "count(test_unit_type.global.exposure)")]


@pytest.fixture(scope="module")
def sum_ratio_check():
    return [
        SumRatioCheck(
            1,
            "EVA",
            "count(test_unit_type.global.inconsistent_exposure)",
            "count(test_unit_type.global.exposure)",
        )
    ]


@pytest.fixture(scope="module")
def checks():
    return [
        SumRatioCheck(
            1,
            "SumRatio",
            "count(test_unit_type.global.inconsistent_exposure)",
            "count(test_unit_type.global.exposure)",
        ),
        SrmCheck(2, "SRM", "count(test_unit_type.global.exposure)"),
    ]


# Testing standard input - no SRM detected
def test_srm(dao, metrics, srm_check):
    experiment = Experiment("test-srm", "a", metrics, srm_check, unit_type="test_unit_type")
    evaluate_experiment_agg(experiment, dao)


# Testing standard input - SRM detected
def test_srm_negative(dao, metrics, srm_check):
    experiment = Experiment("test-srm-negative", "a", metrics, srm_check, unit_type="test_unit_type")
    evaluate_experiment_agg(experiment, dao)


# Testing one-variant test, e.g. A/A test - NaN output expected
def test_srm_one_variant(dao, metrics, srm_check):
    experiment = Experiment("test-srm-one-variant", "a", metrics, srm_check, unit_type="test_unit_type")
    evaluate_experiment_agg(experiment, dao)


def test_sum_ratio(dao, metrics, sum_ratio_check):
    experiment = Experiment("test-sum-ratio", "a", metrics, sum_ratio_check, unit_type="test_unit_type")
    evaluate_experiment_agg(experiment, dao)


def test_multi_check(dao, metrics, checks):
    experiment = Experiment("test-multi-check", "a", metrics, checks, unit_type="test_unit_type")
    evaluate_experiment_agg(experiment, dao)
