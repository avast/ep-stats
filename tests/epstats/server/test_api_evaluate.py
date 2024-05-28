import pandas as pd
from epstats.server.req import Experiment
from fastapi.testclient import TestClient

from src.epstats.main import api, get_dao, get_executor_pool
from src.epstats.server.res import Result
from src.epstats.toolkit.testing import (
    TestDao,
    assert_checks,
    assert_exposures,
    assert_metrics,
)

from .depend import dao_factory, get_test_dao, get_test_executor_pool

client = TestClient(api)
api.dependency_overrides[get_dao] = get_test_dao
api.dependency_overrides[get_executor_pool] = get_test_executor_pool


def test_conversion_evaluate():
    json_blob = {
        "id": "test-conversion",
        "control_variant": "a",
        "unit_type": "test_unit_type",
        "metrics": [
            {
                "id": 1,
                "name": "Click-through Rate",
                "nominator": "count(test_unit_type.unit.click)",
                "denominator": "count(test_unit_type.global.exposure)",
            }
        ],
        "checks": [
            {
                "id": 1,
                "name": "SRM",
                "denominator": "count(test_unit_type.global.exposure)",
            }
        ],
    }

    Experiment.model_validate(json_blob)
    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 200
    assert_experiment(resp.json(), dao_factory.get_dao(), 1)


def test_real_valued_evaluate():
    json_blob = {
        "id": "test-real-valued",
        "control_variant": "a",
        "unit_type": "test_unit_type",
        "metrics": [
            {
                "id": 2,
                "name": "Average Bookings",
                "nominator": "value(test_unit_type.unit.conversion)",
                "denominator": "count(test_unit_type.global.exposure)",
            }
        ],
        "checks": [
            {
                "id": 1,
                "name": "SRM",
                "denominator": "count(test_unit_type.global.exposure)",
            }
        ],
    }

    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 200
    assert_experiment(resp.json(), dao_factory.get_dao(), 1)


def test_multiple_evaluate():
    json_blob = {
        "id": "test-multiple",
        "control_variant": "a",
        "unit_type": "test_unit_type",
        "metrics": [
            {
                "id": 1,
                "name": "Click-through Rate",
                "nominator": "count(test_unit_type.unit.click)",
                "denominator": "count(test_unit_type.global.exposure)",
            },
            {
                "id": 2,
                "name": "Average Bookings",
                "nominator": "value(test_unit_type.unit.conversion)",
                "denominator": "count(test_unit_type.global.exposure)",
            },
        ],
        "checks": [
            {
                "id": 1,
                "name": "SRM",
                "denominator": "count(test_unit_type.global.exposure)",
            }
        ],
    }

    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 200
    assert_experiment(resp.json(), dao_factory.get_dao(), 2)


def test_sequential():
    json_blob = {
        "id": "test-sequential-v2",
        "control_variant": "a",
        "date_from": "2020-01-01",
        "date_to": "2020-01-14",
        "date_for": "2020-01-10",
        "unit_type": "test_unit_type",
        "metrics": [
            {
                "id": 1,
                "name": "Average Bookings",
                "nominator": "value(test_unit_type.unit.conversion)",
                "denominator": "count(test_unit_type.global.exposure)",
            },
        ],
        "checks": [],
    }
    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 200
    assert_experiment(resp.json(), dao_factory.get_dao(), expected_metrics=1, expected_checks=0)

    json_blob = {
        "id": "test-sequential-v3",
        "control_variant": "a",
        "date_from": "2020-01-01",
        "date_to": "2020-01-14",
        "date_for": "2020-01-14",
        "unit_type": "test_unit_type",
        "metrics": [
            {
                "id": 1,
                "name": "Average Bookings",
                "nominator": "value(test_unit_type.unit.conversion)",
                "denominator": "count(test_unit_type.global.exposure)",
            },
        ],
        "checks": [],
    }
    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 200
    assert_experiment(resp.json(), dao_factory.get_dao(), expected_metrics=1, expected_checks=0)


def test_dimension_evaluate():
    json_blob = {
        "id": "test-dimension",
        "control_variant": "a",
        "variants": ["a", "b"],
        "unit_type": "test_unit_type",
        "metrics": [
            {
                "id": 1,
                "name": "Views per User of Screen button-1",
                "nominator": "count(test_unit_type.unit.view(element=button-1))",
                "denominator": "count(test_unit_type.global.exposure)",
            },
            {
                "id": 2,
                "name": "Views per User of Screen button-%",
                "nominator": "count(test_unit_type.unit.view(element=button-%))",
                "denominator": "count(test_unit_type.global.exposure)",
            },
        ],
        "checks": [
            {
                "id": 1,
                "name": "SRM",
                "denominator": "count(test_unit_type.global.exposure)",
            }
        ],
    }

    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 200
    assert_experiment(resp.json(), dao_factory.get_dao(), 2)


def test_filter_scope_goal():
    json_blob = {
        "id": "test-dimension",
        "control_variant": "a",
        "variants": ["a", "b"],
        "unit_type": "test_unit_type",
        "filters": [
            {
                "dimension": "element",
                "value": ["button-1"],
                "scope": "goal",
            },
        ],
        "metrics": [
            {
                "id": 1,
                "name": "Views per User of Screen S",
                "nominator": "count(test_unit_type.unit.view)",
                "denominator": "count(test_unit_type.global.exposure)",
            }
        ],
        "checks": [
            {
                "id": 1,
                "name": "SRM",
                "denominator": "count(test_unit_type.global.exposure)",
            }
        ],
    }

    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 200
    assert_experiment(resp.json(), dao_factory.get_dao(), 1)


def test_sum_ratio_check():
    json_blob = {
        "id": "test-sum-ratio",
        "control_variant": "a",
        "variants": ["a", "b", "c"],
        "unit_type": "test_unit_type",
        "filters": [],
        "metrics": [],
        "checks": [
            {
                "id": 1,
                "name": "EVA",
                "type": "SumRatio",
                "nominator": "count(test_unit_type.global.inconsistent_exposure)",
                "denominator": "count(test_unit_type.global.exposure)",
            }
        ],
    }

    resp = client.post("/evaluate", json=json_blob)
    assert_experiment(resp.json(), dao_factory.get_dao(), 0)


def test_multi_check():
    json_blob = {
        "id": "test-multi-check",
        "control_variant": "a",
        "variants": ["a", "b", "c"],
        "unit_type": "test_unit_type",
        "filters": [],
        "metrics": [],
        "checks": [
            {
                "id": 1,
                "name": "EVA",
                "type": "SumRatio",
                "nominator": "count(test_unit_type.global.inconsistent_exposure)",
                "denominator": "count(test_unit_type.global.exposure)",
            },
            {
                "id": 2,
                "name": "SRM",
                "denominator": "count(test_unit_type.global.exposure)",
            },
        ],
    }

    resp = client.post("/evaluate", json=json_blob)
    assert_experiment(resp.json(), dao_factory.get_dao(), 0, 2)


def test_metric_with_minimum_effect():
    json_blob = {
        "id": "test-conversion-with-minimum-effect",
        "control_variant": "a",
        "unit_type": "test_unit_type",
        "metrics": [
            {
                "id": 1,
                "name": "Click-through Rate",
                "nominator": "count(test_unit_type.unit.click)",
                "denominator": "count(test_unit_type.global.exposure)",
                "minimum_effect": 0.1,
            }
        ],
        "checks": [],
    }

    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 200
    assert_experiment(resp.json(), dao_factory.get_dao(), 1, 0)


def test_prometheus_metrics():
    prometheus_resp = client.get("/metrics")
    assert prometheus_resp.status_code == 200
    assert "evaluation_duration_seconds" in prometheus_resp.text


def assert_experiment(target, test_dao: TestDao, expected_metrics: int, expected_checks: int = 1) -> None:
    result = Result(**target)
    assert len(result.metrics) == expected_metrics
    assert len(result.checks) == expected_checks

    for m in target["metrics"]:
        assert len(m["stats"]) >= 2
        d = {
            "exp_variant_id": [],
            "diff": [],
            "mean": [],
            "std": [],
            "sum_value": [],
            "p_value": [],
            "confidence_interval": [],
            "confidence_level": [],
            "sample_size": [],
            "required_sample_size": [],
            "power": [],
        }
        for s in m["stats"]:
            for i in s.items():
                d[i[0]].append(i[1])

        metric_df = pd.DataFrame(d)
        metric_df["exp_id"] = target["id"]
        metric_df["metric_id"] = m["id"]
        assert_metrics(target["id"], m["id"], metric_df, test_dao)

    for m in target["checks"]:
        d = {"variable_id": [], "value": []}
        for s in m["stats"]:
            for i in s.items():
                d[i[0]].append(i[1])
        metric_df = pd.DataFrame(d)
        metric_df["exp_id"] = target["id"]
        metric_df["check_id"] = m["id"]
        assert_checks(target["id"], m["id"], metric_df, test_dao)

    m = target["exposure"]
    d = {"exp_variant_id": [], "exposures": []}
    for s in m["stats"]:
        d["exp_variant_id"].append(s["exp_variant_id"])
        d["exposures"].append(s["count"])
    metric_df = pd.DataFrame(d)
    metric_df["exp_id"] = target["id"]
    assert_exposures(target["id"], metric_df, test_dao, unit_type="test_unit_type", agg_type="global")
