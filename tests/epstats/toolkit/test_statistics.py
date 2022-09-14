import pytest
import numpy as np
from statsmodels.stats.power import TTestIndPower
from src.epstats.toolkit.statistics import Statistics


def _assert_equal(x, y, abs_tol=1):
    assert abs(x - y) <= abs_tol


@pytest.mark.parametrize(
    "test_length, actual_day, expected",
    [
        (14, 0, 1.00),
        (14, 1, 1.00),
        (14, 2, 1.00),
        (14, 3, 1.00),
        (14, 14, 0.95),
        (7, 1, 1.00),
        (28, 4, 1.00),
        (28, 8, 0.9998),
        (28, 28, 0.95),
    ],
)
def test_obf_alpha_spending_function(test_length, actual_day, expected):

    alpha = Statistics.obf_alpha_spending_function(0.95, test_length, actual_day)
    assert alpha == expected


@pytest.mark.parametrize(
    "minimum_effect, mean, std, expected",
    [
        (0.10, 0.2, 1.2, 56512),
        (0.10, 0.2, 2.0, 156978),
        (0.10, 0.3, 1.2, 25117),
        (0.10, 0.3, 2.0, 69768),
        (0.05, 0.2, 1.2, 226048),
        (0.05, 0.2, 2.0, 627911),
        (0.05, 0.3, 1.2, 100466),
        (0.05, 0.3, 2.0, 279072),
    ],
)
def test_required_sample_size_per_variant_equal_variance(minimum_effect, mean, std, expected):
    # expected from https://bookingcom.github.io/powercalculator

    sample_size_per_variant = Statistics.required_sample_size_per_variant(
        minimum_effect=minimum_effect,
        mean=mean,
        std=std,
    )
    effect_size = (mean * (1 + minimum_effect) - mean) / std

    # nobs1
    expected_from_statsmodels = TTestIndPower().solve_power(
        effect_size=effect_size,
        ratio=1.0,  # N_A / N_B
        alpha=0.05,
        power=0.8,
        nobs1=None,
    )

    expected_from_statsmodels = round(expected_from_statsmodels)

    _assert_equal(sample_size_per_variant, expected_from_statsmodels)
    _assert_equal(sample_size_per_variant, expected)


@pytest.mark.parametrize(
    "minimum_effect, mean, std, std_2",
    [
        (0.10, 0.2, 1.2, 2.0),
        (0.05, 0.3, 2.0, 2.5),
    ],
)
def test_required_sample_size_per_variant_unequal_variance(minimum_effect, mean, std, std_2):

    sample_size_per_variant = Statistics.required_sample_size_per_variant(
        minimum_effect=minimum_effect,
        mean=mean,
        std=std,
        std_2=std_2,
    )

    mean_2 = mean * (1 + minimum_effect)
    var_ = (std ** 2 + std_2 ** 2) / 2
    std_ = np.sqrt(var_)
    effect_size = (mean_2 - mean) / std_

    # nobs1
    expected_from_statsmodels = TTestIndPower().solve_power(
        effect_size=effect_size,
        ratio=1.0,  # N_A / N_B
        alpha=0.05,
        power=0.8,
        nobs1=None,
    )

    _assert_equal(sample_size_per_variant, round(expected_from_statsmodels))


@pytest.mark.parametrize(
    "minimum_effect, mean, std, expected",
    [
        (0.05, 0.4, None, 9490),
        (0.10, 0.1, None, 14749),
    ],
)
def test_required_sample_size_per_variant_bernoulli(minimum_effect, mean, std, expected):
    # expected from https://bookingcom.github.io/powercalculator

    sample_size_per_variant = Statistics.required_sample_size_per_variant_bernoulli(
        minimum_effect=minimum_effect,
        mean=mean,
    )

    mean_2 = mean * (1 + minimum_effect)
    var = mean * (1 - mean)
    var_2 = mean_2 * (1 - mean_2)
    std = np.sqrt((var + var_2) / 2)

    effect_size = (mean_2 - mean) / std

    # nobs1
    expected_from_statsmodels = TTestIndPower().solve_power(
        effect_size=effect_size,
        ratio=1.0,
        alpha=0.05,
        power=0.8,
        nobs1=None,
    )

    expected_from_statsmodels = round(expected_from_statsmodels)

    _assert_equal(sample_size_per_variant, expected_from_statsmodels)
    _assert_equal(sample_size_per_variant, expected)


@pytest.mark.parametrize(
    "minimum_effect, mean, std, f",
    [
        (-0.1, 0.2, 1.2, Statistics.required_sample_size_per_variant),
        (-0.1, 0.2, None, Statistics.required_sample_size_per_variant_bernoulli),
        (0.1, 10.1, None, Statistics.required_sample_size_per_variant_bernoulli),
    ],
)
def test_required_sample_size_per_variant_raises_exception(minimum_effect, mean, std, f):

    args = {"minimum_effect": minimum_effect, "mean": mean}

    if std is not None:
        args["std"] = std

    with pytest.raises(ValueError):
        f(**args)
