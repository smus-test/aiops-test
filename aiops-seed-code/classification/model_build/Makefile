.PHONY: lint init clean help

PROJECT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
PROJECT_NAME = marketing-classification
PYTHON_INTERPRETER = python3

## Lint using flake8
lint:
	flake8 source_scripts ml_pipelines

## Setup git hooks
init:
	git config core.hooksPath .githooks

## Clean build artifacts
clean:
	rm -f cdk.staging
	rm -rf cdk.out
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '.coverage' -exec rm -fr {} +
	find . -name '.pytest_cache' -exec rm -fr {} +
	find . -name '.tox' -exec rm -fr {} +
	find . -name '__pycache__' -exec rm -fr {} +

## Run tests
test:
	pytest tests/ -v

.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Available commands:"
	@echo "  lint   - Run flake8 linting"
	@echo "  init   - Setup git hooks"
	@echo "  clean  - Clean build artifacts"
	@echo "  test   - Run tests"
