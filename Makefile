VERSION := $(shell quickhttp --version)

.PHONY=build
build: clean-build
	poetry build

.PHONY=clean
clean: clean-build clean-docs clean-test

.PHONY=clean-build
clean-build:
	find . -name *.pyc -delete && find . -name __pycache__ -delete
	rm -rf dist
	rm -rf quickhttp.egg-info

.PHONY=clean-docs
clean-docs:
	rm -rf site

.PHONY=clean-test
clean-test:
	rm -f .coverage
	rm -f coverage.xml
	rm -rf htmlcov/
	rm -rf .pytest_cache

.PHONY=docs
docs: clean-docs
	cp README.md docs/index.md
	cp CHANGELOG.md docs/changelog.md
	mkdocs build

.PHONY=lint
lint:
	black --check quickhttp tests
	flake8 quickhttp tests

.PHONY=typecheck
typecheck:
	mypy quickhttp tests

.PHONY=test
test:
	pytest -vv
