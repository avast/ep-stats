ruff:
    uv run ruff check src/epstats tests

test:
    uv run pytest

check: ruff test

install:
    uv sync

install-dev: install
    uv run ipython kernel install --user --name=ep-stats
    uv run pre-commit autoupdate
    uv run pre-commit install

clean:
    rm -rf build src/__pycache__ src/epstats/__pycache__ src/epstats/server/__pycache__ __pycache__ \
    tests/__pycache__ tests/epstats/__pycache__ .pytest_cache src/*.egg-info .eggs tests/epstats/__pycache__\
    tests/epstats/toolkit/__pycache__ tests/epstats/toolkit/testing/__pycache__ \
    src/epstats/toolkit/__pycache__ src/epstats/toolkit/testing/__pycache__ \
    src/epstats/toolkit/testing/resources/__pycache__ \
    tests/epstats/server/__pycache__ tests/epstats/toolkit/__pycache__
