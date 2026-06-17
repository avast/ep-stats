import numpy as np
import pandas as pd
import pytest

from src.epstats.toolkit.check import SimpleSrmCheck, SrmCheck
from src.epstats.toolkit.experiment import Experiment, Filter, FilterScope
from src.epstats.toolkit.metric import Metric, SimpleMetric
from src.epstats.toolkit.testing import (
    TestDao,
    TestData,
    evaluate_experiment_agg,
    evaluate_experiment_by_unit,
    evaluate_experiment_simple_agg,
)


@pytest.fixture(scope="module")
def dao():
    return TestDao(TestData())


@pytest.fixture(scope="module")
def metrics():
    return [
        Metric(
            1,
            "Click-through Rate",
            "count(test_unit_type.unit.click)",
            "count(test_unit_type.global.exposure)",
        )
    ]


@pytest.fixture(scope="module")
def checks():
    return [SrmCheck(1, "SRM", "count(test_unit_type.global.exposure)")]


@pytest.fixture(scope="module")
def unit_type():
    return "test_unit_type"


def test_update_dimension_to_value(unit_type):
    metrics = [
        Metric(
            1,
            "Average Bookings",
            "value(test_unit_type.unit.conversion(country=A))",
            "count(test_unit_type.global.exposure)",
        ),
        Metric(
            2,
            "Average Bookings",
            "value(test_unit_type.unit.conversion(product=p_1)) + value(test_unit_type.view)",
            "count(test_unit_type.global.exposure)",
        ),
        Metric(
            3,
            "Average Bookings",
            "value(test_unit_type.unit.conversion(country=A))",
            "count(test_unit_type.global.exposure)",
        ),
    ]

    experiment = Experiment(
        "test-real-valued",
        "a",
        metrics=metrics,
        checks=[],
        unit_type=unit_type,
    )

    for goal in experiment.get_goals():
        assert {"country", "product"} == set(goal.dimension_to_value.keys())


def test_binary_valued(dao, metrics, checks, unit_type):
    experiment = Experiment(
        "test-conversion", "a", metrics, checks, unit_type=unit_type
    )
    evaluate_experiment_agg(experiment, dao)


def test_real_valued(dao, checks, unit_type):
    experiment = Experiment(
        "test-real-valued",
        "a",
        [
            Metric(
                2,
                "Average Bookings",
                "value(test_unit_type.unit.conversion)",
                "count(test_unit_type.global.exposure)",
            )
        ],
        checks,
        unit_type=unit_type,
    )
    evaluate_experiment_agg(experiment, dao)


def test_simple_metric(dao, checks, unit_type):
    """
    This test tests SimpleMetric and SimpleSrmCheck.
    Input data are pre-aggregated in wide dataframe format.
    """
    experiment = Experiment(
        "test-simple-metric",
        "a",
        [
            SimpleMetric(1, "Click-through Rate", "clicks", "views"),
            SimpleMetric(2, "Conversion Rate", "conversions", "views"),
            SimpleMetric(3, "RPM", "bookings", "views"),
        ],
        [SimpleSrmCheck(1, "SRM", "views")],
        unit_type=unit_type,
    )
    evaluate_experiment_simple_agg(experiment, dao)


def test_unique(dao, unit_type):
    experiment = Experiment(
        "test-unique",
        "a",
        [
            Metric(
                1,
                "Unique Click-through Rate",
                "unique(test_unit_type.unit.click)",
                "count(test_unit_type.global.exposure)",
            )
        ],
        [],  # No check
        unit_type=unit_type,
    )
    evaluate_experiment_agg(experiment, dao)


def test_real_by_unit(dao, unit_type):
    experiment = Experiment(
        "test-real-valued",
        "a",
        [
            Metric(
                2,
                "Average Bookings",
                "value(test_unit_type.unit.conversion)",
                "count(test_unit_type.unit.exposure)",
            )
        ],
        [SrmCheck(1, "SRM", "count(test_unit_type.unit.exposure)")],
        unit_type=unit_type,
    )
    evaluate_experiment_by_unit(experiment, dao)


def test_by_unit_sums_unit_rows_before_squaring(unit_type):
    """
    A unit can be split into multiple rows of the same goal and dimension value, e.g.
    when unit goals are pre-aggregated at a finer granularity than the experiment
    dimensions. `evaluate_by_unit` must sum the values of the same unit before
    squaring them, otherwise variance estimates can go negative resulting in NaN
    standard deviations, p-values and confidence intervals.
    """
    goals = pd.DataFrame(
        {
            "exp_id": "test-by-unit-sums",
            "exp_variant_id": ["a", "a", "a", "a", "a", "b", "b", "b", "b", "b"],
            "unit_type": unit_type,
            "agg_type": "unit",
            "unit_id": ["u1", "u1", "u1", "u2", "u2", "u3", "u3", "u3", "u4", "u4"],
            "goal": [
                "exposure",
                "conversion",
                "conversion",
                "exposure",
                "conversion",
                "exposure",
                "conversion",
                "conversion",
                "exposure",
                "conversion",
            ],
            "product": ["", "p_1", "p_1", "", "p_1", "", "p_1", "p_1", "", "p_1"],
            "count": 1,
            "sum_value": [1, 2, 3, 1, 1, 1, 2, 2, 1, 2],
        }
    )
    experiment = Experiment(
        "test-by-unit-sums",
        "a",
        [
            Metric(
                1,
                "Conversions per Exposure of Product p_1",
                "value(test_unit_type.unit.conversion(product=p_1))",
                "count(test_unit_type.unit.exposure)",
            ),
        ],
        [],
        unit_type=unit_type,
    )
    metrics = experiment.evaluate_by_unit(goals).metrics.set_index(
        ["metric_id", "exp_variant_id"]
    )

    # per-unit conversion totals are a: (5, 1), b: (4, 2); squaring the individual
    # rows instead of the per-unit totals would give a negative variance in variant a
    assert metrics.loc[(1, "a"), "mean"] == pytest.approx(3.0)
    assert metrics.loc[(1, "a"), "std"] == pytest.approx(np.sqrt(8.0))
    assert metrics.loc[(1, "b"), "mean"] == pytest.approx(3.0)
    assert metrics.loc[(1, "b"), "std"] == pytest.approx(np.sqrt(2.0))
    assert np.isfinite(metrics["p_value"].astype(float)).all()


def test_agg_warns_on_negative_variance(unit_type):
    """
    Pre-aggregated goals can carry `sum_sqr_value` that is not a sum of squared
    per-unit totals, e.g. when a dimensional goal is summed over multiple dimension
    values per unit but squared per dimension value. The variance estimate is then
    negative and the evaluation must warn about it instead of failing silently
    with NaN results.
    """
    goals = pd.DataFrame(
        {
            "exp_id": "test-agg-negative-variance",
            "exp_variant_id": ["a", "a", "a", "b", "b", "b"],
            "unit_type": unit_type,
            "agg_type": "unit",
            "goal": ["exposure", "conversion", "conversion"] * 2,
            "product": ["", "p_1", "p_2"] * 2,
            # `sum_sqr_value` of conversion is squared per (unit, product) row, the
            # sum of squared per-unit totals would be much higher
            "count": [1000, 1000, 1000] * 2,
            "sum_sqr_count": [1000, 1000, 1000] * 2,
            "sum_value": [1000, 1000, 1000] * 2,
            "sum_sqr_value": [1000, 1.5, 1.5] * 2,
            "count_unique": [1000, 1000, 1000] * 2,
        }
    )
    experiment = Experiment(
        "test-agg-negative-variance",
        "a",
        [
            Metric(
                1,
                "Conversions per Exposure",
                "value(test_unit_type.unit.conversion)",
                "count(test_unit_type.unit.exposure)",
            ),
        ],
        [],
        unit_type=unit_type,
    )
    with pytest.warns(UserWarning, match="Negative variance estimate"):
        metrics = experiment.evaluate_agg(goals).metrics.set_index(
            ["metric_id", "exp_variant_id"]
        )
    assert np.isnan(float(metrics.loc[(1, "a"), "std"]))


def test_different_control_variant(dao, checks, unit_type):
    """
    This test tests situation when control variant is not the first one as usual.
    Assume experiment with two variants `a` and `b`. Variant `b` is control variant
    and variant `a` is treatment variant.
    """
    experiment = Experiment(
        "test-control-variant-b",
        "b",
        [
            Metric(
                1,
                "Click-through Rate",
                "count(test_unit_type.unit.click)",
                "count(test_unit_type.global.exposure)",
            ),
        ],
        [],  # no check
        unit_type=unit_type,
    )
    evaluate_experiment_agg(experiment, dao)


def test_single_metrics_in_multiple_experiment(dao, checks, unit_type):
    experiment = Experiment(
        "test-multiple",
        "a",
        [
            Metric(
                1,
                "Click-through Rate",
                "count(test_unit_type.unit.click)",
                "count(test_unit_type.global.exposure)",
            ),
            Metric(
                2,
                "Average Bookings",
                "value(test_unit_type.unit.conversion)",
                "count(test_unit_type.global.exposure)",
            ),
            Metric(
                3,
                "Conversion Rate",
                "count(test_unit_type.unit.conversion)",
                "count(test_unit_type.global.exposure)",
            ),
        ],
        checks,
        unit_type=unit_type,
    )
    evaluate_experiment_agg(experiment, dao)


def test_single_metric_in_multiple_experiment_1(dao, checks, unit_type):
    experiment = Experiment(
        "test-multiple",
        "a",
        [
            Metric(
                2,
                "Average Bookings",
                "value(test_unit_type.unit.conversion)",
                "count(test_unit_type.global.exposure)",
            )
        ],
        checks,
        unit_type=unit_type,
    )
    evaluate_experiment_agg(experiment, dao)


def test_single_metric_in_multiple_experiment_2(dao, metrics, checks, unit_type):
    experiment = Experiment("test-multiple", "a", metrics, checks, unit_type=unit_type)
    evaluate_experiment_agg(experiment, dao)


def test_sequential_first_day(dao, unit_type):
    """Param date_for equals to param date_from"""
    experiment = Experiment(
        "test-sequential-v1",
        "a",
        [
            Metric(
                1,
                "Average Bookings",
                "value(test_unit_type.unit.conversion)",
                "count(test_unit_type.global.exposure)",
            )
        ],
        [],
        unit_type=unit_type,
        date_from="2020-01-01",
        date_to="2020-01-14",
        date_for="2020-01-01",
    )
    evaluate_experiment_agg(experiment, dao)


def test_sequential_middle(dao, unit_type):
    """Param date_for is set between params date_from and date_to"""
    experiment = Experiment(
        "test-sequential-v2",
        "a",
        [
            Metric(
                1,
                "Average Bookings",
                "value(test_unit_type.unit.conversion)",
                "count(test_unit_type.global.exposure)",
            )
        ],
        [],
        unit_type=unit_type,
        date_from="2020-01-01",
        date_to="2020-01-14",
        date_for="2020-01-10",
    )
    evaluate_experiment_agg(experiment, dao)


def test_sequential_last_day(dao, unit_type):
    """Param date_for equals to param date_to"""
    experiment = Experiment(
        "test-sequential-v3",
        "a",
        [
            Metric(
                1,
                "Average Bookings",
                "value(test_unit_type.unit.conversion)",
                "count(test_unit_type.global.exposure)",
            )
        ],
        [],
        unit_type=unit_type,
        date_from="2020-01-01",
        date_to="2020-01-14",
        date_for="2020-01-14",
    )
    evaluate_experiment_agg(experiment, dao)


def test_sequential_today(dao, unit_type):
    """Param date_for is not set - it is set in __init__ method to today"""
    experiment = Experiment(
        "test-sequential-v3",
        "a",
        [
            Metric(
                1,
                "Average Bookings",
                "value(test_unit_type.unit.conversion)",
                "count(test_unit_type.global.exposure)",
            )
        ],
        [],
        unit_type=unit_type,
        date_from="2020-01-01",
        date_to="2020-01-14",
    )
    evaluate_experiment_agg(experiment, dao)


def test_missing_variant(dao, metrics, checks, unit_type):
    experiment = Experiment(
        "test-missing-variant",
        "a",
        metrics,
        checks,
        unit_type=unit_type,
        variants=["a", "b"],
    )
    evaluate_experiment_agg(experiment, dao)


def test_missing_data_unique_goal(dao, metrics, checks, unit_type):
    experiment = Experiment(
        "test-missing-data-unique-goal",
        "a",
        [
            Metric(
                1,
                "Unique Click-through Rate",
                "unique(test_unit_type.unit.click)",
                "count(test_unit_type.global.exposure)",
            )
        ],
        [SrmCheck(1, "SRM", "count(test_unit_type.global.exposure)")],
        unit_type=unit_type,
        variants=["a", "b"],
    )
    evaluate_experiment_agg(experiment, dao)


def test_dimension(dao, metrics, checks, unit_type):
    experiment = Experiment(
        "test-dimension",
        "a",
        [
            Metric(
                1,
                "Views per User of Screen button-1",
                "count(test_unit_type.unit.view(element=button-1))",
                "count(test_unit_type.global.exposure)",
            ),
            Metric(
                2,
                "Views per User of Screen button-%",
                "count(test_unit_type.unit.view(element=button-%))",
                "count(test_unit_type.global.exposure)",
            ),
        ],
        [SrmCheck(1, "SRM", "count(test_unit_type.global.exposure)")],
        unit_type=unit_type,
        variants=["a", "b"],
    )
    evaluate_experiment_agg(experiment, dao)


def test_multi_dimension(dao, metrics, checks, unit_type):
    experiment = Experiment(
        "test-multi-dimension",
        "a",
        [
            Metric(
                1,
                "Views per User of Screen button-1,p-1",
                "count(test_unit_type.unit.view(element=button-1, product=p-1))",
                "count(test_unit_type.global.exposure)",
            ),
            Metric(
                2,
                "Views per User of Screen",
                "count(test_unit_type.unit.view)",
                "count(test_unit_type.global.exposure)",
            ),
        ],
        [SrmCheck(1, "SRM", "count(test_unit_type.global.exposure)")],
        unit_type=unit_type,
        variants=["a", "b"],
    )
    evaluate_experiment_agg(experiment, dao)


def test_filter_scope_goal(dao, metrics, checks, unit_type):
    experiment = Experiment(
        "test-dimension",
        "a",
        [
            Metric(
                1,
                "Views per User of Screen S",
                "count(test_unit_type.unit.view)",
                "count(test_unit_type.global.exposure)",
            ),
        ],
        [SrmCheck(1, "SRM", "count(test_unit_type.global.exposure)")],
        unit_type=unit_type,
        variants=["a", "b"],
        filters=[Filter(FilterScope.goal, "element", ["button-1"])],
    )
    evaluate_experiment_agg(experiment, dao)


def test_trigger_evaluate(dao, unit_type):
    experiment = Experiment(
        "test-trigger",
        "a",
        [
            Metric(
                2,
                "Average Bookings",
                "value(test_unit_type.unit.conversion)",
                "count(test_unit_type.unit.exposure)",
            )
        ],
        [SrmCheck(1, "SRM", "count(test_unit_type.unit.exposure)")],
        unit_type=unit_type,
        filters=[
            Filter(FilterScope.trigger, "product", ["1"], "click"),
            Filter(FilterScope.exposure, "country", ["FR"]),
        ],
    )
    evaluate_experiment_by_unit(experiment, dao)


def test_degrees_of_freedom(dao, metrics, checks, unit_type):
    """Testing functions np.round() and np.trunc() used when converting degrees of freedom from float to int."""
    experiment = Experiment(
        "test-degrees-of-freedom",
        "a",
        [
            Metric(
                1,
                "Click-through Rate",
                "count(test_unit_type.unit.click)",
                "count(test_unit_type.global.exposure)",
            ),
        ],
        [SrmCheck(1, "SRM", "count(test_unit_type.global.exposure)")],
        unit_type=unit_type,
        variants=["a", "b"],
    )
    evaluate_experiment_agg(experiment, dao)


@pytest.mark.filterwarnings("ignore:invalid value")
def test_missing_default(dao, metrics, checks, unit_type):
    experiment = Experiment(
        "test-missing-default",
        "a",
        metrics,
        checks,
        unit_type=unit_type,
    )
    evaluate_experiment_agg(experiment, dao)


@pytest.mark.filterwarnings("ignore:invalid value")
@pytest.mark.filterwarnings("ignore:divide by zero")
def test_missing_default_exposure(dao, metrics, checks, unit_type):
    experiment = Experiment(
        "test-missing-default-exposure",
        "a",
        metrics,
        checks,
        unit_type=unit_type,
    )
    evaluate_experiment_agg(experiment, dao)


@pytest.mark.filterwarnings("ignore:invalid value")
def test_missing_default_value(dao, metrics, checks, unit_type):
    experiment = Experiment(
        "test-missing-default-value",
        "a",
        metrics,
        checks,
        unit_type=unit_type,
    )
    evaluate_experiment_agg(experiment, dao)


@pytest.mark.filterwarnings("ignore:invalid value")
@pytest.mark.filterwarnings("ignore:divide by zero")
def test_missing_exposure(dao, metrics, checks, unit_type):
    experiment = Experiment(
        "test-missing-exposure",
        "a",
        metrics,
        checks,
        unit_type=unit_type,
    )
    evaluate_experiment_agg(experiment, dao)


def test_missing_value(dao, metrics, checks, unit_type):
    experiment = Experiment(
        "test-missing-value",
        "a",
        metrics,
        checks,
        unit_type=unit_type,
    )
    evaluate_experiment_agg(experiment, dao)


@pytest.mark.filterwarnings("ignore:invalid value")
def test_bad_experiment_unit(dao, metrics, checks, unit_type):
    experiment = Experiment(
        "bad-experiment-unit",
        "a",
        metrics,
        checks,
        unit_type=unit_type,
    )
    evaluate_experiment_agg(experiment, dao)


@pytest.mark.filterwarnings("ignore:invalid value")
def test_missing_all_value(dao, metrics, checks, unit_type):
    experiment = Experiment(
        "test-missing-all-value",
        "a",
        metrics,
        checks,
        unit_type=unit_type,
    )
    evaluate_experiment_agg(experiment, dao)


@pytest.mark.filterwarnings("ignore:invalid value")
def test_missing_all(dao, metrics, checks, unit_type):
    experiment = Experiment(
        "test-missing-all",
        "a",
        metrics,
        checks,
        unit_type=unit_type,
    )
    evaluate_experiment_agg(experiment, dao)


def test_metric_with_minimum_effect(dao, unit_type):
    experiment = Experiment(
        "test-conversion-with-minimum-effect",
        "a",
        [
            Metric(
                id=1,
                name="Click-through Rate",
                nominator="count(test_unit_type.unit.click)",
                denominator="count(test_unit_type.global.exposure)",
                minimum_effect=0.1,
            )
        ],
        checks=[],
        unit_type=unit_type,
    )
    evaluate_experiment_agg(experiment, dao)


def test_false_positive_risk(dao, unit_type):
    experiment = Experiment(
        "test-false-positive-risk",
        "a",
        [
            Metric(
                1,
                "Views per User of Screen button-1",
                "count(test_unit_type.unit.view(element=button-1))",
                "count(test_unit_type.global.exposure)",
                minimum_effect=0.05,
            ),
            Metric(
                2,
                "Views per User of Screen button-%",
                "count(test_unit_type.unit.view(element=button-%))",
                "count(test_unit_type.global.exposure)",
                minimum_effect=0.05,
            ),
        ],
        [],
        null_hypothesis_rate=0.1,
        unit_type=unit_type,
        variants=["a", "b"],
    )
    evaluate_experiment_agg(experiment, dao)


def test_duplicate_metric_ids_raise_exception():
    with pytest.raises(ValueError):
        Experiment(
            "test",
            "a",
            [
                Metric(
                    id=1,
                    name="Click-through Rate",
                    nominator="count(test_unit_type.unit.click)",
                    denominator="count(test_unit_type.global.exposure)",
                    minimum_effect=0.1,
                ),
                Metric(
                    id=1,
                    name="Click-through Rate",
                    nominator="count(test_unit_type.unit.click)",
                    denominator="count(test_unit_type.global.exposure)",
                    minimum_effect=0.1,
                ),
            ],
            checks=[],
            unit_type="test",
        )


def test_dimension_operators(dao, metrics, checks, unit_type):
    experiment = Experiment(
        "test-dim-operators",
        "a",
        [
            Metric(
                1,
                "Views per User of Screen ^button-1, product>1",
                "count(test_unit_type.unit.view(element=^button-1, product>1))",
                "count(test_unit_type.global.exposure)",
            ),
            Metric(
                2,
                "Views per User of Screen ^button-1, product!=1",
                "count(test_unit_type.unit.view(element=^button-1, product!=1))",
                "count(test_unit_type.global.exposure)",
            ),
        ],
        [SrmCheck(1, "SRM", "count(test_unit_type.global.exposure)")],
        unit_type=unit_type,
        variants=["a", "b"],
    )
    evaluate_experiment_agg(experiment, dao)


def test_operator_precedence(dao, unit_type):
    experiment = Experiment(
        "test-operator-precedence",
        "a",
        [
            Metric(
                id=1,
                name="Clicks",
                nominator="""
                    count(test_unit_type.unit.click_1)
                    - count(test_unit_type.unit.click_2)
                    + count(test_unit_type.unit.click_3)
                """,
                denominator="count(test_unit_type.global.exposure)",
            )
        ],
        checks=[],
        unit_type=unit_type,
    )
    evaluate_experiment_agg(experiment, dao)
