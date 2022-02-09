import pytest

from src.epstats.toolkit.experiment import Experiment
from src.epstats.toolkit.check import SrmCheck, MaxRatioCheck
from src.epstats.toolkit.testing import evaluate_experiment_agg, TestDao, TestData


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
def max_ratio_check():
    return [
        MaxRatioCheck(
            1,
            "MaxRatio",
            "count(test_unit_type.global.inconsistent_exposure)",
            "count(test_unit_type.global.exposure)",
        )
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


# Testing standard input - no SRM detected
def test_max_ratio(dao, metrics, max_ratio_check):
    experiment = Experiment("test-max-ratio", "a", metrics, max_ratio_check, unit_type="test_unit_type")
    evaluate_experiment_agg(experiment, dao)
