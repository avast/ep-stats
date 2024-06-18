import pandas as pd

from .experiment import Experiment


def _add_confidence_intervals(metrics: pd.DataFrame) -> pd.DataFrame:
    # Compute lower and upper bound for confidence interval
    metrics["conf_int_lower"] = metrics["diff"] - metrics["confidence_interval"]
    metrics["conf_int_upper"] = metrics["diff"] + metrics["confidence_interval"]

    return metrics


def results_long_to_wide(metrics: pd.DataFrame) -> pd.DataFrame:
    """Adjusts metric results from long format to wide."""
    metrics = _add_confidence_intervals(metrics)

    # Change experiment variants to upper case
    metrics = metrics.assign(exp_variant_id=lambda r: r.exp_variant_id.str.title())

    # Reshape metrics DataFrame - from long to wide
    metrics = metrics.pivot_table(
        index=["exp_id", "exp_variant_id"],
        columns=["metric_name", "metric_id"],
        values=["mean", "diff", "conf_int_lower", "conf_int_upper", "p_value"],
    )

    # Add column multi-index names and transpose
    metrics.columns.names = ["statistic", "metric_name", "metric_id"]
    metrics = metrics.transpose()

    # Sort metrics and statistics in the right order
    metrics = metrics.reset_index()
    metrics["metric_id"] = metrics.apply(_enrich_metric_id, axis="columns")
    metrics = metrics.sort_values(by="metric_id")
    metrics = metrics.drop(columns=[("metric_id", "")])

    # Set index and transpose back
    metrics = metrics.set_index(["metric_name", "statistic"])
    metrics = metrics.transpose()

    return metrics


def _enrich_metric_id(row):
    """Auxiliary function for proper order of the metrics and statistics."""
    name = row.iloc[0]
    metric = row.iloc[2]
    if name == "mean":
        return metric + 0.1
    elif name == "diff":
        return metric + 0.2
    elif name == "conf_int_lower":
        return metric + 0.3
    elif name == "conf_int_upper":
        return metric + 0.4
    elif name == "p_value":
        return metric + 0.5


def format_results(
    metrics: pd.DataFrame, experiment: Experiment, format_pct: str = "{:+,.1%}", format_pval: str = "{:,.3f}"
) -> pd.DataFrame:
    """
    Method formatting wide dataframe with results. Using params `format_pct` and `format_pval` you can set number of
    decimals.

    Arguments:
        metrics: dataframe with results in wide format
        experiment: evaluated experiment
        format_pct: optional param with format of columns `Impact`, `Conf. interval lower bound` and `Conf. interval
        upper bound`
        format_pval: optional param with format of `p-value` column

    Returns:
        nicely formatted dataframe
    """
    # Fix ugly naming
    metrics = metrics.rename(
        columns={
            "mean": "Mean",
            "diff": "Impact",
            "conf_int_lower": "Conf. interval lower bound",
            "conf_int_upper": "Conf. interval upper bound",
            "p_value": "p-value",
        }
    )

    # Set names for axis
    metrics.columns.names = ["Metric", "Statistics"]
    metrics.index.names = ["Experiment Id", "Variant"]

    # How should mean (metric value) formatted
    format_mean = [metric.metric_format for metric in experiment.metrics]
    metric_mean_multipliers = [metric.metric_value_multiplier for metric in experiment.metrics]

    # Select appropriate columns
    columns_pct = [col for col in metrics.columns if ("interval" in col[1]) | ("Impact" in col[1])]
    columns_pvalue = [col for col in metrics.columns if "p-value" in col[1]]
    columns_mean = [col for col in metrics.columns if "Mean" in col[1]]

    # Set formatting for specific columns
    columns_pct_format = {col: format_pct for col in columns_pct}
    columns_pvalue_format = {col: format_pval for col in columns_pvalue}
    columns_mean_format = {columns_mean[i]: format_mean[i] for i in range(len(columns_mean))}

    columns_format = {**columns_pct_format, **columns_pvalue_format, **columns_mean_format}

    # Apply metric_value_multiplier, e.g. 1000 for RPM
    for i in range(len(columns_mean)):
        metrics[columns_mean[i]] = metrics[columns_mean[i]] * metric_mean_multipliers[i]

    # Apply columns formatting including colour p-value format
    return metrics.style.format(columns_format).map(_p_value_color_format, subset=columns_pvalue)


def format_metrics_long(
    metrics: pd.DataFrame,
    experiment: Experiment,
    format_pct: str = "{:+,.1%}",
    format_pval: str = "{:,.3f}",
) -> pd.DataFrame:
    """
    Method formatting long dataframe with result metrics. Using params `format_pct` and `format_pval` you can set number of
    decimals.

    Arguments:
        metrics: dataframe with result metrics in long format
        experiment: evaluated experiment
        format_pct: optional param with format of columns `Impact`, `Conf. interval lower bound` and `Conf. interval
        upper bound`
        format_pval: optional param with format of `p-value` column

    Returns:
        nicely formatted dataframe
    """

    metrics = _add_confidence_intervals(metrics)
    # Fix ugly naming
    metrics = metrics.rename(
        columns={
            "exp_id": "Experiment Id",
            "exp_variant_id": "Variant",
            "metric_id": "Metric Id",
            "metric_name": "Metric",
            "mean": "Mean",
            "diff": "Impact",
            "conf_int_lower": "Conf. interval lower bound",
            "conf_int_upper": "Conf. interval upper bound",
            "p_value": "p-value",
            "sum_value": "Value",
        }
    )

    # How should mean (metric value) formatted
    format_mean_df = pd.DataFrame(
        [{"Metric Id": metric.id, "metric_format": metric.metric_format} for metric in experiment.metrics]
    )
    metric_mean_multipliers_df = pd.DataFrame(
        [
            {"Metric Id": metric.id, "metric_value_multiplier": metric.metric_value_multiplier}
            for metric in experiment.metrics
        ]
    )

    # Merge with format_mean_df and metric_mean_multipliers_df to apply formatting
    metrics = metrics.merge(metric_mean_multipliers_df, on="Metric Id", how="inner")
    metrics["Mean"] = metrics["Mean"] * metrics["metric_value_multiplier"]
    metrics["Value"] = metrics["Value"] * metrics["metric_value_multiplier"]

    metrics = metrics.merge(format_mean_df, on="Metric Id", how="inner")
    metrics["Mean"] = metrics.apply(lambda row: row["metric_format"].format(row["Mean"]), axis=1)
    metrics["Value"] = metrics.apply(lambda row: row["metric_format"].format(row["Value"]), axis=1)

    # Select appropriate columns
    columns_pct = [col for col in metrics.columns if ("interval" in col) | ("Impact" in col)]
    columns_format = {
        **{col: format_pct for col in columns_pct},
        "p-value": format_pval,
    }

    metrics = metrics[
        [
            "Experiment Id",
            "Variant",
            "Metric",
            "Mean",
            "Value",
            "Impact",
            "Conf. interval lower bound",
            "Conf. interval upper bound",
            "p-value",
        ]
    ]

    return metrics.style.format(columns_format).map(_p_value_color_format, subset=["p-value"])


def _p_value_color_format(pval):
    """Auxiliary function to set p-value color -- green or red."""
    color = "green" if pval < 0.05 else "red"
    return "color: %s" % color
