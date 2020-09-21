import pandas as pd
from fastapi.testclient import TestClient

from epstats.toolkit.testing import (
    assert_metrics,
    assert_checks,
    assert_exposures,
    TestDao,
)

from epstats.main import api
from epstats.main import get_dao, get_statsd, get_executor_pool
from epstats.server.res import Result

from .depend import get_test_dao, get_test_executor_pool, get_test_statsd, dao_factory


client = TestClient(api)
api.dependency_overrides[get_dao] = get_test_dao
api.dependency_overrides[get_statsd] = get_test_statsd
api.dependency_overrides[get_executor_pool] = get_test_executor_pool


def test_conversion_evaluate():
    json_blob = {
        'id': 'test-conversion',
        'control_variant': 'a',
        'unit_type': 'test_unit_type',
        'metrics': [
            {
                'id': 1,
                'name': 'Click-through Rate',
                'nominator': 'count(test_unit_type.unit.click)',
                'denominator': 'count(test_unit_type.global.exposure)',
            }
        ],
        'checks': [{'id': 1, 'name': 'SRM', 'denominator': 'count(test_unit_type.global.exposure)',}],
    }

    resp = client.post('/evaluate', json=json_blob)
    assert resp.status_code == 200
    assert_experiment(resp.json(), dao_factory.get_dao(), 1)


def test_real_valued_evaluate():
    json_blob = {
        'id': 'test-real-valued',
        'control_variant': 'a',
        'unit_type': 'test_unit_type',
        'metrics': [
            {
                'id': 2,
                'name': 'Average Bookings',
                'nominator': 'value(test_unit_type.unit.conversion)',
                'denominator': 'count(test_unit_type.global.exposure)',
            }
        ],
        'checks': [{'id': 1, 'name': 'SRM', 'denominator': 'count(test_unit_type.global.exposure)',}],
    }

    resp = client.post('/evaluate', json=json_blob)
    assert resp.status_code == 200
    assert_experiment(resp.json(), dao_factory.get_dao(), 1)


def test_multiple_evaluate():
    json_blob = {
        'id': 'test-multiple',
        'control_variant': 'a',
        'unit_type': 'test_unit_type',
        'metrics': [
            {
                'id': 1,
                'name': 'Click-through Rate',
                'nominator': 'count(test_unit_type.unit.click)',
                'denominator': 'count(test_unit_type.global.exposure)',
            },
            {
                'id': 2,
                'name': 'Average Bookings',
                'nominator': 'value(test_unit_type.unit.conversion)',
                'denominator': 'count(test_unit_type.global.exposure)',
            },
        ],
        'checks': [{'id': 1, 'name': 'SRM', 'denominator': 'count(test_unit_type.global.exposure)',}],
    }

    resp = client.post('/evaluate', json=json_blob)
    assert resp.status_code == 200
    assert_experiment(resp.json(), dao_factory.get_dao(), 2)


def test_sequential():
    json_blob = {
        'id': 'test-sequential-v2',
        'control_variant': 'a',
        'date_from': '2020-01-01',
        'date_to': '2020-01-14',
        'date_for': '2020-01-10',
        'unit_type': 'test_unit_type',
        'metrics': [
            {
                'id': 1,
                'name': 'Average Bookings',
                'nominator': 'value(test_unit_type.unit.conversion)',
                'denominator': 'count(test_unit_type.global.exposure)',
            },
        ],
        'checks': [],
    }
    resp = client.post('/evaluate', json=json_blob)
    assert resp.status_code == 200
    assert_experiment(resp.json(), dao_factory.get_dao(), expected_metrics=1, expected_checks=0)

    json_blob = {
        'id': 'test-sequential-v3',
        'control_variant': 'a',
        'date_from': '2020-01-01',
        'date_to': '2020-01-14',
        'date_for': '2020-01-14',
        'unit_type': 'test_unit_type',
        'metrics': [
            {
                'id': 1,
                'name': 'Average Bookings',
                'nominator': 'value(test_unit_type.unit.conversion)',
                'denominator': 'count(test_unit_type.global.exposure)',
            },
        ],
        'checks': [],
    }
    resp = client.post('/evaluate', json=json_blob)
    assert resp.status_code == 200
    assert_experiment(resp.json(), dao_factory.get_dao(), expected_metrics=1, expected_checks=0)


def assert_experiment(target, test_dao: TestDao, expected_metrics: int, expected_checks: int = 1) -> None:
    result = Result(**target)
    assert len(result.metrics) == expected_metrics
    assert len(result.checks) == expected_checks
    if expected_checks > 0:
        assert len(result.checks[0].stats) == 3

    for m in target['metrics']:
        assert len(m['stats']) >= 2
        d = {
            'exp_variant_id': [],
            'diff': [],
            'mean': [],
            'sum_value': [],
            'p_value': [],
            'confidence_interval': [],
            'confidence_level': [],
        }
        for s in m['stats']:
            for i in s.items():
                d[i[0]].append(i[1])
        df = pd.DataFrame(d)
        df['exp_id'] = target['id']
        df['metric_id'] = m['id']
        assert_metrics(target['id'], m['id'], df, test_dao)

    for m in target['checks']:
        d = {'variable_id': [], 'value': []}
        for s in m['stats']:
            for i in s.items():
                d[i[0]].append(i[1])
        df = pd.DataFrame(d)
        df['exp_id'] = target['id']
        df['check_id'] = m['id']
        assert_checks(target['id'], m['id'], df, test_dao)

    m = target['exposure']
    d = {'exp_variant_id': [], 'exposures': []}
    for s in m['stats']:
        d['exp_variant_id'].append(s['exp_variant_id'])
        d['exposures'].append(s['count'])
    df = pd.DataFrame(d)
    df['exp_id'] = target['id']
    assert_exposures(target['id'], df, test_dao, unit_type='test_unit_type', agg_type='global')
