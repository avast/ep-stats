import pytest
from src.epstats.toolkit.statistics import Statistics


@pytest.mark.parametrize(
    "test_length, actual_day, expected",
    [
        (14, 0, 1.00),
        (14, 1, 1.00),
        (14, 2, 1.00),
        (14, 3, 1.00),
        (14, 14, 0.95),
        (7, 1, 1.00),
        (28, 4, 1.00),
        (28, 8, 0.9998),
        (28, 28, 0.95),
    ],
)
def test_obf_alpha_spending_function(test_length, actual_day, expected):

    alpha = Statistics.obf_alpha_spending_function(0.95, test_length, actual_day)
    assert alpha == expected
