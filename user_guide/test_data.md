# Test Data

We made testing data part of the `epstats` python package to simplify development and to provide real
example of input data and formats required by `epstats`.

There are test goal data in both pre-aggregated and by-unit forms. See [`TestData`](../api/test_data.md) for various access methods.

Test data itself are saved as csv files in [src/epstats/toolkit/testing/resources](/doodlebug/ep-stats-lib/tree/master/src/epstats/toolkit/testing/resources). They include pre-aggregated and by-unit goals together with pre-computed evaluations of metrics, checks, and exposures that are used to assert our unit-tests against (e.g. in [`test_experiment.py`](/doodlebug/ep-stats-lib/tree/master/tests/epstats/toolkit/test_experiment.py)).

## How to Update Test Data

We keep master of test data in [google spreadsheet](https://docs.google.com/spreadsheets/d/1e9snKuhVd_JN69zhlE0DSrJ3RRS6suEezebwtMQQP6s/edit#gid=1085989942) because we implemented statistical procedure in the sheet itself to pre-calculate experiment evaluations we then use in unit test asserts.
