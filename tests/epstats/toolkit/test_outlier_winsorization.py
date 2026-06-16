import pandas as pd
import pytest

from src.epstats.toolkit.experiment import Experiment
from src.epstats.toolkit.metric import Metric, SimpleMetric


def _by_unit_goals(units_per_variant: dict) -> pd.DataFrame:
    """
    Build a flat by-unit goals data frame (one row per unit and goal) from a mapping
    `{variant: [per-unit conversion value, ...]}`. Every unit gets one exposure.
    """
    rows = []
    unit_id = 0
    for variant, values in units_per_variant.items():
        for value in values:
            unit_id += 1
            common = dict(
                exp_id="test-outlier",
                exp_variant_id=variant,
                unit_type="test_unit_type",
                agg_type="unit",
                dimension="",
                dimension_value="",
                unit_id=unit_id,
            )
            rows.append({**common, "goal": "exposure", "count": 1, "sum_value": 1})
            rows.append(
                {**common, "goal": "conversion", "count": 1, "sum_value": value}
            )
    return pd.DataFrame(rows)


def _evaluate(goals, outlier_upper_percentile=None, outlier_lower_percentile=None):
    metric = Metric(
        1,
        "Average Bookings",
        "value(test_unit_type.unit.conversion)",
        "count(test_unit_type.unit.exposure)",
        outlier_upper_percentile=outlier_upper_percentile,
        outlier_lower_percentile=outlier_lower_percentile,
    )
    experiment = Experiment(
        "test-outlier", "a", [metric], [], unit_type="test_unit_type"
    )
    return experiment.evaluate_by_unit(goals).metrics.set_index("exp_variant_id")


def test_upper_winsorization_caps_outlier_and_keeps_units():
    # Variant `a` is clean, variant `b` has a single extreme outlier.
    goals = _by_unit_goals({"a": [10] * 100, "b": [10] * 99 + [100_000]})

    metrics = _evaluate(goals, outlier_upper_percentile=1)

    # The outlier in `b` is capped to the pooled upper threshold (10), but the unit is *kept*,
    # so the count / sample size is unchanged (this is the key difference from trimming).
    assert metrics.loc["a", "count"] == 100
    assert metrics.loc["a", "mean"] == pytest.approx(10)
    assert metrics.loc["b", "count"] == 100
    assert metrics.loc["b", "mean"] == pytest.approx(10)


def test_pooled_threshold_is_applied_identically_to_all_variants():
    # Each variant has the same clean values 1..50 plus a single (different) extreme outlier.
    clean = list(range(1, 51))
    goals = _by_unit_goals({"a": clean + [10_000], "b": clean + [20_000]})

    metrics = _evaluate(goals, outlier_upper_percentile=2)

    # The cap is the pooled 98th percentile (= 50), so both arms' outliers are capped to the same
    # absolute value. The two variants therefore evaluate identically despite different raw outliers.
    expected_sum = sum(clean) + 50  # the outlier is capped down to 50
    assert metrics.loc["a", "count"] == 51
    assert metrics.loc["b", "count"] == 51
    assert metrics.loc["a", "sum_value"] == pytest.approx(expected_sum)
    assert metrics.loc["b", "sum_value"] == pytest.approx(expected_sum)
    assert metrics.loc["a", "mean"] == pytest.approx(metrics.loc["b", "mean"])


def test_lower_winsorization_floors_low_values():
    goals = _by_unit_goals({"a": [10] * 100, "b": [10] * 99 + [-100_000]})

    metrics = _evaluate(goals, outlier_lower_percentile=1)

    # The extreme low value in `b` is floored to the pooled lower threshold (10), unit kept.
    assert metrics.loc["b", "count"] == 100
    assert metrics.loc["b", "mean"] == pytest.approx(10)


def test_winsorization_disabled_keeps_raw_values():
    goals = _by_unit_goals({"a": [10] * 100, "b": [10] * 99 + [100_000]})

    metrics = _evaluate(goals)

    # Without winsorization the outlier inflates the mean of `b`.
    assert metrics.loc["b", "count"] == 100
    assert metrics.loc["b", "mean"] == pytest.approx((10 * 99 + 100_000) / 100)


def test_disabled_matches_zero_percentiles():
    goals = _by_unit_goals({"a": list(range(1, 101)), "b": list(range(50, 150))})

    disabled = _evaluate(goals)
    zero = _evaluate(goals, outlier_upper_percentile=0, outlier_lower_percentile=0)

    pd.testing.assert_frame_equal(disabled, zero)


@pytest.mark.parametrize("percentile", [-1, 50, 60, 100])
@pytest.mark.parametrize(
    "param", ["outlier_upper_percentile", "outlier_lower_percentile"]
)
def test_outlier_percentile_out_of_range_raises(param, percentile):
    with pytest.raises(ValueError):
        Metric(
            1,
            "Average Bookings",
            "value(test_unit_type.unit.conversion)",
            "count(test_unit_type.unit.exposure)",
            **{param: percentile},
        )


def test_simple_metric_passes_outlier_percentiles():
    metric = SimpleMetric(
        1,
        "Average Bookings",
        "conversion",
        "exposure",
        unit_type="test_unit_type",
        outlier_upper_percentile=5,
        outlier_lower_percentile=2,
    )
    assert metric.outlier_upper_percentile == 5
    assert metric.outlier_lower_percentile == 2
    assert metric._get_outlier_quantiles() == (0.02, 0.95)
