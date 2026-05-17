.PHONY: test coverage lint oss-health build frontend package check-package smoke clean

test:
	PYTHONPATH=backend python3 -m pytest backend/tests -q

coverage:
	PYTHONPATH=backend python3 -m pytest backend/tests -q --cov=openri --cov-report=term-missing

lint:
	python3 -m ruff check backend/openri backend/tests scripts

oss-health:
	python3 scripts/oss_health_check.py

frontend:
	cd frontend && npm run build

package:
	rm -rf dist build *.egg-info backend/*.egg-info
	python3 -m build

check-package: package
	python3 -m twine check dist/*

smoke:
	PYTHONPATH=backend python3 -m openri.cli check samples/high_risk_manuscript.txt --fail-on high || test $$? -eq 1

build: lint oss-health coverage frontend check-package smoke

clean:
	rm -rf dist build *.egg-info backend/*.egg-info .pytest_cache .ruff_cache
