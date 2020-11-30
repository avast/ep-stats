import pytest

from epstats.toolkit.experiment import Experiment
from epstats.toolkit.check import SrmCheck
from epstats.toolkit.testing import evaluate_experiment_agg, TestDao, TestData


@pytest.fixture(scope="module")
def dao():
    return TestDao(TestData())


@pytest.fixture(scope="module")
def metrics():
    return []


@pytest.fixture(scope="module")
def checks():
    return [SrmCheck(1, "SRM", "count(test_unit_type.global.exposure)")]


# Testing standard input - no SRM detected
def test_srm(dao, metrics, checks):
    experiment = Experiment("test-srm", "a", metrics, checks, unit_type="test_unit_type")
    evaluate_experiment_agg(experiment, dao)


# Testing standard input - SRM detected
def test_srm_negative(dao, metrics, checks):
    experiment = Experiment("test-srm-negative", "a", metrics, checks, unit_type="test_unit_type")
    evaluate_experiment_agg(experiment, dao)


# Testing one-variant test, e.g. A/A test - NaN output expected
def test_srm_one_variant(dao, metrics, checks):
    experiment = Experiment("test-srm-one-variant", "a", metrics, checks, unit_type="test_unit_type")
    evaluate_experiment_agg(experiment, dao)
