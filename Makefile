# Federal Contract Spending Efficiency Analysis
# `make all` reproduces every published number from a clean checkout.

PY ?= python

.PHONY: help install ingest analyse warehouse validate report powerbi deck sample all test lint clean distclean

help:
	@echo "install    editable install with dev extras"
	@echo "ingest     pull USAspending extracts into data/interim"
	@echo "analyse    build curated tables into data/curated"
	@echo "warehouse  load DuckDB and install SQL views"
	@echo "validate   run data-quality contracts (fails the build on ERROR)"
	@echo "report     render dashboard and BI exports into outputs/"
	@echo "powerbi    build the Power BI model into work-in-progress/powerbi/"
	@echo "deck       build the PowerPoint leave-behind (needs Node.js)"
	@echo "all        ingest -> analyse -> warehouse -> validate -> report -> powerbi"
	@echo "test       run the pytest suite"
	@echo "lint       ruff check"
	@echo "clean      remove derived data and outputs (keeps the API cache)"

install:
	$(PY) -m pip install -e ".[dev]"

ingest:
	$(PY) -m fedspend.cli ingest

analyse:
	$(PY) -m fedspend.cli analyse

warehouse:
	$(PY) -m fedspend.cli warehouse

validate:
	$(PY) -m fedspend.cli validate

report:
	$(PY) -m fedspend.cli report

powerbi:
	$(PY) -m fedspend.cli powerbi

deck:
	$(PY) -m fedspend.cli deck

sample:
	$(PY) -m fedspend.cli sample

all:
	$(PY) -m fedspend.cli all

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check src tests

clean:
	rm -rf data/interim data/curated outputs/figures outputs/tables outputs/dashboard.html

distclean: clean
	rm -rf data/raw
