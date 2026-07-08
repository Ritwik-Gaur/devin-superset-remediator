.PHONY: test run docker-build docker-up simulate scan publish-issues

test:
	python3 -m unittest discover -s tests -v

run:
	python3 -m app

docker-build:
	docker compose build

docker-up:
	docker compose up --build

simulate:
	python3 scripts/seed_demo.py

scan:
	python3 scripts/local_superset_scan.py superset-fork > .data/scan-results.json

publish-issues:
	python3 scripts/publish_superset_issues.py issues/superset-remediation-plan.json
