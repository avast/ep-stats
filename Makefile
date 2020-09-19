brunette:
	brunette src/epstats tests setup.py --check

flake:
	flake8 src/epstats tests setup.py

test:
	pytest

check: brunette flake test

install:
	python -m pip install -e .

venv:
	python -m pip install virtualenv
	python -m virtualenv venv

install-dev: venv
	source venv/bin/activate && python -m pip install -e ".[dev]"
	source venv/bin/activate && pre-commit install
	source venv/bin/activate && python -m pip install ipykernel
	source venv/bin/activate && ipython kernel install --user --name=ep-stats

install-test:
	python -m pip install -e ".[test]"

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
