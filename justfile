# Keep in sync with just-version in .github/workflows/*.yml
set minimum-version := '1.55.0'

python := "3.13"

# Print this help documentation
help:
    just --list

# Sync dev environment dependencies
sync:
    uv sync --python {{python}}

# Run linting
lint:
    ruff format --check
    ruff check

# Run formatting
format:
    ruff format
    ruff check --fix

# Audit GitHub Actions workflows with zizmor (passes through args)
zizmor *args:
    uvx --exclude-newer "7 days" zizmor .github/ {{args}}

# Run static typechecking
typecheck:
    uv run --python {{python}} --no-dev --group typecheck --isolated \
        mypy . --install-types --non-interactive

# Run tests
test *args:
    uv run --python {{python}} --no-editable --no-dev --group test --isolated \
        python -I -m pytest {{args}}

# Run all tests with Python version matrix
test-all:
    for python in 3.11 3.12 3.13 3.14 3.15; do \
        just python=$python test; \
    done
