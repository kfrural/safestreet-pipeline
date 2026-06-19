.PHONY: help install dev-install lint typecheck test clean db-up db-down db-reset pipeline dashboard run-all pre-commit

help:
	@echo "SafeStreet Pipeline - Comandos Disponíveis"
	@echo "----------------------------------------"
	@echo "make install       - Instalar dependências de produção"
	@echo "make dev-install   - Instalar dependências de desenvolvimento"
	@echo "make lint          - Executar ruff (linter + formatter)"
	@echo "make typecheck     - Executar mypy (type hints)"
	@echo "make test          - Executar testes com cobertura"
	@echo "make clean         - Limpar artefatos temporários"
	@echo "make db-up         - Subir PostGIS via Docker"
	@echo "make db-down       - Parar PostGIS"
	@echo "make db-reset      - Resetar banco de dados"
	@echo "make pipeline      - Executar pipeline ETL"
	@echo "make dashboard     - Iniciar dashboard Streamlit"
	@echo "make run-all       - Subir toda a stack"
	@echo "make pre-commit    - Executar hooks do pre-commit"

install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

typecheck:
	mypy src/

test:
	pytest

clean:
	rm -rf .pytest_cache .coverage htmlcov
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf *.egg-info dist build

db-up:
	docker-compose up -d postgis

db-down:
	docker-compose down

db-reset:
	docker-compose down -v
	docker-compose up -d postgis

pipeline:
	python -m src.pipeline_etl

dashboard:
	streamlit run src/dashboard/app.py

run-all:
	docker-compose up -d --build

pre-commit:
	pre-commit run --all-files
