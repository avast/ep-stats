ruff:
	poetry run ruff check src/epstats tests

test:
	poetry run pytest

check: ruff test

install:
	poetry update
	poetry install

install-dev: install
	poetry run ipython kernel install --user --name=ep-stats
	poetry run pre-commit autoupdate
	poetry run pre-commit install

clean:
	rm -rf build src/__pycache__ src/epstats/__pycache__ src/epstats/server/__pycache__ __pycache__ \
	tests/__pycache__ tests/epstats/__pycache__ .pytest_cache src/*.egg-info .eggs tests/epstats/__pycache__\
	tests/epstats/toolkit/__pycache__ tests/epstats/toolkit/testing/__pycache__ \
	src/epstats/toolkit/__pycache__ src/epstats/toolkit/testing/__pycache__ \
	src/epstats/toolkit/testing/resources/__pycache__ \
	tests/epstats/server/__pycache__ tests/epstats/toolkit/__pycache__

locust-evaluate:
	locust -f src/epstats/locust.py --headless --host http://localhost:8080 -u 40 -r 5 --tags evaluate

locust-health:
	locust -f src/epstats/locust.py --headless --host https://localhost:8080 -u 1000 -r 50 --tags health
