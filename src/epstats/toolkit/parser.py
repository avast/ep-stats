from typing import Set
from pyparsing import (
    Word,
    alphas,
    oneOf,
    infixNotation,
    opAssoc,
    nums,
    ParseException,
    alphanums,
)
import pandas as pd


class Parser:
    """
    Parse and evaluate nominator and denominator expressions from goals and give various
    access to parsed forms to e.g. create simple compiler to sql code.
    """

    def __init__(self, nominator: str, denominator: str):
        func = Word(alphas)
        unit_type = Word(alphas + "_").setParseAction(UnitType)
        agg_type = Word(alphas).setParseAction(AggType)
        goal = Word(alphas + "_" + nums).setParseAction(Goal)
        number = Word(nums).setParseAction(Number)
        dimension = Word(alphas + "_").setParseAction(Dimension)
        dimension_value = Word(alphanums + "_" + "-" + "." + "%").setParseAction(DimensionValue)

        ep_goal = (func + "(" + unit_type + "." + agg_type + "." + goal + ")").setParseAction(EpGoal)
        ep_goal_with_dimension = (
            func + "(" + unit_type + "." + agg_type + "." + goal + "(" + dimension + "=" + dimension_value + ")" + ")"
        ).setParseAction(EpGoal)
        operand = number | ep_goal | ep_goal_with_dimension

        multop = oneOf("*")
        divop = oneOf("/")
        plusop = oneOf("+")
        subop = oneOf("-")

        expr = infixNotation(
            operand,
            [
                (multop, 2, opAssoc.LEFT, MultBinOp),
                (divop, 2, opAssoc.LEFT, DivBinOp),
                (plusop, 2, opAssoc.LEFT, PlusBinOp),
                (subop, 2, opAssoc.LEFT, SubBinOp),
            ],
        )

        self._nominator_expr = expr.parseString(nominator)[0]
        self._denominator_expr = expr.parseString(denominator)[0]

    def evaluate_agg(self, goals: pd.DataFrame):
        """
        Get `count`, `sum_value`, `sum_value_sqr` numpy array of shape (variants, metrics) after
        evaluating nominator and denominator expressions from pre-aggregated goals.

        Arguments:
            goals: one row per experiment variant

        See [`Experiment.evaluate_agg`][epstats.toolkit.experiment.Experiment.evaluate_agg] for details
        on `goals` at input.

        Returns:
            numpy array of shape (variants, metrics) where metrics are in order of
            (count, sum_value, sum_sqr_value)
        """
        sum_value = self._nominator_expr.evaluate_agg(goals)
        sum_sqr_value = self._nominator_expr.evaluate_sqr(goals)
        count = self._denominator_expr.evaluate_agg(goals)
        return count, sum_value, sum_sqr_value

    def evaluate_by_unit(self, goals: pd.DataFrame):
        """
        Get `count`, `sum_value`, `sum_value_sqr` numpy array of shape (variants, metrics) after
        evaluating nominator and denominator expressions from goals aggregated by unit.

        Arguments:
            goals: one row per experiment variant

        See [`Experiment.evaluate_agg`][epstats.toolkit.experiment.Experiment.evaluate_by_unit] for details
        on `goals` at input.

        Returns:
            numpy array of shape (variants, metrics) where metrics are in order of
            (count, sum_value, sum_sqr_value)
        """
        value_variants, value = self._nominator_expr.evaluate_by_unit(goals, "sum_value")
        value_df = (
            pd.DataFrame(
                {
                    "exp_variant_id": value_variants,  # go through variants
                    "sum_value": value,
                    "sum_sqr_value": value * value,
                }
            )
            .groupby("exp_variant_id")
            .sum()
        )

        count_variants, count = self._denominator_expr.evaluate_by_unit(goals, "count")
        count_df = pd.DataFrame({"exp_variant_id": count_variants, "count": count}).groupby("exp_variant_id").sum()

        df = value_df.join(count_df)
        return df["count"], df["sum_value"], df["sum_sqr_value"]

    def get_goals(self) -> Set:
        """
        Get set of goals that appear in `nominator` and `denominator` expressions as `EpGoal` instances.
        """
        return self._nominator_expr.get_goals().union(self._denominator_expr.get_goals())

    def get_goals_str(self) -> Set[str]:
        """
        Gets set of goals that appear in `nominator` and `denominator` expressions as strings.
        """
        return self._nominator_expr.get_goals_str().union(self._denominator_expr.get_goals_str())


class UnitType:
    def __init__(self, t):
        self.unit_type = t[0]

    def __str__(self):
        return self.unit_type

    __repr__ = __str__


class AggType:
    def __init__(self, t):
        if t[0] not in ["unit", "global"]:
            raise ParseException(f"Only `unit` and `global` aggregation types are supported but `{t[0]}` received.")
        self.agg_type = t[0]

    def __str__(self):
        return self.agg_type

    __repr__ = __str__


class Goal:
    def __init__(self, t):
        self.goal = t[0]

    def __str__(self):
        return self.goal

    __repr__ = __str__


class Dimension:
    def __init__(self, t):
        self.dimension = t[0]

    def __str__(self):
        return self.dimension

    __repr__ = __str__


class DimensionValue:
    def __init__(self, t):
        self.dimension_value = t[0]

    def __str__(self):
        return self.dimension_value

    __repr__ = __str__


class Number:
    def __init__(self, t):
        self.value = float(t[0])

    def __str__(self):
        return f"{self.value}"

    def evaluate_agg(self, goals):
        return self.value

    def evaluate_by_unit(self, goals):
        return self.evaluate_agg(goals)

    def evaluate_sqr(self, goals):
        return self.value * self.value

    def get_goals_str(self) -> Set[str]:
        return set()

    def get_goals(self) -> Set:
        return set()

    __repr__ = __str__


class EpGoal:
    """
    Represents one specification of a goal in nominator or denominator expression
    eg. `count(test_unit_type.global.conversion(product=product_1))` where
    dimensional part is optional.
    """

    def __init__(self, t):
        if t[0] not in ["value", "count", "unique"]:
            raise ParseException(f"Only `value`, `count`, `unique` functions are supported but `{t[0]}` received.")
        if t[0] == "value":
            self.column = "sum_value" if t[0] == "value" else "count"
            self.column_sqr = "sum_sqr_value" if t[0] == "value" else "sum_sqr_count"
        if t[0] == "count":
            self.column = "count"
            self.column_sqr = "sum_sqr_count"
        if t[0] == "unique":
            self.column = "count_unique"
            self.column_sqr = "count_unique"

        self.unit_type = t[2].unit_type
        self.agg_type = t[4].agg_type
        self.goal = t[6].goal
        self.dimension = t[8].dimension if len(t) > 8 else ""
        self.dimension_value = t[10].dimension_value if len(t) > 8 else ""

    def _to_string(self):
        dimension = f"[{self.dimension}={self.dimension_value}]" if self.dimension != "" else ""
        return f"{self.unit_type}.{self.agg_type}.{self.goal}{dimension}"

    def __str__(self):
        return self._to_string()

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return self._to_string() == other._to_string()

    def __hash__(self):
        return hash(self._to_string())

    def evaluate_agg(self, goals):
        return self._evaluate_agg(goals, self.column)

    def evaluate_by_unit(self, goals, key):
        g = goals[
            (goals["unit_type"] == self.unit_type)
            & (goals["agg_type"] == self.agg_type)
            & (goals["dimension"] == self.dimension)
            & (goals["dimension_value"] == self.dimension_value)
        ]
        return g["exp_variant_id"], g.xs(key=key, level=1, axis=1)[self.goal]

    def evaluate_sqr(self, goals):
        return self._evaluate_agg(goals, self.column_sqr)

    def _evaluate_agg(self, goals, column):
        return goals[
            (goals["unit_type"] == self.unit_type)
            & (goals["agg_type"] == self.agg_type)
            & (goals["goal"] == self.goal)
            & (goals["dimension"] == self.dimension)
            & (goals["dimension_value"] == self.dimension_value)
        ][column].values

    def get_goals_str(self) -> Set[str]:
        return {self._to_string()}

    def get_goals(self) -> Set:
        return {self}

    def is_dimensional(self):
        return self.dimension != "" and self.dimension_value != ""

    __repr__ = __str__


class BinOp:
    """
    Operation connecting `EpGoal` or `Number` terms in nominator or denominator expression
    eg. `value(test_unit_type.unit.conversion) - value(test_unit_type.unit.refund)`.
    """

    def __init__(self, t):
        self.args = t[0][0::2]

    def symbol(self):
        raise NotImplementedError()

    def evaluate_agg(self, goals):
        raise NotImplementedError()

    def evaluate_by_unit(self, goals):
        raise NotImplementedError()

    def evaluate_sqr(self, goals):
        raise NotImplementedError()

    def get_goals_str(self) -> Set[str]:
        return set().union(*map(lambda o: o.get_goals_str(), self.args))

    def get_goals(self) -> Set[str]:
        return set().union(*map(lambda o: o.get_goals(), self.args))

    def __str__(self):
        sep = f" {self.symbol()} "
        return "(" + sep.join(map(str, self.args)) + ")"

    __repr__ = __str__


class PlusBinOp(BinOp):
    def symbol(self):
        return "+"

    def evaluate_agg(self, goals):
        return self.args[0].evaluate_agg(goals) + self.args[1].evaluate_agg(goals)

    def evaluate_sqr(self, goals):
        return self.args[0].evaluate_sqr(goals) + self.args[1].evaluate_sqr(goals)

    def evaluate_by_unit(self, goals):
        return self.args[0].evaluate_by_unit(goals) + self.args[1].evaluate_by_unit(goals)


class MultBinOp(BinOp):
    def symbol(self):
        return "*"

    def evaluate_agg(self, goals):
        return self.args[0].evaluate_agg(goals) * self.args[1].evaluate_agg(goals)

    def evaluate_sqr(self, goals):
        return self.args[0].evaluate_sqr(goals) * self.args[1].evaluate_sqr(goals)

    def evaluate_by_unit(self, goals):
        return self.args[0].evaluate_by_unit(goals) * self.args[1].evaluate_by_unit(goals)


class DivBinOp(BinOp):
    def symbol(self):
        return "/"

    def evaluate_agg(self, goals):
        return self.args[0].evaluate_agg(goals) / self.args[1].evaluate_agg(goals)

    def evaluate_sqr(self, goals):
        return self.args[0].evaluate_sqr(goals) / self.args[1].evaluate_sqr(goals)

    def evaluate_by_unit(self, goals):
        return self.args[0].evaluate_by_unit(goals) / self.args[1].evaluate_by_unit(goals)


class SubBinOp(BinOp):
    def symbol(self):
        return "-"

    def evaluate_agg(self, goals):
        return self.args[0].evaluate_agg(goals) - self.args[1].evaluate_agg(goals)

    def evaluate_sqr(self, goals):
        return self.args[0].evaluate_sqr(goals) - self.args[1].evaluate_sqr(goals)

    def evaluate_by_unit(self, goals):
        return self.args[0].evaluate_by_unit(goals) - self.args[1].evaluate_by_unit(goals)
