.PHONY: clean clean-test clean-pyc clean-build docs help conform release-test release codebuild coverage
.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"
AWS := aws

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test clean-c9 ## remove all build, test, coverage and Python artifacts

clean-c9:
	find . -type f -name ".~c9*.py" -print -delete

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -type d -name '*.egg-info' -exec rm -fr {} +
	find . -type d -name '*.egg' -exec rm -rf {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

test: ## run tests quickly with the default Python
# 	poetry run python -m behave tests/features
	poetry run python -m pytest tests -vv -s -x

test-all: ## run tests on every Python version with tox
	poetry run python -m tox --skip-missing-interpreters

coverage: ## check code coverage quickly with the default Python
	#poetry run coverage run --source kafka_connect_watcher -m behave tests/features --junit
	poetry run python -m pytest -W ignore --cov=kafka_connect_watcher --cov-report term-missing:skip-covered --cov-report lcov:docs/cov.info --log-level=CRITICAL
	poetry run coverage report -m
	poetry run coverage xml -o coverage/coverage.xml
	poetry run coverage html
	$(BROWSER) htmlcov/index.html

.ONESHELL:

codebuild: ## check code coverage quickly with the default Python
	coverage run --source kafka_connect_watcher -m behave tests/features --junit;\
	BEHAVE=$$? ;\
	coverage run --source kafka_connect_watcher -a -m pytest tests/pytests -vv -x ;\
	PYTEST=$$? ;\
	echo $$BEHAVE
	echo $$PYTEST
	coverage report -m
	coverage xml -o coverage/coverage.xml
	if [ $$BEHAVE -eq 0 ] && [ $$PYTEST -eq 0 ]; then exit 0; else exit 1; fi

docs: clean-c9 ## generate Sphinx HTML documentation, including API docs
	rm -f docs/kafka_connect_watcher.rst
	rm -f docs/modules.rst
	find docs -name "kafka_connect_watcher.*.rst" -print -delete
		sphinx-apidoc -o docs/ kafka_connect_watcher
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	$(BROWSER) docs/_build/html/index.html

nightly-docs: docs
	echo Uploading to s3://${NIGHTLY_DOCS_BUCKET} && \
	cd docs/_build/html && \
	$(AWS) s3 sync . s3://${NIGHTLY_DOCS_BUCKET}/ \
	--acl public-read --sse AES256 --storage-class ONEZONE_IA

publish-docs: docs
	cd docs/_build/html && \
	$(AWS) s3 sync . s3://${DOCS_BUCKET}/ \
	--storage-class ONEZONE_IA

servedocs: docs ## compile the docs watching for changes
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

release: dist ## package and upload a release
	twine check dist/*
	poetry publish --build

release-test: dist ## package and upload a release
	twine check dist/* || echo Failed to validate release
	poetry config repositories.pypitest https://test.pypi.org/legacy/
	poetry publish -r pypitest --build

dist: clean ## builds source and wheel package
	poetry build
	ls -l dist

install: conform ## install the package to the active Python's site-packages
	pip install . --use-pep517 #--use-feature=in-tree-build

conform	: ## Conform to a standard of coding syntax
	isort --profile black kafka_connect_watcher || poetry run isort --profile black kafka_connect_watcher
	black kafka_connect_watcher || poetry run black kafka_connect_watcher
	find kafka_connect_watcher -name "*.json" -type f  -exec sed -i '1s/^\xEF\xBB\xBF//' {} +
