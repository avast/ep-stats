import pandas as pd

from .experiment import Experiment


def results_long_to_wide(metrics: pd.DataFrame) -> pd.DataFrame:
    """Adjusts metric results from long format to wide."""

    # Compute lower and upper bound for confidence interval
    metrics["conf_int_lower"] = metrics["diff"] - metrics["confidence_interval"]
    metrics["conf_int_upper"] = metrics["diff"] + metrics["confidence_interval"]

    # Change experiment variants to upper case
    metrics = metrics.assign(exp_variant_id=lambda r: r.exp_variant_id.str.title())

    # Reshape metrics DataFrame - from long to wide
    r = metrics.pivot_table(
        index=["exp_id", "exp_variant_id"],
        columns=["metric_name", "metric_id"],
        values=["mean", "diff", "conf_int_lower", "conf_int_upper", "p_value"],
    )

    # Add column multi-index names and transpose
    r.columns.names = ["statistic", "metric_name", "metric_id"]
    r = r.transpose()

    # Sort metrics and statistics in the right order
    r.reset_index(inplace=True)  # noqa: PD002
    r["metric_id"] = r.apply(_enrich_metric_id, axis="columns")
    r.sort_values(by="metric_id", inplace=True)  # noqa: PD002
    r.drop(columns=[("metric_id", "")], inplace=True)  # noqa: PD002

    # Set index and transpose back
    r.set_index(["metric_name", "statistic"], inplace=True)  # noqa: PD002
    r = r.transpose()

    return r


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
    r: pd.DataFrame, experiment: Experiment, format_pct: str = "{:+,.1%}", format_pval: str = "{:,.3f}"
) -> pd.DataFrame:
    """
    Method formatting wide dataframe with resutls. Using params `format_pct` and `format_pval` you can set number of
    decimals.

    Arguments:
        r: dataframe with resutls in wide format
        experiment: evaluated experiment
        format_pct: optional param with format of columns `Impact`, `Conf. interval lower bound` and `Conf. interval
        upper bound`
        format_pval: optional param with format of `p-value` column

    Returns:
        nicely formated dataframe
    """
    # Fix ugly naming
    r.rename(
        columns={
            "mean": "Mean",
            "diff": "Impact",
            "conf_int_lower": "Conf. interval lower bound",
            "conf_int_upper": "Conf. interval upper bound",
            "p_value": "p-value",
        },
        inplace=True,  # noqa: PD002
    )

    # Set names for axis
    r.columns.names = ["Metric", "Statistics"]
    r.index.names = ["Experiment Id", "Variant"]

    # How should mean (metric value) formated
    format_mean = [metric.metric_format for metric in experiment.metrics]
    metric_mean_multipliers = [metric.metric_value_multiplier for metric in experiment.metrics]

    # Select appropriate columns
    columns_pct = [col for col in r.columns if ("interval" in col[1]) | ("Impact" in col[1])]
    columns_pvalue = [col for col in r.columns if "p-value" in col[1]]
    columns_mean = [col for col in r.columns if "Mean" in col[1]]

    # Set formatting for specific columns
    columns_pct_format = {col: format_pct for col in columns_pct}
    columns_pvalue_format = {col: format_pval for col in columns_pvalue}
    columns_mean_format = {columns_mean[i]: format_mean[i] for i in range(len(columns_mean))}

    columns_format = {**columns_pct_format, **columns_pvalue_format, **columns_mean_format}

    # Apply metric_value_multiplier, e.g. 1000 for RPM
    for i in range(len(columns_mean)):
        r[columns_mean[i]] = r[columns_mean[i]] * metric_mean_multipliers[i]

    # Apply columns formatting including colour p-value format
    return r.style.format(columns_format).map(_p_value_color_format, subset=columns_pvalue)


def _p_value_color_format(pval):
    """Auxiliary function to set p-value color -- green or red."""
    color = "green" if pval < 0.05 else "red"
    return "color: %s" % color
