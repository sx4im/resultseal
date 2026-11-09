.PHONY: install test lint typecheck build demo all

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest -q

lint:
	python -m ruff check .

typecheck:
	python -m mypy src

build:
	python -m build

demo:
	resultseal replay fixtures/*.yaml

all: test lint typecheck build
