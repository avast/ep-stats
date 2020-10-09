![](https://img.shields.io/github/workflow/status/avast/ep-stats/Code%20Checks?color=green)
[![PyPI version](https://img.shields.io/pypi/v/ep-stats?color=green)](https://pypi.org/project/ep-stats/)
[![Python versions](https://img.shields.io/pypi/pyversions/ep-stats?color=green)](https://pypi.org/project/ep-stats/)
[![Code style](https://img.shields.io/badge/formatted%20with-brunette-362511)](https://github.com/odwyersoftware/brunette)
[![Code style](https://img.shields.io/badge/styled%20with-flake8-green)](https://flake8.pycqa.org/en/latest/)
![](https://img.shields.io/github/languages/code-size/avast/ep-stats?color=green)
<img src="theme/experiment_b.png" align="right" />

# ep-stats

**Statistical package for the experimentation platform.**

It provides a general Python package and REST API that can be used to evaluate any metric
in an AB test experiment.

## Features

* Robust two-tailed t-test implementation with multiple p-value corrections and delta methods applied.
* Sequential evaluations allow experiments to be stopped early.
* Connect it to any data source to get either pre-aggregated or per randomization unit data.
* Simple expression language to define arbitrary metrics.
* REST API to integrate it as a service in experimentation portal with score cards.

## Documentation

We have got a lovely [documentation](https://avast.github.io/ep-stats/).

## Base Example

ep-stats allows for a quick experiment evaluation. We are using sample testing data to evaluate metric `Click-through Rate` in experiment `test-conversion`.

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

`ev` contains evaluations of exposures, metrics, and checks. This will provide the following output.

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

Then, see Swagger on [http://localhost:8080/docs](http://localhost:8080/docs) for API documentation.

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

### Documentation

To update documentation run

```bash
mkdocs gh-deploy
```

It updates documentation in GitHub pages stored in branch `gh-pages`.

## Inspiration

Software engineering practices of this package have been heavily inspired by marvelous [calmcode.io](https://calmcode.io/) site managed by [Vincent D. Warmerdam](https://github.com/koaning).
