.PHONY: install test lint typecheck build demo all

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest -q

lint:
	ruff check .

typecheck:
	mypy src

build:
	python -m build || uv build

demo:
	resultseal replay fixtures/*.yaml

all: test lint typecheck build
