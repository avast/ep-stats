import pytest
from fastapi.testclient import TestClient

from src.epstats.main import api
from src.epstats.main import get_statsd, get_executor_pool

from .depend import get_test_executor_pool, get_test_statsd


client = TestClient(api)
api.dependency_overrides[get_statsd] = get_test_statsd
api.dependency_overrides[get_executor_pool] = get_test_executor_pool


@pytest.mark.parametrize(
    "n_variants, minimum_effect, mean, std, expected",
    [(2, 0.10, 0.2, 1.2, 56512), (2, 0.05, 0.4, None, 9489), (3, 0.05, 0.4, None, 11492)],
)
def test_sample_size_calculation(n_variants, minimum_effect, mean, std, expected):
    json_blob = {
        "minimum_effect": minimum_effect,
        "mean": mean,
        "std": std,
        "n_variants": n_variants,
    }

    resp = client.post("/sample-size-calculation", json=json_blob)
    assert resp.status_code == 200
    assert resp.json()["sample_size_per_variant"] == expected


@pytest.mark.parametrize(
    "n_variants, minimum_effect, mean, expected_message",
    [
        (2, -0.4, 0.2, "minimum_effect must be greater than zero"),
        (2, 0.05, 1.4, "mean must be between zero and one"),
        (1, 0.05, 0.2, "must be at least two variants"),
    ],
)
def test_sample_size_calculation_error(n_variants, minimum_effect, mean, expected_message):
    json_blob = {
        "minimum_effect": minimum_effect,
        "mean": mean,
        "n_variants": n_variants,
    }

    resp = client.post("/sample-size-calculation", json=json_blob)
    assert resp.status_code == 500
    assert expected_message in resp.content.decode()
