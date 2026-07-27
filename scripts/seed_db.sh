#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

export $(grep -v '^\s*#' "$PROJECT_DIR/.env" | xargs)

echo "=== SafeStreet - Inicialização do Banco ==="

echo "Criando banco de dados e extensões PostGIS..."
docker-compose -f "$PROJECT_DIR/docker-compose.yml" up -d postgis

echo "Aguardando PostGIS ficar saudável..."
until docker exec safestreet-db pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" > /dev/null 2>&1; do
    sleep 2
done

echo "Executando script de inicialização..."
docker exec -i safestreet-db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" < "$SCRIPT_DIR/init_db.sql"

echo "Banco de dados inicializado com sucesso!"
