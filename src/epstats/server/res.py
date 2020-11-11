import pandas as pd
from typing import List
from pydantic import BaseModel, Field

from ..toolkit import Evaluation
from .req import Experiment, Metric, Check


class MetricStat(BaseModel):
    """
    Per-variant metric evaluation result.
    """

    exp_variant_id: str = Field(title="Variant in the Experiment")
    diff: float = Field(
        title="Difference",
        description="""Relative difference of means of this variant and control variant.
        If this is a variant `b` and `a` is the control variant, then `diff = (b.mean - a.mean) / a.mean`.""",
    )
    mean: float = Field(
        title="Metric Mean",
        description="""Nominator and denominator to calculate the mean
        are given in metric definition. `mean = nominator / denominator`.""",
    )
    sum_value: float = Field(
        title="Metric Value",
        description="""Value of the metric, it is given by the
        nominator in the metric definition.""",
    )
    p_value: float = Field(
        title="p-Value",
        description="""We calculate p-value (under `confidence_level` statistical significance) of the relative
        difference (`diff`) of this variant mean and the control variant mean. We use
        [2-tailed Welch's test](https://en.wikipedia.org/wiki/Welch%27s_t-test)
        with unknown and unequal variance assumption and Welch–Satterthwaite equation approximation of degrees
        of freedom.""",
    )
    confidence_interval: float = Field(
        title="Confidence Interval",
        description="""Confidence interval for relative difference ('diff`)
        of means of this variant and control variant - `[mean - confidence_interval, mean + confidence_interval]`.
        Associated confidence level is the next parameter.""",
    )
    confidence_level: float = Field(
        title="Confidence Level (Statistical Significance)",
        description="""Confidence level used
        to compute (obtain) `confidence_interval`.""",
    )

    @staticmethod
    def from_df(df: pd.DataFrame):
        return [
            MetricStat(
                exp_variant_id=r["exp_variant_id"],
                diff=r["diff"],
                mean=r["mean"],
                sum_value=r["sum_value"],
                p_value=r["p_value"],
                confidence_interval=r["confidence_interval"],
                confidence_level=r["confidence_level"],
            )
            for i, r in df.iterrows()
        ]


class MetricResult(BaseModel):
    """
    Result of single metric evaluation.
    """

    id: int = Field(
        title="Metric Id",
        description="""Database id of the metric, not used at the moment in ep-stats""",
    )
    name: str = Field(
        title="Metric Name",
        description="""Official metric name as it appears in EP.
        The name is only for debugging and has no meaning for ep-stats.""",
    )
    stats: List[MetricStat] = Field(
        title="Per-variant statistics",
        description="""List with one entry per
        variant statistical results.""",
    )

    @staticmethod
    def from_df(metrics: List[Metric], df: pd.DataFrame):
        return [MetricResult(id=m.id, name=m.name, stats=MetricStat.from_df(df[df.metric_id == m.id])) for m in metrics]


class CheckStat(BaseModel):
    variable_id: str = Field(
        title="Check Variable",
        description="""Every check can return different
        variables and their values. E.g. SRM check returns `test_stat` and `p_value` variables with
        their `value`s.""",
    )
    value: float = Field(
        title="Value of the Variable",
        description="""Value of some variable returned by
        the check. E.g. SRM check returns `test_stat` and `p_value` variables with
        their `value`s.""",
    )

    @staticmethod
    def from_df(df: pd.DataFrame):
        return [CheckStat(variable_id=r["variable_id"], value=r["value"]) for i, r in df.iterrows()]


class CheckResult(BaseModel):
    """
    Result of single check evaluation.
    """

    id: int = Field(
        title="Check Id",
        description="Database id of the check, not used at the moment.",
    )
    name: str = Field(
        title="Check Name",
        description="""Official check name as it appears in EP.
        The name is only for debugging and has no meaning for ep-stats.""",
    )
    stats: List[CheckStat] = Field(
        title="Per-variant statistics",
        description="""List with one entry per
        variant statistical results.""",
    )

    @staticmethod
    def from_df(checks: List[Check], df: pd.DataFrame):
        return [CheckResult(id=c.id, name=c.name, stats=CheckStat.from_df(df[df.check_id == c.id])) for c in checks]


class ExposureStat(BaseModel):
    """
    Exposures in the experiment per-variant.
    """

    exp_variant_id: str = Field(title="Variant in the Experiment")
    count: int = Field(
        title="Per-variant exposures",
        description="""Exposure count of experiment (randomization) unit.""",
    )

    @staticmethod
    def from_df(df: pd.DataFrame):
        return [ExposureStat(exp_variant_id=r["exp_variant_id"], count=r["exposures"]) for i, r in df.iterrows()]


class ExposureResult(BaseModel):
    """
    Exposures in the experiment.
    """

    unit_type: str = Field(
        title="Experiment/randomization Unit Type",
        description="""Experiment (randomization) unit type is
    needed to correctly retrieve number of exposures per experiment variant.""",
    )
    stats: List[ExposureStat] = Field(
        title="Experiment Exposures",
        description="""List with experiment variant exposure counts per entry.""",
    )

    @staticmethod
    def from_df(experiment: Experiment, df: pd.DataFrame):
        return ExposureResult(unit_type=experiment.unit_type, stats=ExposureStat.from_df(df))


class Result(BaseModel):
    """
    Result of experiment evaluation.

    Top-level element in the response.
    """

    id: str = Field(
        title="Experiment Id",
    )
    metrics: List[MetricResult] = Field(
        title="Metric Results",
        description="""List with one entry per evaluated metric.""",
    )
    checks: List[CheckResult] = Field(
        title="Check Results",
        description="""List with one entry per evaluated check.""",
    )
    exposure: ExposureResult = Field(title="Experiment Exposures")

    @staticmethod
    def from_evaluation(experiment: Experiment, evaluation: Evaluation):
        metrics = MetricResult.from_df(experiment.metrics, evaluation.metrics)
        checks = CheckResult.from_df(experiment.checks, evaluation.checks)
        exposure = ExposureResult.from_df(experiment, evaluation.exposures)

        return Result(id=experiment.id, metrics=metrics, checks=checks, exposure=exposure)

    class Config:
        schema_extra = {
            "example": {
                "id": "test-conversion",
                "metrics": [
                    {
                        "id": 1,
                        "name": "Click-through Rate",
                        "stats": [
                            {
                                "exp_variant_id": "a",
                                "diff": 0,
                                "mean": 0.23809523809523808,
                                "sum_value": 5,
                                "p_value": 1,
                                "confidence_interval": 1.1432928868841614,
                                "confidence_level": 0.95,
                            },
                            {
                                "exp_variant_id": "b",
                                "diff": 0.13076923076923078,
                                "mean": 0.2692307692307692,
                                "sum_value": 7,
                                "p_value": 1,
                                "confidence_interval": 1.2327467657322932,
                                "confidence_level": 0.95,
                            },
                            {
                                "exp_variant_id": "c",
                                "diff": 0.26,
                                "mean": 0.3,
                                "sum_value": 9,
                                "p_value": 1,
                                "confidence_interval": 1.352808784877644,
                                "confidence_level": 0.95,
                            },
                        ],
                    }
                ],
                "checks": [
                    {
                        "id": 1,
                        "name": "SRM",
                        "stats": [
                            {"variable_id": "p_value", "value": 0.4528439055646014},
                            {"variable_id": "test_stat", "value": 1.5844155844155843},
                            {"variable_id": "confidence_level", "value": 0.999},
                        ],
                    }
                ],
                "exposure": {
                    "unit_type": "test_unit_type",
                    "stats": [
                        {"exp_variant_id": "a", "count": 21},
                        {"exp_variant_id": "b", "count": 26},
                        {"exp_variant_id": "c", "count": 30},
                    ],
                },
            }
        }
