## Installation

You can install this package via `pip`.

```bash
pip install ep-stats
```

## Running

You can run a testing version of ep-stats via

```bash
python -m epstats
```

Then see Swagger on [http://localhost:8080/docs](http://localhost:8080/docs) for API documentation.

## Contributing

To get started locally, you can clone the repo and quickly get started using the `Makefile`.

```bash
git clone https://github.com/avast/ep-stats.git
cd ep-stats
make install-dev
```

It sets a new virtual environment `venv` in `./venv` using [venv](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/), installs all development dependencies, and sets [pre-commit](https://pre-commit.com/) git hooks to keep the code neatly formatted with [flake8](https://pypi.org/project/flake8/) and [brunette](https://pypi.org/project/brunette/).

To run tests, you can use `Makefile` as well.

```bash
source venv/bin/activate  # activate python environment
make check
```

To run a development version of ep-stats do

```bash
source venv/bin/activate
cd src
python -m epstats
```

## Base Example

Ep-stats allows for quick experiment evaluation. We are using provided testing data to evaluate metric `Click-through Rate` in experiment `test-conversion`.

```python
from epstats.toolkit import Experiment, Metric, SrmCheck
experiment = Experiment(
    'test-conversion',
    'a',
    [Metric(
        1,
        'Click-through Rate',
        'count(test_unit_type.unit.click)',
        'count(test_unit_type.global.exposure)'),
    ],
    [SrmCheck(1, 'SRM', 'count(test_unit_type.global.exposure)')],
    unit_type='test_unit_type')

# This gets testing data, use other Dao or get aggregated goals in some other way.
from epstats.toolkit.testing import TestData
goals = TestData.load_goals_agg(experiment.id)

# evaluate experiment
ev = experiment.evaluate_agg(goals)
```

`ev` contains evaluations of exposures, metrics and checks. This will have following output.

`ev.exposures`:

| exp_id | exp_variant_id | exposures |
| :----- | :------------- | --------: |
|test-conversion|a|21|
|test-conversion|b|26|

`ev.metrics`:

| exp_id | metric_id | metric_name | exp_variant_id | count | mean | std | sum_value | confidence_level | diff | test_stat | p_value | confidence_interval | standard_error | degrees_of_freedom |
| :----- | --------: | :---------- | -------------: | ----: | ---: | --: | --------: | ---------------: | ---: | --------: | ------: | ------------------: | -------------: | -----------------: |
|test-conversion|1|Click-through Rate|a|21|0.238095|0.436436|5|0.95|0|0|1|1.14329|0.565685|40|
|test-conversion|1|Click-through Rate|b|26|0.269231|0.452344|7|0.95|0.130769|0.223152|0.82446|1.18137|0.586008|43.5401|

`ev.checks`:

| exp_id | check_id | check_name | variable_id | value |
| :----- | -------: | :--------- | :---------- | ----: |
|test-conversion|1|SRM|p_value|0.465803|
|test-conversion|1|SRM|test_stat|0.531915|
|test-conversion|1|SRM|confidence_level|0.999000|
