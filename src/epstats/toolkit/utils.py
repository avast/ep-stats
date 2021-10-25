import pytz
import pandas as pd


def get_utc_timestamp(dt):
    mytz = pytz.timezone("UTC")
    return mytz.normalize(mytz.localize(dt, is_dst=False))


def goals_wide_to_long(df: pd.DataFrame, unit_type: str = "test_unit_type") -> pd.DataFrame:
    """
    Modify the input DataFrame in a way that it can be evaluatetd using Experiment.evaluate_agg().

    Arguments:
        df: dataframe in wide format - one row per variant and aggregated data in columns
        unit_type: should be the same value as the `unit_type` passed to `Experiment`

    Returns:
        dataframe in long format - one row per variant and goal

    Input dataframe example:
    ```
    experiment_id   variant_id  views   clicks  conversions     bookings    bookings_squared
    my-exp          a           473661  48194   413             17152       803105
    my-exp          b           471485  47184   360             14503       677178
    my-exp          c           477159  48841   406             15892       711661
    my-exp          d           474934  49090   289             11995       566700
    ```
    """

    # Do not modify the input `df` via reference
    df = df.copy()
    # Rename first two columns
    df.columns = ["exp_id", "exp_variant_id"] + df.columns.to_list()[2:]

    # DataFrame `sum_value` to long format
    # Select non squared columns and switch from long to wide
    cols = [col for col in df.columns.to_list()[2:] if "square" not in col]
    df_long = pd.melt(
        df, id_vars=["exp_id", "exp_variant_id"], value_vars=cols, var_name="goal", value_name="sum_value"
    )

    # DataFrame `sum_sqr_value` to long format
    # Select squared columns and swich from long to wide
    cols_squared = [col for col in df.columns.to_list()[2:] if "square" in col]
    df_long_sqr = pd.melt(
        df, id_vars=["exp_id", "exp_variant_id"], value_vars=cols_squared, var_name="goal", value_name="sum_sqr_value"
    )
    df_long_sqr["goal"] = df_long_sqr["goal"].apply(lambda x: "_".join(x.split("_")[:-1]))

    # Merge together and add other necessary columns for evaluation
    goals = pd.merge(left=df_long, right=df_long_sqr, how="outer", on=["exp_id", "exp_variant_id", "goal"])
    goals.insert(2, "unit_type", unit_type)
    goals.insert(3, "agg_type", "global")
    goals.insert(5, "dimension", "")
    goals.insert(6, "dimension_value", "")
    goals.insert(7, "count", 0)
    goals.insert(8, "sum_sqr_count", 0)
    goals.insert(11, "count_unique", 0)
    goals["sum_sqr_value"] = goals.apply(_add_value_squared_where_missing, axis="columns")

    return goals


def _add_value_squared_where_missing(row):
    """Add values `value_squared` where missing."""
    value_squared = row[-2]
    value = row[-3]

    if value_squared != value_squared:
        return value
    else:
        return value_squared
