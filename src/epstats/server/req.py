from typing import List, Optional, Any
from pydantic import BaseModel, validator, root_validator, Field
from pyparsing import ParseException
from datetime import datetime
from statsd import StatsClient

from ..toolkit import Experiment as EvExperiment, Filter as EvFilter, FilterScope
from ..toolkit import Metric as EvMetric
from ..toolkit import SrmCheck as EvSrmCheck
from ..toolkit import Parser


class Metric(BaseModel):
    """
    Defines metric to evaluate.
    """

    id: int = Field(
        title="Metric Id",
        description="""Database id of the metric, not used at the moment in ep-stats. We only
        repeat this id in response so the caller knows what result belongs to what request.""",
    )
    name: str = Field(
        title="Metric Name",
        description="""Official metric name as it appears in EP.
        The name is only for debugging and has no meaning for ep-stats. We only repeat the name in the response
        for caller's convenience.""",
    )
    nominator: str = Field(
        title="Metric Nominator",
        description="""EP metric is defined in the form of `nominator / denominator`.
        Both parts are entered as expressions. Example: `count(my_unit_type.unit.conversion)`.""",
    )
    denominator: str = Field(
        title="Metric Denominator",
        description="""EP metric is defined in the form of `nominator / denominator`.
        Both parts are entered as expressions. Example: `count(my_unit_type.unit.conversion)`.""",
    )

    @validator("id")
    def id_must_be_not_empty(cls, value):
        if not value:
            raise ValueError("we expect id to be non-empty")
        return value

    @validator("name")
    def name_must_be_not_empty(cls, value):
        if not value:
            raise ValueError("we expect name to be non-empty")
        return value

    @validator("nominator")
    def nominator_must_be_not_empty(cls, value):
        if not value:
            raise ValueError("we expect nominator to be non-empty")
        return value

    @validator("denominator")
    def denominator_must_be_not_empty(cls, value):
        if not value:
            raise ValueError("we expect denominator to be non-empty")
        return value

    @root_validator
    def check_nominator_denominator(cls, values):
        nominator, denominator = values.get("nominator"), values.get("denominator")
        if not nominator:
            raise ValueError("we expect nominator to be non-empty")
        if not denominator:
            raise ValueError("we expect denominator to be non-empty")
        try:
            parser = Parser(nominator, denominator)
            if not parser.get_goals():
                raise ValueError("We expect the metric to have at least one goal in nominator and denominator")
            return values
        except ParseException as e:
            raise ValueError(f"Cannot parse nominator '{nominator}' or '{denominator}' because of '{e}'")

    def to_metric(self):
        return EvMetric(self.id, self.name, self.nominator, self.denominator)


class Check(BaseModel):
    """
    Defines metric to evaluate.

    Only `SRM` check is available at the moment.
    """

    id: int = Field(
        title="Check Id",
        description="""Database id of the check, not used at the moment in ep-stats. We only
        repeat this id in response so the caller knows what result belongs to what request.""",
    )
    name: str = Field(
        title="Check Name",
        description="""Official check name as it appears in EP. The name is only for debugging
        and has no meaning for ep-stats. We only repeat the name in the response for caller's convenience.""",
    )
    denominator: str = Field(
        title="Check Denominator",
        description="""EP metric is defined in the form of `nominator / denominator`.
        Both parts are entered as expressions.

        The only supported check is SRM check and it should be called with denominator
        of `count(my_unit_type.global.exposure)`.""",
    )

    @validator("id")
    def id_must_be_not_empty(cls, value):
        if not value:
            raise ValueError("we expect id to be non-empty")
        return value

    @validator("name")
    def name_must_be_not_empty(cls, value):
        if not value:
            raise ValueError("we expect name to be non-empty")
        return value

    @validator("denominator")
    def denominator_must_be_not_empty(cls, value):
        if not value:
            raise ValueError("we expect denominator to be non-empty")
        return value

    @validator("denominator")
    def check_denominator(cls, value):
        try:
            parser = Parser(value, value)
            if not parser.get_goals():
                raise ValueError("We expect the check to have at least one goal in denominator")
            return value
        except ParseException as e:
            raise ValueError(f"Cannot parse '{value}' because of '{e}'")

    def to_check(self):
        return EvSrmCheck(self.id, self.name, self.denominator)


class Filter(BaseModel):
    """
    Filter specification for data to evaluate.
    """

    dimension: str = Field(title="Name of the dimension")

    value: List[Any] = Field(title="List of possible values")

    scope: FilterScope = Field(
        title="Scope of the filter", description="Scope of the filter is either `exposure` or `goal`."
    )

    @validator("dimension")
    def dimension_must_be_not_empty(cls, value):
        if not value:
            raise ValueError("we expect dimension to be non-empty")
        return value

    @validator("scope")
    def scope_must_be_not_empty(cls, value):
        if not value:
            raise ValueError("we expect scope to be either `exposure` or `goal`")
        return value

    @validator("value")
    def value_must_be_not_empty(cls, value):
        if not value:
            raise ValueError("we expect value to be non-empty")
        return value

    def to_filter(self):
        return EvFilter(self.dimension, self.value, self.scope)


class Experiment(BaseModel):
    """
    Experiment to evaluate.
    """

    id: str = Field(
        title="Experiment Id",
    )

    control_variant: str = Field(
        title="Identification of the control variant",
        description="""All other variant data
        in the experiment are evaluated against this control variant.""",
    )

    variants: Optional[List[str]] = Field(
        title="Variants", description="""List of experiment variants to evaluate for."""
    )

    unit_type: str = Field(
        title="Experiment/randomization Unit Type",
        description="""Experiment (randomization) unit type is
        needed to correctly retrieve number of exposures per experiment variant.""",
    )

    date_from: Optional[str] = Field(
        title="Start of the date range",
        description="""Required format is `2020-06-15`.
        `date_from` is optional, data are unbound from the start when `date_from` is not present.""",
        default=None,
    )

    date_to: Optional[str] = Field(
        title="End of the date range (inclusive)",
        description="""Required format is `2020-06-15`.
        `date_to` is optional, data are unbound from the end when `date_to` is not present.""",
        default=None,
    )

    date_for: Optional[str] = Field(
        title="Date of the experiment to evaluate for",
        description="""Required format is `2020-06-15`.
        `date_for` is optional. If present, both `date_from` and `date_to` must be present too and `date_for` must be
        between `date_from` and `date_to`. `date_from` and `date_to` set expected experiment duration,
        while `date_for` informs about position within the experiment duration. It is used for sequential analysis.""",
        default=None,
    )
    metrics: List[Metric] = Field(title="List of metrics to evaluate")

    checks: List[Check] = Field(title="List of checks to evaluate")

    filters: Optional[List[Filter]] = Field(
        title="Filtering conditions", description="""List of filtering conditions to apply on exposure and goals."""
    )

    @validator("id")
    def id_must_be_not_empty(cls, value):
        if not value:
            raise ValueError("we expect id to be non-empty")
        return value

    @validator("control_variant")
    def control_variant_must_be_not_empty(cls, value):
        if not value:
            raise ValueError("we expect control_variant to be non-empty")
        return value

    @validator("date_from")
    def date_from_must_be_date(cls, value):
        if value is not None:
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                raise ValueError("we expect date_from to be in `2020-06-15` format")

        return value

    @validator("date_to")
    def date_to_must_be_date(cls, value):
        if value is not None:
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                raise ValueError("we expect date_to to be in `2020-06-15` format")

        return value

    @root_validator
    def check_date_from_to(cls, values):
        date_from, date_to, date_for = (
            values.get("date_from"),
            values.get("date_to"),
            values.get("date_for"),
        )
        if date_for is not None and (date_from is None or date_to is None):
            raise ValueError("date_for requires date_from and date_to to be present as well")
        if date_from is not None and date_to is not None:
            try:
                df = datetime.strptime(date_from, "%Y-%m-%d")
                dt = datetime.strptime(date_to, "%Y-%m-%d")
            except ValueError:
                raise ValueError("cannot parse date_from, date_to")
            if date_for is not None:
                try:
                    dfor = datetime.strptime(date_for, "%Y-%m-%d")
                except ValueError:
                    raise ValueError("cannot parse date_for")
                if dfor < df:
                    raise ValueError("we expect date_for to be greater or equal to date_from")
                if dfor > dt:
                    raise ValueError("we expect date_for to be less or equal to date_to")
            if dt < df:
                raise ValueError("we expect date_to to be greater or equal to date_from")

        return values

    def to_experiment(self, statsd: StatsClient):
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
            statsd=statsd,
            filters=[f.to_filter() for f in self.filters] if self.filters else [],
        )

    class Config:
        schema_extra = {
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
