from locust import HttpUser, between, task, tag


class WebsiteUser(HttpUser):
    """
    Locust stress-testing configuration.
    """

    wait_time = between(2, 4)

    @tag("health")
    @task
    def attempt(self):
        self.client.get("/health")

    @tag("evaluate")
    @task
    def evaluate(self):
        self.client.post(
            "/evaluate/",
            json={
                "id": "test-conversion",
                "control_variant": "a",
                "variants": ["a", "b", "c"],
                "unit_type": "test_unit_type",
                "metrics": [
                    {
                        "id": 1,
                        "name": "Click-through Rate",
                        "nominator": "count(test_unit_type.unit.click)",
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
            },
        )
