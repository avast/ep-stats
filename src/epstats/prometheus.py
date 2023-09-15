from prometheus_client import Counter, Summary, REGISTRY
from typing import Union


application_prefix = "ep_stats_"


def get_prometheus_metric(metric_name: str, metric_type: type) -> Union[Counter, Summary]:
    metric_name_with_application_prefix = application_prefix + metric_name
    try:
        return metric_type(metric_name_with_application_prefix, "")
    except ValueError:
        return REGISTRY._names_to_collectors[metric_name_with_application_prefix]
