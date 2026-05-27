.PHONY: setup dev test lint spec-validate docker-build

setup:
	cd backend && python -m pip install -r requirements.txt
	cd frontend && npm install

dev:
	@echo "Run backend: cd backend && uvicorn main:app --reload --port 8000"
	@echo "Run frontend: cd frontend && npm run dev"

test:
	cd backend && pytest tests -v
	cd frontend && npm run test

lint:
	cd backend && ruff check .
	cd frontend && npm run lint

spec-validate:
	python scripts/validate_specs.py

docker-build:
	docker compose build
