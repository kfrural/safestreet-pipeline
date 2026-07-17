.PHONY: help install dev-install lint typecheck test clean db-up db-down db-reset pipeline pipeline-sp pipeline-all dashboard run-all pre-commit download download-sp

help:
	@echo "SafeStreet Pipeline - Comandos Disponiveis"
	@echo "----------------------------------------"
	@echo "make install       - Instalar dependencias de producao"
	@echo "make dev-install   - Instalar dependencias de desenvolvimento"
	@echo "make lint          - Executar ruff (linter + formatter)"
	@echo "make typecheck     - Executar mypy (type hints)"
	@echo "make test          - Executar testes com cobertura"
	@echo "make clean         - Limpar artefatos temporarios"
	@echo "make download      - Baixar dados CTTU Recife (ano padrao: 2024)"
	@echo "make download-sp   - Baixar dados SSP-SP (ano padrao: 2024)"
	@echo "make db-up         - Subir PostGIS via Docker"
	@echo "make db-down       - Parar PostGIS"
	@echo "make db-reset      - Resetar banco de dados"
	@echo "make pipeline      - Executar pipeline Recife"
	@echo "make pipeline-sp   - Executar pipeline Sao Paulo"
	@echo "make pipeline-all  - Executar pipeline todas cidades"
	@echo "make dashboard     - Iniciar dashboard Streamlit"
	@echo "make run-all       - Subir toda a stack"
	@echo "make pre-commit    - Executar hooks do pre-commit"

install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install

download:
	python scripts/download_data.py $(or $(YEARS),2024)

download-sp:
	python scripts/download_ssp_sp.py $(or $(YEARS),2024)

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
	docker compose up -d postgis

db-down:
	docker compose down

db-reset:
	docker compose down -v
	docker compose up -d postgis

pipeline:
	PYTHONPATH=$(pwd) python -m src.pipeline_etl --city recife

pipeline-sp:
	PYTHONPATH=$(pwd) python -m src.pipeline_etl --city sao-paulo

pipeline-all:
	PYTHONPATH=$(pwd) python -m src.pipeline_etl --all

dashboard:
	streamlit run src/dashboard/app.py

run-all:
	docker compose up -d --build

pre-commit:
	pre-commit run --all-files
