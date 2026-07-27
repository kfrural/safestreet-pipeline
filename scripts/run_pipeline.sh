#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
export $(grep -v '^\s*#' "$PROJECT_DIR/.env" | xargs)

echo "=== SafeStreet Pipeline ==="
echo "Iniciando execução do pipeline ETL..."

cd "$PROJECT_DIR"

python -m src.pipeline_etl "$@"

echo "Pipeline concluído com sucesso!"
