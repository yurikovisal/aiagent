COMPOSE = docker compose -f docker/docker-compose.yml
COMPOSE_DEV = $(COMPOSE) -f docker/docker-compose.dev.yml
COMPOSE_GPU = $(COMPOSE) -f docker/docker-compose.gpu.yml

.PHONY: env up up-dev up-gpu down logs health test lint api-shell

env:
	@test -f .env || cp .env.example .env
	@echo ".env ready"

up: env
	$(COMPOSE) up --build -d

up-dev: env
	$(COMPOSE_DEV) up --build

up-gpu: env
	$(COMPOSE_GPU) up --build -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f api

health:
	curl -sS http://localhost:8000/health | python3 -m json.tool

test:
	cd backend && python -m pytest -q

lint:
	cd backend && ruff check app tests

api-shell:
	$(COMPOSE) exec api bash
