import numpy as np
import pytest
from statsmodels.stats.power import TTestIndPower

from src.epstats.toolkit.statistics import Statistics


def _assert_sample_sizes_equal(x, y):
    assert abs(x - y) <= 2


def _assert_sample_sizes_equal_within_tolerance(x, y, n_variants):
    # Booking calculator is using Sidak's correction instead of Bonferroni's,
    # https://github.com/bookingcom/powercalculator/blob/master/src/js/math.js#L303
    # it produces slightly different results in case of multiple variants.
    # The difference is less than 0.5%.
    if n_variants > 2:
        rel_tol = 0.005
        assert abs((x - y) / x) <= rel_tol
    else:
        _assert_sample_sizes_equal(x, y)


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
    # expected from https://bookingcom.github.io/powercalculator
    "n_variants, minimum_effect, mean, std, expected",
    [
        (2, 0.10, 0.2, 1.2, 56512),
        (2, 0.10, 0.2, 2.0, 156978),
        (2, 0.10, 0.3, 1.2, 25117),
        (2, 0.10, 0.3, 2.0, 69768),
        (2, 0.05, 0.2, 1.2, 226048),
        (2, 0.05, 0.2, 2.0, 627911),
        (2, 0.05, 0.3, 1.2, 100466),
        (2, 0.05, 0.3, 2.0, 279072),
        (3, 0.05, 0.3, 2.0, 336878),
        (3, 0.10, 0.2, 1.2, 68218),
        (4, 0.10, 0.2, 2.0, 208576),
    ],
)
def test_required_sample_size_per_variant_equal_variance(n_variants, minimum_effect, mean, std, expected):
    sample_size_per_variant = Statistics.required_sample_size_per_variant(
        n_variants=n_variants,
        minimum_effect=minimum_effect,
        mean=mean,
        std=std,
    )
    effect_size = (mean * (1 + minimum_effect) - mean) / std

    # nobs1
    expected_from_statsmodels = TTestIndPower().solve_power(
        effect_size=effect_size,
        ratio=1.0,  # N_A / N_B
        alpha=0.05 / (n_variants - 1),
        power=0.8,
        nobs1=None,
    )

    _assert_sample_sizes_equal(sample_size_per_variant, round(expected_from_statsmodels))
    _assert_sample_sizes_equal_within_tolerance(sample_size_per_variant, expected, n_variants)


@pytest.mark.parametrize(
    "minimum_effect, mean, std, std_2",
    [
        (0.10, 0.2, 1.2, 2.0),
        (0.05, 0.3, 2.0, 2.5),
    ],
)
def test_required_sample_size_per_variant_unequal_variance(minimum_effect, mean, std, std_2):
    sample_size_per_variant = Statistics.required_sample_size_per_variant(
        n_variants=2,
        minimum_effect=minimum_effect,
        mean=mean,
        std=std,
        std_2=std_2,
    )

    mean_2 = mean * (1 + minimum_effect)
    var_ = (std**2 + std_2**2) / 2
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

    _assert_sample_sizes_equal(sample_size_per_variant, round(expected_from_statsmodels))


@pytest.mark.parametrize(
    # expected from https://bookingcom.github.io/powercalculator
    "n_variants, minimum_effect, mean, std, expected",
    [
        (2, 0.05, 0.4, None, 9490),
        (2, 0.10, 0.1, None, 14749),
        (3, 0.05, 0.4, None, 11455),
        (4, 0.10, 0.1, None, 19596),
    ],
)
def test_required_sample_size_per_variant_bernoulli(n_variants, minimum_effect, mean, std, expected):
    sample_size_per_variant = Statistics.required_sample_size_per_variant_bernoulli(
        n_variants=n_variants,
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
        alpha=0.05 / (n_variants - 1),
        power=0.8,
        nobs1=None,
    )

    _assert_sample_sizes_equal(sample_size_per_variant, round(expected_from_statsmodels))
    _assert_sample_sizes_equal_within_tolerance(sample_size_per_variant, expected, n_variants)


@pytest.mark.parametrize(
    "n_variants, minimum_effect, mean, std, f",
    [
        (2, -0.1, 0.2, 1.2, Statistics.required_sample_size_per_variant),
        (1, -0.1, 0.2, 1.2, Statistics.required_sample_size_per_variant),
        (2, 0.1, 10.1, None, Statistics.required_sample_size_per_variant_bernoulli),
    ],
)
def test_required_sample_size_per_variant_raises_exception(n_variants, minimum_effect, mean, std, f):
    args = {"minimum_effect": minimum_effect, "mean": mean, "n_variants": n_variants}

    if std is not None:
        args["std"] = std

    with pytest.raises(ValueError):
        f(**args)


@pytest.mark.parametrize(
    "minimum_effect, mean, std, expected",
    [
        (0.1, 0, 0, np.isnan),
        (0.1, np.nan, np.nan, np.isnan),
        (0.1, 0, np.nan, np.isnan),
        (0.1, 0, 1, np.isinf),
        (np.nan, np.nan, np.nan, np.isnan),
    ],
)
def test_required_sample_size_per_variant_not_valid(minimum_effect, mean, std, expected):
    assert expected(
        Statistics.required_sample_size_per_variant(
            minimum_effect=minimum_effect,
            mean=mean,
            std=std,
            n_variants=2,
        )
    )


@pytest.mark.parametrize(
    "n_variants, sample_size_per_variant",
    [
        (2, 400000),
        (2, 200000),
        (2, 627911),
        (3, 500000),
        (4, 300000),
    ],
)
def test_power_from_required_sample_size_per_variant(n_variants, sample_size_per_variant):
    mean = 0.2
    std = 2.0
    minimum_effect = 0.05
    required_sample_size_per_variant = Statistics.required_sample_size_per_variant(
        n_variants=n_variants,
        std=std,
        mean=mean,
        minimum_effect=minimum_effect,
    )

    expected = TTestIndPower().solve_power(
        effect_size=(mean * (1 + minimum_effect) - mean) / std,
        ratio=1.0,
        alpha=0.05 / (n_variants - 1),
        power=None,
        nobs1=sample_size_per_variant,
    )

    power = Statistics.power_from_required_sample_size_per_variant(
        n_variants=n_variants,
        sample_size_per_variant=sample_size_per_variant,
        required_sample_size_per_variant=required_sample_size_per_variant,
    )

    assert np.allclose(power, expected, atol=1e-3)


def test_power_from_required_sample_size_per_variant_nan_params():
    assert np.isnan(
        Statistics.power_from_required_sample_size_per_variant(
            n_variants=np.nan,
            sample_size_per_variant=np.nan,
            required_sample_size_per_variant=np.nan,
        )
    )


@pytest.mark.parametrize(
    "args",
    [
        {
            "n_variants": 1,
            "sample_size_per_variant": 100,
            "required_sample_size_per_variant": 100,
        },
        {
            "n_variants": 2,
            "sample_size_per_variant": 0,
            "required_sample_size_per_variant": 0,
        },
    ],
)
def test_power_from_required_sample_size_per_variant_is_nan(args):
    assert np.isnan(Statistics.power_from_required_sample_size_per_variant(**args))
