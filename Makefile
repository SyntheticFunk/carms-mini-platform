.PHONY: db-up db-down data install test-db

db-up:
	docker compose up -d

db-down:
	docker compose down

install:
	pip install -e .

data:
	python scripts/fetch_dnokes_data.py

test-db:
	python -c "from carms_platform.db import engine; print(engine.url)"
