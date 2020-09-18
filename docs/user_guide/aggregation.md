# Aggregation

## Goals in Metric Definition

Goals in the metric definition look like

```value(test_unit_type.unit.conversion)```

where

* `count`, `value`, or `unique` determines we need *number* of goals recorded or their *value* (e.g. USD bookings of `conversion` goal) or that we need only info if at least 1 goal has been collected.
* `test_unit_type` is a type of the unit the goal has been recorded for.
* `unit` or `global` are types of aggregation.
* `conversion` is a name of the goal.

## Supported Unit Types

Ep-stats support any type of randomization unit. It is a responsibility of an integrator to correctly query for the data.

### Note on Randomization

It is necessary for the statistics to work correctly that unit exposures are randomly (independently and identically a.k.a. IID) distributed within one experiment into its variants. This is usually the case when we randomize at pageview or event session unit types.

In general, one unit can experience the experiment variant multiple times.

Violation of IID leads to uncontrolled false-positive errors in metric evaluation. Ep-stats remedies this IID violation by using [delta method for IID](../stats/ctr.md##asymptotic-distribution-of-ctr).

## Aggregation Types

There are 2 types or levels of aggregation of goals available:

1. `global` aggregates goals as if one goal is one observation.
1. `unit` aggregates goals first per unit (e.g. count of `conversion` goals per unit id `unit_1`).

### Unit Aggregation Type

We need to use *unit aggregation type* when we calculate any "per User" or generally any "per exposure" metrics. It is "per User" metric so we need all goals that happened for one user represented as one observation of one unit. This is required for correct calculation of sample standard deviation which is a basic block in all statistical evaluation methods.

For example, if there are 2 `conversion` goals for unit id `unit_1`, we want to have 2 as a count of `conversion` goals for this unit id making it 1 observation rather than having 2 separate observations of `conversion` goals.

### Global Aggregation Type

*Global aggregation type* skips "per User" aggregation step described in previous section and treats every goal as one observation. This is now enough for all metrics that are not based directly on exposures of the experiment randomization unit type.

For example Refund Rate metric defined as `count(test_unit_type.global.refund) / count(test_unit_type.global.conversion)` does not need to use unit aggregation type because 1 observation is 1 `conversion` that can have only zero or one `refund` goal.

This kind of metrics needs application of delta method or bootstrapping which has not been implemented yet.

## Dimensional Goals

Metric goal definition allows to filter goals by supported dimensions. For example we can specify that we want transactional metrics to be calculated only for transactions involving VPN products. Or we want Revenue per Mile or CTR metrics calculated for particular screen.

For example Average Bookings of product `p_1` can be defined as

```
value(test_unit_type.unit.conversion(product=p_1)) / count(test_unit_type.global.exposure)
```

Different goals may allow filtering by different dimensions.

!!!note
    Dimensions are not supported yet.

## Example

See [Test Data](test_data.md) for examples of pre-aggregated goals that make input to statistical evaluation using [`Experiment.evaluate_agg`](../api/experiment.md#epstats.toolkit.experiment.Experiment.evaluate_agg) or per unit goals that make input to statistical evaluation using [`Experiment.evaluate_by_unit`](../api/experiment.md#epstats.toolkit.experiment.Experiment.evaluate_by_unit).
