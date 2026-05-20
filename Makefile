# EpidemiTracker - Makefile
# Cibles courantes pour développement et déploiement

COMPOSE := docker compose
COMPOSE_PROD := docker compose -f docker-compose.yml -f docker-compose.prod.yml

.PHONY: help build up down logs ps shell migrate makemigrations seed test lint keys prod-up prod-down restart

help:
	@echo "EpidemiTracker - cibles disponibles :"
	@echo "  make build           - build des images Docker"
	@echo "  make up              - lancer la stack dev (postgres, redis, web, worker, beat, channels)"
	@echo "  make down            - arrêter la stack"
	@echo "  make logs            - suivre les logs"
	@echo "  make ps              - lister les services"
	@echo "  make shell           - shell Django interactif (manage.py shell_plus)"
	@echo "  make bash            - bash dans le conteneur web"
	@echo "  make migrate         - appliquer les migrations"
	@echo "  make makemigrations  - générer les migrations"
	@echo "  make seed            - charger les données de référence (maladies, points entrée, rôles, formulaire Ebola)"
	@echo "  make test            - lancer les tests pytest"
	@echo "  make lint            - ruff + black --check"
	@echo "  make keys            - générer les clés crypto Ed25519 pour le QR pass"
	@echo "  make prod-up         - lancer la stack production (Traefik + monitoring)"

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart web worker beat channels

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) ps

shell:
	$(COMPOSE) exec web python manage.py shell_plus

bash:
	$(COMPOSE) exec web bash

migrate:
	$(COMPOSE) exec web python manage.py migrate

makemigrations:
	$(COMPOSE) exec web python manage.py makemigrations

seed:
	$(COMPOSE) exec web python manage.py seed_reference_data
	$(COMPOSE) exec web python manage.py seed_ebola_form

test:
	$(COMPOSE) exec web pytest -q

lint:
	$(COMPOSE) exec web ruff check apps config
	$(COMPOSE) exec web black --check apps config

keys:
	$(COMPOSE) exec web python manage.py generate_pass_keys

prod-up:
	$(COMPOSE_PROD) up -d --build

prod-down:
	$(COMPOSE_PROD) down
