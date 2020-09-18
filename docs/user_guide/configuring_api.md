# Integration

This short integration guide assumes you are familiar with [Basic Principles](../principles.md).

## Access to Data

To evaluate a metric in experiment, we have to compile metric definition that comes in form of nominator and denominator expressions into some underlying data source in the form that is vastly company or use-case specific. We use class [`DAO`](../api/dao.md) to interface underlying data source. [`DAO`](../api/dao.md) gets all the information contained in [`Experiment`](../api/experiment.md) and needs to compile it into SQL or something else understandable by company's data systems to provide pre-aggregated or by-unit goals.

Following snippet shows one way how to aggregate data to provide input in form of pre-aggregated goals in some implementation of [`DAO`](../api/dao.md) class.

```sql
SELECT
    -- we aggregate secondly by all dims required by ep-stats and omit `unit_id`
    -- this way we get correct $\sum x^2$ values in `sum_sqr_value` to calculate
    -- correct sample standard deviation of real-valued metrics.
    exp_id,
    exp_variant_id,
    unit_type,
    agg_type,
    goal,
    dimension,
    dimension_value,
    SUM(sum_cnt) count,
    SUM(sum_cnt * sum_cnt) sum_sqr_count,
    SUM(value) sum_value,
    SUM(value * value) sum_sqr_value,
    SUM(unique) count_unique
    FROM (
        -- we aggregate firstly by all dims required by ep-stats and by `unit_id`
        SELECT
            exp_id,
            exp_variant_id,
            unit_type,
            agg_type,
            goal,
            dimension,
            dimension_value,
            unit_id,
            SUM(cnt) sum_cnt,
            SUM(value) value,
            IF(SUM(cnt) > 0, 1, 0) unique
            FROM events
            GROUP BY
                exp_id,
                exp_variant_id,
                unit_type,
                agg_type,
                goal,
                dimension,
                dimension_value,
                unit_id
    ) u
    GROUP BY
        exp_id,
        exp_variant_id,
        unit_type,
        agg_type,
        goal,
        dimension,
        dimension_value
```

## Configuring REST API

After having access to our data in custom implementation of [`Dao`](../api/dao.md) class e.g. `CustomDao`, we can follow up an example in [`main.py`](/doodlebug/ep-stats-lib/tree/master/src/epstats/main.py) to configure the REST API with our `CustomDao`. We need to implement `CustomDaoFactory` that creates instances of our `CustomDao` for every request served. We can then customize `get_dao_factory()` method in `main.py` and to launch the server.

```python
def get_dao_factory():
    return CustomDaoFactory(...)


def main():
    from .config import config

    logging.config.dictConfig(config['logging'])
    serve('my_package:api', settings.api, config['logging'])


if __name__ == '__main__':
    main()
```
