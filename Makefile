.PHONY: env init dev up build down down-v logs ps migrate fixtures

env:
	test -f .env || cp .env.example .env
	test -f backend/.env || cp backend/.env.example backend/.env

init: env build migrate fixtures
	@echo "Frontend: http://localhost:3000"
	@echo "Django admin: http://localhost:8000/admin/"

dev: env build migrate
	@echo "Frontend: http://localhost:3000"
	@echo "Django admin: http://localhost:8000/admin/"

up: env
	docker compose up -d

build: env
	docker compose up --build -d

down:
	docker compose down

down-v:
	docker compose down -v

logs:
	docker compose logs -f

ps:
	docker compose ps

migrate:
	docker compose exec backend uv run python manage.py migrate

fixtures:
	docker compose exec backend uv run python manage.py loaddata fixtures/users_data.json fixtures/hotels_data.json fixtures/bookings_data.json

db-redo: env
	docker compose down -v
	docker compose up --build -d
	docker compose exec backend uv run python manage.py migrate
	docker compose exec backend uv run python manage.py loaddata fixtures/users_data.json fixtures/hotels_data.json fixtures/bookings_data.json