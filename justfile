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
    for python in 3.8 3.9 3.10 3.11 3.12 3.13; do \
        just python=$python test; \
    done

# Build docs
[working-directory: 'docs']
docs:
    mkdocs build

# Serve docs
[working-directory: 'docs']
docs-serve:
    mkdocs serve
