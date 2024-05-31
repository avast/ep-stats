from datetime import datetime
from inspect import signature
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pyparsing import ParseException

from ..toolkit import DEFAULT_CONFIDENCE_LEVEL, DEFAULT_POWER, FilterScope, Parser
from ..toolkit import Experiment as EvExperiment
from ..toolkit import Filter as EvFilter
from ..toolkit import Metric as EvMetric
from ..toolkit import SrmCheck as EvSrmCheck
from ..toolkit import SumRatioCheck as EvSumRatioCheck


class Metric(BaseModel):
    """
    Defines metric to evaluate.
    """

    id: int = Field(
        ...,
        title="Metric Id",
        description="""Database id of the metric, not used at the moment in ep-stats. We only
        repeat this id in response so the caller knows what result belongs to what request.""",
    )
    name: str = Field(
        ...,
        title="Metric Name",
        description="""Official metric name as it appears in EP.
        The name is only for debugging and has no meaning for ep-stats. We only repeat the name in the response
        for caller's convenience.""",
    )
    nominator: str = Field(
        ...,
        title="Metric Nominator",
        description="""EP metric is defined in the form of `nominator / denominator`.
        Both parts are entered as expressions. Example: `count(my_unit_type.unit.conversion)`.""",
    )
    denominator: str = Field(
        ...,
        title="Metric Denominator",
        description="""EP metric is defined in the form of `nominator / denominator`.
        Both parts are entered as expressions. Example: `count(my_unit_type.unit.conversion)`.""",
    )
    minimum_effect: Optional[float] = Field(
        None,
        title="Minimum effect of interest",
        description=f"""The minimum effect of interest is the smallest relative difference that is meaningful to detect,
        defining it allows us to estimate the size of the sample data required to reach {DEFAULT_POWER:.0%} power.""",
    )

    @model_validator(mode="after")
    def check_nominator_denominator(self):
        nominator, denominator = self.nominator, self.denominator
        if not nominator:
            raise ValueError("we expect nominator to be non-empty")
        if not denominator:
            raise ValueError("we expect denominator to be non-empty")
        try:
            parser = Parser(nominator, denominator)
            if not parser.get_goals():
                raise ValueError("We expect the metric to have at least one goal in nominator and denominator")
            return self
        except ParseException as e:
            raise ValueError(f"Cannot parse nominator '{nominator}' or '{denominator}' because of '{e}'")

    def to_metric(self):
        return EvMetric(
            id=self.id,
            name=self.name,
            nominator=self.nominator,
            denominator=self.denominator,
            minimum_effect=self.minimum_effect,
        )


class Check(BaseModel):
    """
    Defines metric to evaluate.
    """

    _SRM_TYPE = "SRM"
    _SUM_RATIO_TYPE = "SumRatio"
    _ALLOWED_CHECKS = {
        _SRM_TYPE: EvSrmCheck,
        _SUM_RATIO_TYPE: EvSumRatioCheck,
    }

    id: int = Field(
        ...,
        title="Check Id",
        description="""Database id of the check, not used at the moment in ep-stats. We only
        repeat this id in response so the caller knows what result belongs to what request.""",
    )
    name: str = Field(
        ...,
        title="Check Name",
        description="""Name to identify each check.""",
    )
    type: str = Field(
        _SRM_TYPE,
        title="Check Type",
        description="""Defines which check to run. Currently supported types are `"SRM", "SumRatio"`.
        Default is `SRM`""",
    )
    nominator: Optional[str] = Field(
        None,
        title="Check Nominator",
        description="""Nominator is only required by `SumRatio` check.
        Example: `count(my_unit_type.global.inconsistent_exposure)`.""",
    )
    denominator: str = Field(
        ...,
        title="Check Denominator",
        description="""Denominator is required by both `SRM` and `SumRatio` checks.
        Example: `count(my_unit_type.global.exposure)`.""",
    )

    @staticmethod
    def _validate_nominator_or_denominator(value, which):
        if not value:
            raise ValueError(f"we expect {which} to be non-empty")

        try:
            parser = Parser(value, value)
            if not parser.get_goals():
                raise ValueError(f"We expect the check to have at least one goal in {which}")
            return value
        except ParseException as e:
            raise ValueError(f"Cannot parse '{value}' because of '{e}'")

    @field_validator("denominator")
    @classmethod
    def check_denominator(cls, value):
        return cls._validate_nominator_or_denominator(value, "denominator")

    @model_validator(mode="after")
    def check_nominator(self):
        class_ = self._ALLOWED_CHECKS[self.type]
        if "nominator" in signature(class_).parameters:
            _ = Check._validate_nominator_or_denominator(self.nominator, "nominator")

        return self

    def to_check(self):
        class_ = self._ALLOWED_CHECKS[self.type]
        return class_(**self.dict())


class Filter(BaseModel):
    """
    Filter specification for data to evaluate.
    """

    dimension: str = Field(..., title="Name of the dimension")

    value: List[Any] = Field(..., title="List of possible values")

    scope: FilterScope = Field(
        ...,
        title="Scope of the filter",
        description="Scope of the filter is either `exposure` or `goal`.",
    )

    def to_filter(self):
        return EvFilter(self.dimension, self.value, self.scope)


class Experiment(BaseModel):
    """
    Experiment to evaluate.
    """

    id: str = Field(
        ...,
        title="Experiment Id",
    )

    control_variant: str = Field(
        ...,
        title="Identification of the control variant",
        description="""All other variant data
        in the experiment are evaluated against this control variant.""",
    )

    variants: Optional[List[str]] = Field(
        None, title="Variants", description="""List of experiment variants to evaluate for."""
    )

    unit_type: str = Field(
        ...,
        title="Experiment/randomization Unit Type",
        description="""Experiment (randomization) unit type is
        needed to correctly retrieve number of exposures per experiment variant.""",
    )

    date_from: Optional[str] = Field(
        None,
        title="Start of the date range",
        description="""Required format is `2020-06-15`.
        `date_from` is optional, data are unbound from the start when `date_from` is not present.""",
    )

    date_to: Optional[str] = Field(
        None,
        title="End of the date range (inclusive)",
        description="""Required format is `2020-06-15`.
        `date_to` is optional, data are unbound from the end when `date_to` is not present.""",
    )

    date_for: Optional[str] = Field(
        None,
        title="Date of the experiment to evaluate for",
        description="""Required format is `2020-06-15`.
        `date_for` is optional. If present, both `date_from` and `date_to` must be present too and `date_for` must be
        between `date_from` and `date_to`. `date_from` and `date_to` set expected experiment duration,
        while `date_for` informs about position within the experiment duration. It is used for sequential analysis.""",
    )
    metrics: List[Metric] = Field(..., title="List of metrics to evaluate")

    checks: List[Check] = Field(..., title="List of checks to evaluate")

    filters: Optional[List[Filter]] = Field(
        None,
        title="Filtering conditions",
        description="""List of filtering conditions to apply on exposure and goals.""",
    )

    query_parameters: dict = Field(
        {},
        title="Custom query parameters used in the data access.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "test-conversion",
                "variants": ["a", "b", "c"],
                "control_variant": "a",
                "unit_type": "test_unit_type",
                "filters": [
                    {"dimension": "element", "value": ["button-1"], "scope": "goal"},
                    {"dimension": "browser", "value": ["firefox"], "scope": "exposure"},
                ],
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
        }
    )

    @field_validator("date_from")
    @classmethod
    def date_from_must_be_date(cls, value):
        if value is not None:
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                raise ValueError("we expect date_from to be in `2020-06-15` format")

        return value

    @field_validator("date_to")
    @classmethod
    def date_to_must_be_date(cls, value):
        if value is not None:
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                raise ValueError("we expect date_to to be in `2020-06-15` format")

        return value

    @model_validator(mode="after")
    def check_date_from_to(self):
        if self.date_for is not None and (self.date_from is None or self.date_to is None):
            raise ValueError("date_for requires date_from and date_to to be present as well")
        if self.date_from is not None and self.date_to is not None:
            try:
                df = datetime.strptime(self.date_from, "%Y-%m-%d")  # noqa: PD901
                dt = datetime.strptime(self.date_to, "%Y-%m-%d")
            except ValueError:
                raise ValueError("cannot parse date_from, date_to")
            if self.date_for is not None:
                try:
                    dfor = datetime.strptime(self.date_for, "%Y-%m-%d")
                except ValueError:
                    raise ValueError("cannot parse date_for")
                if dfor < df:
                    raise ValueError("we expect date_for to be greater or equal to date_from")
                if dfor > dt:
                    raise ValueError("we expect date_for to be less or equal to date_to")
            if dt < df:
                raise ValueError("we expect date_to to be greater or equal to date_from")

        return self

    def to_experiment(self):
        metrics = [m.to_metric() for m in self.metrics]
        checks = [c.to_check() for c in self.checks]
        return EvExperiment(
            self.id,
            self.control_variant,
            metrics,
            checks,
            date_from=self.date_from,
            date_to=self.date_to,
            date_for=self.date_for,
            unit_type=self.unit_type,
            variants=self.variants,
            filters=[f.to_filter() for f in self.filters] if self.filters else [],
            query_parameters=self.query_parameters,
        )


class SampleSizeCalculationData(BaseModel):
    """
    Data needed for the sample size calculation.
    """

    n_variants: int = Field(
        ...,
        title="Number of variants",
        description="Number of variants in the experiment.",
    )

    minimum_effect: float = Field(
        ...,
        title="Minimum effect of interest",
        description="Relative effect, must be greater than zero.",
    )

    mean: float = Field(
        ...,
        title="Current mean",
        description="""Estimate of the current population mean. If `std` is empty,
        it is assumed that the data comes from Bernoulli distribution. In such case,
        `mean` must be between zero and one.""",
    )

    std: Optional[float] = Field(
        None,
        title="Current standard deviation",
        description="""Estimate of the current population standard deviation. If empty,
        it is assumed that the data comes from Bernoulli distribution. In such case,
        `mean` must be between zero and one.""",
    )

    confidence_level: float = Field(DEFAULT_CONFIDENCE_LEVEL, title="Confidence level")

    power: float = Field(DEFAULT_POWER, title="Power")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "minimum_effect": 0.1,
                "mean": 0.2,
                "std": 1.2,
                "n_variants": 2,
            }
        }
    )
