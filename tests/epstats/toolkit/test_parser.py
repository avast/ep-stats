from unittest import TestCase
import numpy as np
from numpy.testing import assert_almost_equal
import pandas as pd
import pytest
from pyparsing import ParseException

from epstats.toolkit.parser import Parser


class TestParser(TestCase):
    def test_parser(self):
        variants = ['a', 'b', 'c', 'd']
        goals = ['click', 'exposure', 'conversion', 'refund']
        ln = len(variants) * len(goals)

        goals = pd.DataFrame(
            {
                'exp_variant_id': np.repeat(variants, len(goals)),
                'unit_type': np.repeat('test_unit_type', ln),
                'agg_type': np.repeat('unit', ln),
                'dimension': np.repeat('', ln),
                'dimension_value': np.repeat('', ln),
                'goal': np.array(goals * len(variants)),
                'count': 1000 + np.random.randint(-100, 100, ln),
                'sum_sqr_count': 1000 + np.random.randint(-100, 100, ln),
                'sum_value': 10 + np.random.normal(0, 3, ln),
                'sum_sqr_value': 100 + np.random.normal(0, 10, ln),
            }
        )

        parser = Parser('count(test_unit_type.unit.click)', 'count(test_unit_type.unit.exposure)',)
        assert_count_value(
            parser.evaluate_agg(goals),
            goals[goals.goal == 'exposure']['count'].values,
            goals[goals.goal == 'click']['count'].values,
            goals[goals.goal == 'click']['sum_sqr_count'].values,
        )

        parser = Parser(
            'value(test_unit_type.unit.conversion) - value(test_unit_type.unit.refund)',
            'count(test_unit_type.unit.exposure)',
        )

        conversion_sqr_value = goals[goals.goal == 'conversion']['sum_sqr_value'].values
        refund_sqr_value = goals[goals.goal == 'refund']['sum_sqr_value'].values
        assert_count_value(
            parser.evaluate_agg(goals),
            goals[goals.goal == 'exposure']['count'],
            goals[goals.goal == 'conversion']['sum_value'].values - goals[goals.goal == 'refund']['sum_value'].values,
            conversion_sqr_value - refund_sqr_value,
        )

        parser = Parser('value(test_unit_type.unit.conversion)', 'count(test_unit_type.unit.exposure) / 1000',)
        assert_count_value(
            parser.evaluate_agg(goals),
            goals[goals.goal == 'exposure']['count'].values / 1000,
            goals[goals.goal == 'conversion']['sum_value'].values,
            goals[goals.goal == 'conversion']['sum_sqr_value'].values,
        )

    def test_equal(self):
        parser = Parser(
            'value(test_unit_type.unit.conversion(product=p_1))', 'value(test_unit_type.unit.conversion(product=p_1))',
        )
        assert len(parser.get_goals()) == 1

        parser = Parser('value(test_unit_type.unit.conversion(product=p_1))', 'value(test_unit_type.unit.conversion)',)
        assert len(parser.get_goals()) == 2

        parser = Parser(
            'value(test_unit_type.unit.conversion(product=p_1)) + value(test_unit_type.unit.conversion(product=p_1))',
            'value(test_unit_type.unit.conversion)',
        )
        assert len(parser.get_goals()) == 2

    def test_unknown_function(self):
        with pytest.raises(ParseException):
            parser = Parser(
                'foo(test_unit_type.unit.click) * count(test_unit_type.unit.bar)',
                'count(test_unit_type.global.exposure)',
            )
            parser.evaluate_agg(pd.DataFrame({'foo': np.ones(10)}))

    def test_fail_if_unknown_unit_type(self):
        with pytest.raises(KeyError):
            parser = Parser(
                'count(unknown_unit_type.unit.click) * count(test_unit_type.unit.bar)',
                'count(test_unit_type.global.exposure)',
            )
            parser.evaluate_agg(pd.DataFrame({'foo': np.ones(10)}))

    def test_parsing(self):
        with pytest.raises(ParseException):
            parser = Parser(' / count(test_unit_type.global.exposure)', 'count(test_unit_type.unit.bar)',)
            parser.evaluate_agg(pd.DataFrame({'foo': np.ones(10)}))

    def test_get_goals(self):
        parser = Parser(
            'value(test_unit_type.unit.conversion) - value(test_unit_type.unit.refund)',
            'count(test_unit_type.global.exposure)',
        )
        assert parser.get_goals_str() == {
            'test_unit_type.unit.conversion',
            'test_unit_type.unit.refund',
            'test_unit_type.global.exposure',
        }

        parser = Parser('value(test_unit_type.global.conversion)', 'count(test_unit_type.global.exposure)',)
        assert parser.get_goals_str() == {
            'test_unit_type.global.conversion',
            'test_unit_type.global.exposure',
        }

    def test_get_goals_dimensional(self):
        parser = Parser(
            'count(test_unit_type.global.conversion(product=p_1)) + count(test_unit_type.global.conversion)',
            'count(test_unit_type.unit.conversion(product=p_1_2))',
        )
        goals = parser.get_goals()
        dim_goals = [g for g in goals if g.is_dimensional()]

        assert len(goals) == 3
        assert len(dim_goals) == 2

        assert set([dg.dimension for dg in dim_goals]) == {'product'}
        assert set([dg.dimension_value for dg in dim_goals]) == {'p_1', 'p_1_2'}


def assert_count_value(evaluation, count, value, value_sqr, precision=5):
    assert_almost_equal(evaluation[0], count, precision)
    assert_almost_equal(evaluation[1], value, precision)
    assert_almost_equal(evaluation[2], value_sqr, precision)
