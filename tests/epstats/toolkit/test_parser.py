import numpy as np
import pandas as pd
import pytest
from numpy.testing import assert_almost_equal
from pyparsing import ParseException

from src.epstats.toolkit.parser import MultBinOp, Parser


def test_evaluate_agg():
    variants = ["a", "b", "c", "d"]
    goals = ["click", "exposure", "conversion", "refund"]
    ln = len(variants) * len(goals)

    goals = pd.DataFrame(
        {
            "exp_id": "test",
            "exp_variant_id": np.repeat(variants, len(goals)),
            "unit_type": "test_unit_type",
            "agg_type": "unit",
            "goal": goals * len(variants),
            "count": 1000 + np.random.randint(-100, 100, ln),
            "sum_sqr_count": 1000 + np.random.randint(-100, 100, ln),
            "sum_value": 10 + np.random.normal(0, 3, ln),
            "sum_sqr_value": 100 + np.random.normal(0, 10, ln),
        }
    )

    parser = Parser(
        "count(test_unit_type.unit.click)",
        "count(test_unit_type.unit.exposure)",
    )
    assert_count_value(
        parser.evaluate_agg(goals),
        goals[goals.goal == "exposure"]["count"].values,
        goals[goals.goal == "click"]["count"].values,
        goals[goals.goal == "click"]["sum_sqr_count"].values,
    )

    parser = Parser(
        "value(test_unit_type.unit.conversion) - value(test_unit_type.unit.refund)",
        "count(test_unit_type.unit.exposure)",
    )

    conversion_sqr_value = goals[goals.goal == "conversion"]["sum_sqr_value"].to_numpy()
    refund_sqr_value = goals[goals.goal == "refund"]["sum_sqr_value"].to_numpy()
    conversion_value = goals[goals.goal == "conversion"]["sum_value"].to_numpy()
    refund_value = goals[goals.goal == "refund"]["sum_value"].to_numpy()
    assert_count_value(
        parser.evaluate_agg(goals),
        goals[goals.goal == "exposure"]["count"],
        conversion_value - refund_value,
        conversion_sqr_value - refund_sqr_value,
    )

    parser = Parser(
        "value(test_unit_type.unit.conversion) ~ value(test_unit_type.unit.refund)",
        "count(test_unit_type.unit.exposure)",
    )
    assert_count_value(
        parser.evaluate_agg(goals),
        goals[goals.goal == "exposure"]["count"],
        conversion_value - refund_value,
        conversion_sqr_value + refund_sqr_value,
    )

    parser = Parser(
        "value(test_unit_type.unit.conversion)",
        "count(test_unit_type.unit.exposure) / 1000",
    )
    assert_count_value(
        parser.evaluate_agg(goals),
        goals[goals.goal == "exposure"]["count"].to_numpy() / 1000,
        conversion_value,
        conversion_sqr_value,
    )


def test_evaluate_agg_dimensional():
    goals = pd.DataFrame(
        {
            "exp_id": "testt",
            "exp_variant_id": ["a", "a", "a", "b", "b", "b"],
            "unit_type": "test_unit_type",
            "agg_type": "unit",
            "goal": ["exposure", "click", "click"] * 2,
            "count": 1000 + np.random.randint(-100, 100, 6),
            "sum_sqr_count": 1000 + np.random.randint(-100, 100, 6),
            "sum_value": 10 + np.random.normal(0, 3, 6),
            "sum_sqr_value": 100 + np.random.normal(0, 10, 6),
            "product": ["", "", "p_1"] * 2,
            "country": ["", "", "US"] * 2,
        }
    )

    parser = Parser(
        "count(test_unit_type.unit.click(country=US, product=p_1))",
        "count(test_unit_type.unit.exposure)",
    )

    click_mask = (goals["goal"] == "click") & (goals["country"] == "US") & (goals["product"] == "p_1")

    assert_count_value(
        parser.evaluate_agg(goals),
        goals[goals["goal"] == "exposure"]["count"].values,
        goals[click_mask]["count"].values,
        goals[click_mask]["sum_sqr_count"].values,
    )


def test_fail_if_unknown_function():
    with pytest.raises(ParseException):
        parser = Parser(
            "foo(test_unit_type.unit.click) * count(test_unit_type.unit.bar)",
            "count(test_unit_type.global.exposure)",
        )
        parser.evaluate_agg(pd.DataFrame({"foo": np.ones(10)}))


def test_fail_if_unknown_unit_type():
    with pytest.raises(KeyError):
        parser = Parser(
            "count(unknown_unit_type.unit.click) * count(test_unit_type.unit.bar)",
            "count(test_unit_type.global.exposure)",
        )
        parser.evaluate_agg(pd.DataFrame({"foo": np.ones(10)}))


def test_fail_if_incorrect_syntax():
    with pytest.raises(ParseException):
        parser = Parser(
            " / count(test_unit_type.global.exposure)",
            "count(test_unit_type.unit.bar)",
        )
        parser.evaluate_agg(pd.DataFrame({"foo": np.ones(10)}))


@pytest.mark.parametrize(
    "parser, expected",
    [
        (
            Parser(
                "value(test_unit_type.unit.conversion) - value(test_unit_type.unit.refund)",
                "count(test_unit_type.global.exposure)",
            ),
            {
                "test_unit_type.unit.conversion",
                "test_unit_type.unit.refund",
                "test_unit_type.global.exposure",
            },
        ),
        (
            Parser(
                "value(test_unit_type.global.conversion)",
                "count(test_unit_type.global.exposure)",
            ),
            {
                "test_unit_type.global.conversion",
                "test_unit_type.global.exposure",
            },
        ),
        (
            Parser(
                "value(test_unit_type.unit.conversion) ~ value(test_unit_type.unit.refund)",
                "count(test_unit_type.global.exposure)",
            ),
            {
                "test_unit_type.unit.conversion",
                "test_unit_type.unit.refund",
                "test_unit_type.global.exposure",
            },
        ),
        (
            Parser(
                "value(test_unit_type.unit.conversion(a=b, y=x, test=test))",
                "count(test_unit_type.global.exposure)",
            ),
            {
                "test_unit_type.unit.conversion[a=b, y=x, test=test]",
                "test_unit_type.global.exposure",
            },
        ),
        (
            Parser(
                "value(test_unit_type.unit.conversion(a=b))",
                "count(test_unit_type.global.exposure)",
            ),
            {
                "test_unit_type.unit.conversion[a=b]",
                "test_unit_type.global.exposure",
            },
        ),
        (
            Parser(
                "value(test_unit_type.unit.conversion(product=p_1))",
                "value(test_unit_type.unit.conversion(product=p_1))",
            ),
            {"test_unit_type.unit.conversion[product=p_1]"},
        ),
        (
            Parser(
                "value(test_unit_type.unit.conversion(product=p_1))",
                "value(test_unit_type.unit.conversion)",
            ),
            {"test_unit_type.unit.conversion[product=p_1]", "test_unit_type.unit.conversion"},
        ),
        (
            Parser(
                "value(test_unit_type.unit.conversion(product=p_1)) + "
                "value(test_unit_type.unit.conversion(product=p_1))",
                "value(test_unit_type.unit.conversion)",
            ),
            {"test_unit_type.unit.conversion[product=p_1]", "test_unit_type.unit.conversion"},
        ),
    ],
)
def test_get_goals(parser, expected):
    assert parser.get_goals_str() == expected


def test_fail_if_duplicate_dimensions():
    with pytest.raises(ParseException):
        Parser(
            "value(test_unit_type.unit.conversion(a=b, a=c))",
            "count(test_unit_type.global.exposure)",
        )


@pytest.mark.parametrize(
    "parser, expected_goals",
    [
        (
            Parser(
                "count(test_unit_type.global.conversion(product=p_1)) + count(test_unit_type.global.conversion)",
                "count(test_unit_type.unit.conversion(product=p_1_2))",
            ),
            {
                "test_unit_type.global.conversion[product=p_1]": {"product": "p_1"},
                "test_unit_type.global.conversion": {"product": ""},
                "test_unit_type.unit.conversion[product=p_1_2]": {"product": "p_1_2"},
            },
        ),
        (
            Parser(
                "count(test_unit_type.global.conversion(x=1, y=2))",
                "count(test_unit_type.unit.conversion)",
            ),
            {
                "test_unit_type.global.conversion[x=1, y=2]": {"x": "1", "y": "2"},
                "test_unit_type.unit.conversion": {"x": "", "y": ""},
            },
        ),
        (
            Parser(
                "count(test_unit_type.global.conversion(x=1, y=2))",
                "count(test_unit_type.global.conversion(x=1))",
            ),
            {
                "test_unit_type.global.conversion[x=1, y=2]": {"x": "1", "y": "2"},
                "test_unit_type.global.conversion[x=1]": {"x": "1", "y": ""},
            },
        ),
        (
            Parser(
                "count(test_unit_type.global.conversion(x=A/ A, y=A B /C))",
                "count(test_unit_type.unit.conversion)",
            ),
            {
                "test_unit_type.global.conversion[x=A/ A, y=A B /C]": {"x": "A/ A", "y": "A B /C"},
                "test_unit_type.unit.conversion": {"x": "", "y": ""},
            },
        ),
        (
            Parser(
                "count(test_unit_type.global.conversion(x=A/ A|BB, y=X|Y|Z))",
                "count(test_unit_type.unit.conversion)",
            ),
            {
                "test_unit_type.global.conversion[x=A/ A|BB, y=X|Y|Z]": {"x": "A/ A|BB", "y": "X|Y|Z"},
                "test_unit_type.unit.conversion": {"x": "", "y": ""},
            },
        ),
        (
            Parser(
                "count(test_unit_type.global.conversion(x=^test|test, y=^test))",
                "count(test_unit_type.unit.conversion)",
            ),
            {
                "test_unit_type.global.conversion[x=^test|test, y=^test]": {"x": "^test|test", "y": "^test"},
                "test_unit_type.unit.conversion": {"x": "", "y": ""},
            },
        ),
        (
            Parser(
                "count(test.global.conversion(x=test, y>=123))",
                "count(test.unit.conversion(a<=4, b>42))",
            ),
            {
                "test.global.conversion[x=test, y>=123]": {"x": "test", "y": ">=123", "a": "", "b": ""},
                "test.unit.conversion[a<=4, b>42]": {"a": "<=4", "b": ">42", "x": "", "y": ""},
            },
        ),
        (
            Parser(
                "count(test.global.conversion(x=test, y!=123))",
                "count(test.global.conversion)",
            ),
            {
                "test.global.conversion[x=test, y!=123]": {"x": "test", "y": "!=123"},
                "test.global.conversion": {"x": "", "y": ""},
            },
        ),
        (
            Parser(
                "count(test.global.conversion(x_1=test, x_234=234))",
                "count(test.global.conversion)",
            ),
            {
                "test.global.conversion[x_1=test, x_234=234]": {"x_1": "test", "x_234": "234"},
                "test.global.conversion": {"x_1": "", "x_234": ""},
            },
        ),
    ],
)
def test_get_goals_dimensional(parser, expected_goals):
    goals = parser.get_goals()

    for g in goals:
        assert expected_goals[str(g)] == g.dimension_to_value
        if not g.is_dimensional():
            assert all(v == "" for v in g.dimension_to_value.values())


@pytest.mark.parametrize(
    "dimension_value",
    [
        "232>44",
        "abc^def",
        "<=2",
    ],
)
def test_operator_position_not_correct(dimension_value):
    with pytest.raises(ParseException):
        Parser(
            f"count(test_unit_type.global.conversion(x={dimension_value})",
            "count(test_unit_type.unit.conversion)",
        )


@pytest.mark.parametrize(
    "nominator",
    [
        "2 * count(test_unit_type.global.conversion)",
        "-1 * count(test_unit_type.global.conversion)",
    ],
)
def test_numbers(nominator):
    assert isinstance(
        Parser(nominator, "count(test_unit_type.unit.conversion)")._nominator_expr,
        MultBinOp,
    )


def assert_count_value(evaluation, count, value, value_sqr, precision=5):
    assert_almost_equal(evaluation[0], count, precision)
    assert_almost_equal(evaluation[1], value, precision)
    assert_almost_equal(evaluation[2], value_sqr, precision)
