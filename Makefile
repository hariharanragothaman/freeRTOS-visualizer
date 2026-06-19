.PHONY: help install install-dev test cov cov-html demo stats timeline clean

PY ?= python3
VENV ?= .venv
BIN := $(VENV)/bin

help:
	@echo "Targets:"
	@echo "  install      Create venv and install runtime + GUI dependencies"
	@echo "  install-dev  Create venv and install headless test dependencies only"
	@echo "  test         Run the test suite"
	@echo "  cov          Run tests with a terminal coverage report"
	@echo "  cov-html     Run tests and write an HTML coverage report to htmlcov/"
	@echo "  demo         Run the headless serial-simulator demo"
	@echo "  stats        Print task statistics from a simulated run"
	@echo "  timeline     Render a Gantt-style timeline PNG from a simulated run"
	@echo "  clean        Remove caches and coverage artifacts"

$(BIN)/python:
	$(PY) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip

install: $(BIN)/python
	$(BIN)/python -m pip install -r requirements.txt

install-dev: $(BIN)/python
	$(BIN)/python -m pip install pyserial pytest pytest-cov

test:
	$(BIN)/python -m pytest -v

cov:
	$(BIN)/python -m pytest --cov=freertos_visualizer --cov-report=term-missing

cov-html:
	$(BIN)/python -m pytest --cov=freertos_visualizer --cov-report=html
	@echo "Open htmlcov/index.html"

demo:
	$(BIN)/python examples/run_demo.py

stats:
	$(BIN)/python examples/print_stats.py

timeline:
	$(BIN)/python examples/plot_timeline.py --out timeline.png

clean:
	rm -rf .pytest_cache htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
