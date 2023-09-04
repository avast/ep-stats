from prometheus_client import Counter, Summary, REGISTRY
from typing import Union


def get_prometheus_metric(metric_name: str, metric_type: type) -> Union[Counter, Summary]:
    try:
        return metric_type(metric_name, "")
    except ValueError:
        return REGISTRY._names_to_collectors[metric_name]
