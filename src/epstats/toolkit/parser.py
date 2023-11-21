from typing import Set
from collections import Counter
from pyparsing import (
    Word,
    alphas,
    oneOf,
    infixNotation,
    opAssoc,
    nums,
    ParseException,
    alphanums,
    delimitedList,
    Optional,
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
        number = (Optional("-") + Word(nums)).setParseAction(Number)
        dimension = Word(alphanums + "_").setParseAction(Dimension)
        dimension_value_chars = alphanums + "_" + "-" + "." + "%" + " " + "/" + "|"
        dimension_operator = oneOf("< = > <= >= =^ !=")
        dimension_value = (dimension_operator + Word(dimension_value_chars)).setParseAction(DimensionValue)
        dimension_list = delimitedList(dimension + dimension_value)

        ep_goal = (func + "(" + unit_type + "." + agg_type + "." + goal + ")").setParseAction(EpGoal)
        ep_goal_with_dimensions = (
            func + "(" + unit_type + "." + agg_type + "." + goal + "(" + dimension_list + ")" + ")"
        ).setParseAction(EpGoal)
        operand = number | ep_goal | ep_goal_with_dimensions

        multop = oneOf("*")
        divop = oneOf("/")
        plusop = oneOf("+")
        subop = oneOf("-")
        tildaop = oneOf("~")

        expr = infixNotation(
            operand,
            [
                (multop, 2, opAssoc.LEFT, MultBinOp),
                (divop, 2, opAssoc.LEFT, DivBinOp),
                (plusop, 2, opAssoc.LEFT, PlusBinOp),
                (subop, 2, opAssoc.LEFT, SubBinOp),
                (tildaop, 2, opAssoc.LEFT, TildaBinOp),
            ],
        )

        self._nominator_expr = expr.parseString(nominator)[0]
        self._denominator_expr = expr.parseString(denominator)[0]
        self._update_dimension_to_value()

    def _update_dimension_to_value(self):
        """
        To every `EpGoal`, we need to add missing dimensions that are present
        in other `EpGoal` instances so the row masking can work properly.
        """

        all_dimensions = {d for g in self.get_goals() for d in g.dimension_to_value.keys()}
        for goal in self.get_goals():
            for dimension in all_dimensions:
                if dimension not in goal.dimension_to_value:
                    goal.dimension_to_value[dimension] = ""

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
        if t[0] == "=":
            self.dimension_value = t[1]

        elif t[0] == "=^":
            self.dimension_value = "^" + t[1]

        else:
            self.dimension_value = "".join(t)

    def __str__(self):
        return self.dimension_value

    __repr__ = __str__


class Number:
    def __init__(self, t):
        self.value = float("".join(t))

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

        dimensions = [d.dimension for d in t if isinstance(d, Dimension)]
        dimension_values = [v.dimension_value for v in t if isinstance(v, DimensionValue)]
        self._raise_if_duplicate_dimensions(dimensions)
        # empty dict if no dimensions
        self.dimension_to_value = {d: v for d, v in zip(dimensions, dimension_values)}

    @staticmethod
    def _raise_if_duplicate_dimensions(dimensions):
        duplicates = {k: v for k, v in Counter(dimensions).items() if v > 1}
        if duplicates:
            raise ParseException(f"Multiple values encountered for dimensions: `{list(duplicates.keys())}`.")

    def _to_string(self):
        if self.is_dimensional():
            # we want to avoid stuff like `name=>=value` when formatting the dimensions
            dimension_list = ", ".join(
                f"{d}{v}" if v[0] in "><=!" else f"{d}={v}" for d, v in self.dimension_to_value.items() if v != ""
            )
            dimensions = f"[{dimension_list}]"
        else:
            dimensions = ""

        return f"{self.unit_type}.{self.agg_type}.{self.goal}{dimensions}"

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

    def _get_dimension_mask(self, goals):
        mask = pd.Series([True] * len(goals))
        for dimension, dimension_value in self.dimension_to_value.items():
            mask &= goals[dimension] == dimension_value

        return mask

    def evaluate_by_unit(self, goals, key):
        g = goals[
            (goals["unit_type"] == self.unit_type)
            & (goals["agg_type"] == self.agg_type)
            & self._get_dimension_mask(goals)
        ]
        return g["exp_variant_id"], g.xs(key=key, level=1, axis=1)[self.goal]

    def evaluate_sqr(self, goals):
        return self._evaluate_agg(goals, self.column_sqr)

    def _evaluate_agg(self, goals, column):
        groupby_columns = ["exp_id", "exp_variant_id", "unit_type", "agg_type", "goal"]
        return (
            goals[
                (goals["unit_type"] == self.unit_type)
                & (goals["agg_type"] == self.agg_type)
                & (goals["goal"] == self.goal)
                & self._get_dimension_mask(goals)
            ]
            .groupby(groupby_columns)
            .agg({column: sum})[column]
            .values
        )

    def get_goals_str(self) -> Set[str]:
        return {self._to_string()}

    def get_goals(self) -> Set:
        return {self}

    def is_dimensional(self):
        return bool([v for v in self.dimension_to_value.values() if v != ""])

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


class TildaBinOp(BinOp):
    """
    Tilda treats the second operand as negative,
    resulting in substraction of values and addition of squared values.
    """

    def symbol(self):
        return "~"

    def evaluate_agg(self, goals):
        return self.args[0].evaluate_agg(goals) - self.args[1].evaluate_agg(goals)

    def evaluate_sqr(self, goals):
        return self.args[0].evaluate_sqr(goals) + self.args[1].evaluate_sqr(goals)

    def evaluate_by_unit(self, goals):
        return self.args[0].evaluate_by_unit(goals) - self.args[1].evaluate_by_unit(goals)
