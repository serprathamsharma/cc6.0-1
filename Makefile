.PHONY: up down migrate lint test e2e eval dev-api dev-web shell-api shell-db

up:
	docker compose up --build -d

down:
	docker compose down -v

migrate:
	docker compose exec api alembic upgrade head

lint:
	cd api && ruff check . && mypy api/ worker/ --ignore-missing-imports

test:
	cd api && pytest tests/ -x -q

e2e:
	cd frontend && npx playwright test e2e/

eval:
	cd api && python evals/run_evals.py

dev-api:
	cd api && uvicorn api.main:app --reload --port 8000

dev-web:
	cd frontend && npm run dev

shell-api:
	docker compose exec api bash

shell-db:
	docker compose exec postgres psql -U scoutiq scoutiq

logs:
	docker compose logs -f api worker

format:
	cd api && ruff format .

install-api:
	cd api && pip install -r requirements.txt

install-web:
	cd frontend && npm install
