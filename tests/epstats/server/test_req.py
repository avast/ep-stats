from fastapi.testclient import TestClient

from src.epstats.main import api, get_dao, get_executor_pool

from .depend import get_test_dao, get_test_executor_pool

client = TestClient(api)
api.dependency_overrides[get_dao] = get_test_dao
api.dependency_overrides[get_executor_pool] = get_test_executor_pool


def test_validate_control_variant():
    json_blob = {
        "id": "test-conversions",
        "controlvariant": "a",
        "metrics": [
            {
                "id": 1,
                "name": "Click-through Rate",
                "nominator": "count(test_unit_type.unit.click)",
                "denominator": "count(test_unit_type.global.exposure)",
            }
        ],
        "checks": [],
    }

    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 422
    json = resp.json()
    assert json["detail"][0]["loc"][1] == "control_variant"
    assert json["detail"][0]["type"] == "missing"


def test_validate_metric_nominator():
    json_blob = {
        "id": "test-binary",
        "control_variant": "a",
        "unit_type": "test_unit_type",
        "metrics": [
            {
                "id": 1,
                "name": "Click-through Rate",
                "nnominator": "count(test_unit_type.unit.click)",
                "denominator": "count(test_unit_type.global.exposure)",
            }
        ],
        "checks": [],
    }

    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 422
    json = resp.json()
    assert json["detail"][0]["loc"][3] == "nominator"
    assert json["detail"][0]["type"] == "missing"


def test_validate_metric_denominator():
    json_blob = {
        "id": "test-conversions",
        "control_variant": "a",
        "unit_type": "test_unit_type",
        "metrics": [
            {
                "id": 1,
                "name": "Click-through Rate",
                "nominator": "count(test_unit_type.unit.click)",
                "ddenominator": "count(test_unit_type.global.exposure)",
            }
        ],
        "checks": [],
    }

    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 422
    json = resp.json()
    assert json["detail"][0]["loc"][3] == "denominator"
    assert json["detail"][0]["type"] == "missing"


def test_validate_default_check_type():
    json_blob = {
        "id": "test-conversions",
        "control_variant": "a",
        "unit_type": "test_unit_type",
        "metrics": [],
        "checks": [
            {
                "id": 1,
                "name": "SRM",
                "denominator": "count(test_unit_type.global.exposure)",
            },
        ],
    }

    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 200


def test_validate_sum_ratio_nominator():
    json_blob = {
        "id": "test-conversions",
        "control_variant": "a",
        "unit_type": "test_unit_type",
        "metrics": [],
        "checks": [
            {
                "id": 1,
                "name": "SumRatio",
                "type": "SumRatio",
                "denominator": "count(test_unit_type.global.exposure)",
            },
        ],
    }

    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 422
    json = resp.json()
    assert json["detail"][0]["loc"][1] == "checks"
    assert json["detail"][0]["loc"][1] == "checks"
    assert json["detail"][0]["type"] == "value_error"


def test_validate_metric_parsing():
    json_blob = {
        "id": "test-conversions",
        "control_variant": "a",
        "unit_type": "test_unit_type",
        "metrics": [
            {
                "id": 1,
                "name": "Click-through Rate",
                "nominator": "count(test_unit_type.unit.click)",
                "denominator": "fce(test_unit_type.global.exposure)",
            }
        ],
        "checks": [],
    }

    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 422
    json = resp.json()
    assert json["detail"][0]["loc"][1] == "metrics"
    assert json["detail"][0]["type"] == "value_error"


def test_date_parsing():
    json_blob = {
        "id": "test-conversions",
        "control_variant": "a",
        "date_from": "2020-01-01",
        "date_to": "2020-01-14",
        "date_for": "2020-01-10",
        "metrics": [],
        "checks": [],
        "unit_type": "test_unit_type",
    }
    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 200

    json_blob = {
        "id": "test-conversions",
        "control_variant": "a",
        "date_from": "2020-01-40",
        "date_to": "2020-01-",
        "metrics": [],
        "checks": [],
        "unit_type": "test_unit_type",
    }

    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 422
    json = resp.json()
    assert json["detail"][0]["loc"][1] == "date_from"
    assert json["detail"][0]["type"] == "value_error"
    assert json["detail"][1]["loc"][1] == "date_to"
    assert json["detail"][1]["type"] == "value_error"


def test_validate_date_to_ge_from():
    json_blob = {
        "id": "test-conversions",
        "control_variant": "a",
        "date_from": "2020-01-02",
        "date_to": "2020-01-01",
        "metrics": [],
        "checks": [],
        "unit_type": "test_unit_type",
    }
    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 422
    json = resp.json()
    assert json["detail"][0]["loc"][0] == "body"
    assert json["detail"][0]["type"] == "value_error"


def test_validate_date_for_requires_date_to_and_date_for():
    json_blob = {
        "id": "test-conversions",
        "control_variant": "a",
        "date_from": "2020-01-01",
        "date_for": "2020-01-10",
        "metrics": [],
        "checks": [],
        "unit_type": "test_unit_type",
    }
    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 422
    json = resp.json()
    assert json["detail"][0]["loc"][0] == "body"
    assert json["detail"][0]["type"] == "value_error"

    json_blob = {
        "id": "test-conversions",
        "control_variant": "a",
        "date_for": "2020-01-01",
        "date_to": "2020-01-10",
        "metrics": [],
        "checks": [],
        "unit_type": "test_unit_type",
    }
    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 422
    json = resp.json()
    assert json["detail"][0]["loc"][0] == "body"
    assert json["detail"][0]["type"] == "value_error"


def test_validate_date_for_between_date_to_and_date_for():
    json_blob = {
        "id": "test-conversions",
        "control_variant": "a",
        "date_from": "2020-01-01",
        "date_to": "2020-01-05",
        "date_for": "2020-01-10",
        "metrics": [],
        "checks": [],
        "unit_type": "test_unit_type",
    }
    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 422
    json = resp.json()
    assert json["detail"][0]["loc"][0] == "body"
    assert json["detail"][0]["type"] == "value_error"

    json_blob = {
        "id": "test-conversions",
        "control_variant": "a",
        "date_from": "2020-01-05",
        "date_to": "2020-01-10",
        "date_for": "2020-01-01",
        "metrics": [],
        "checks": [],
        "unit_type": "test_unit_type",
    }
    resp = client.post("/evaluate", json=json_blob)
    assert resp.status_code == 422
    json = resp.json()
    assert json["detail"][0]["loc"][0] == "body"
    assert json["detail"][0]["type"] == "value_error"
