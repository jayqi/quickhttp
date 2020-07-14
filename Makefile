.PHONY: build clean clean-build clean-docs clean-test lint test

build: clean-build
	poetry build

clean: clean-build clean-docs clean-test

clean-build:
	find . -name *.pyc -delete && find . -name __pycache__ -delete
	rm -rf dist
	rm -rf quickhttp.egg-info

clean-docs:
	rm -rf site

clean-test:
	rm -f .coverage
	rm -f coverage.xml
	rm -rf htmlcov/
	rm -rf .pytest_cache

docs: clean-docs
	cp README.md docs/index.md
	mkdocs build

lint:
	black --check quickhttp tests
	flake8 quickhttp tests

test:
	pytest -s
