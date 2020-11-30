import pytest

from epstats.toolkit.experiment import Experiment
from epstats.toolkit.testing.utils import check_docstring


@pytest.mark.parametrize("m", [m for m in dir(Experiment) if not m.startswith("_")])
def test_experiment_docstring(m):
    check_docstring(getattr(Experiment, m).__doc__, indent=8)
