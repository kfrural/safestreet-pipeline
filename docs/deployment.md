# Guia de Deploy

## Pre-requisitos

| Requisito | Versao Minima | Verificacao |
|-----------|---------------|-------------|
| Python | 3.9+ | `python --version` |
| Docker | 24.0+ | `docker --version` |
| Docker Compose | 2.0+ | `docker-compose --version` |
| Git | 2.0+ | `git --version` |
| Espaco em disco | 2 GB | `df -h` |

## Deploy Local

### 1. Clone e Setup

```bash
# Clonar repositorio
git clone https://github.com/kfrural/safestreet-pipeline.git
cd safestreet-pipeline

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variaveis de ambiente
cp .env.example .env
```

### 2. Banco de Dados

```bash
# Subir PostGIS
make db-up

# Verificar se esta saudavel
docker-compose ps

# Verificar logs
docker-compose logs -f postgis
```

### 3. Dados

```bash
# Baixar dados reais da CTTU
make download

# Ou baixar multiplos anos
make download YEARS="2023 2024"

# Verificar arquivo
ls -lh data/raw/
```

### 4. Pipeline

```bash
# Executar pipeline completo
make pipeline

# Ou com debug
python -m src.pipeline_etl --debug

# Com arquivo especifico
python -m src.pipeline_etl --input data/raw/acidentes_transito_recife_2024.csv
```

### 5. Dashboard

```bash
# Iniciar dashboard
make dashboard

# Ou diretamente
streamlit run src/dashboard/app.py
```

Acesse: http://localhost:8501

## Deploy com Docker (Completo)

```bash
# Subir toda a stack
make run-all

# Ou manualmente
docker-compose up -d --build
``

### Servicos

| Servico | Porta | Descricao |
|---------|-------|-----------|
| postgis | 5432 | Banco de dados PostgreSQL + PostGIS |
| pipeline | - | Executa o ETL uma vez |
| dashboard | 8501 | Aplicacao Streamlit |

### Logs

```bash
# Todos os servicos
docker-compose logs -f

# Apenas PostGIS
docker-compose logs -f postgis

# Apenas pipeline
docker-compose logs -f pipeline
```

### Parar

```bash
docker-compose down

# Com volumes (remove dados)
docker-compose down -v
```

## Variaveis de Ambiente

| Variavel | Padrao | Descricao |
|----------|--------|-----------|
| `POSTGRES_HOST` | localhost | Host do PostgreSQL |
| `POSTGRES_PORT` | 5432 | Porta do PostgreSQL |
| `POSTGRES_DB` | safestreet | Nome do banco |
| `POSTGRES_USER` | safestreet | Usuario |
| `POSTGRES_PASSWORD` | safestreet_pass | Senha |
| `OSM_CITY_NAME` | Recife, Brazil | Cidade para extracao OSM |
| `PIPELINE_CRIME_FILE` | data/raw/acidentes_transito_recife_2024.csv | Arquivo de entrada |
| `PIPELINE_OUTPUT_DIR` | data/processed | Diretorio de saida |
| `H3_RESOLUTION` | 9 | Resolucao H3 (0-15) |

## Comandos Uteis

```bash
# Verificar status do banco
docker-compose exec postgis psql -U safestreet -d safestreet -c "\dt safestreet.*"

# Contar registros
docker-compose exec postgis psql -U safestreet -d safestreet -c "SELECT COUNT(*) FROM safestreet.crime_records"

# Ver celulas H3
docker-compose exec postgis psql -U safestreet -d safestreet -c "SELECT h3_index, crime_count, vulnerability_score FROM safestreet.h3_cells ORDER BY vulnerability_score DESC LIMIT 10"

# Limpar cache de geocodificacao
rm data/external/bairros_recife_centroides.json

# Re-executar pipeline
make pipeline

# Verificar testes
make test

# Verificar estilo
make lint
```

## Troubleshooting

### Erro de conexao com PostgreSQL

```bash
# Verificar se o PostGIS esta rodando
docker-compose ps

# Reiniciar
docker-compose restart postgis

# Verificar logs
docker-compose logs postgis
```

### Erro de geocodificacao

```bash
# Limpar cache
rm data/external/bairros_recife_centroides.json

# Re-executar (vai reconectar ao OSM)
python scripts/download_data.py
```

### Erro de dependencias

```bash
# Reinstalar
pip install -r requirements.txt --force-reinstall

# Verificar versao do Python
python --version
```

### Pipeline lento

- A extracao OSM pode demorar dependendo da conexao
- O download de dados CTTU depende da API externa
- O calculo de Moran's I e O(n) com permutacoes

## Producao

Para ambientes de producao, recomenda-se:

1. **Banco dedicado**: Usar RDS, Cloud SQL, ou similar
2. **Cache Redis**: Para geocodificacao e queries frequentes
3. **Scheduler**: Airflow ou Cron para re-execucao periodica
4. **Monitoramento**: Prometheus + Grafana para metricas
5. **Backup**: Backup automatico do PostgreSQL
