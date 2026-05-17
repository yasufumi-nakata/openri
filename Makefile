.PHONY: test build frontend package check-package smoke clean

test:
	PYTHONPATH=backend python3 -m pytest backend/tests -q

frontend:
	cd frontend && npm run build

package:
	rm -rf dist build *.egg-info backend/*.egg-info
	python3 -m build

check-package: package
	python3 -m twine check dist/*

smoke:
	PYTHONPATH=backend python3 -m openri.cli check samples/high_risk_manuscript.txt --fail-on high || test $$? -eq 1

build: test frontend check-package smoke

clean:
	rm -rf dist build *.egg-info backend/*.egg-info .pytest_cache .ruff_cache
