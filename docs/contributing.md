# Contribuindo para o SafeStreet

## Como Contribuir

1. Fork o repositorio
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Faca seus cambios
4. Execute os testes (`make test`)
5. Verifique o estilo (`make lint`)
6. Faca commit (`git commit -m "feat: adicionar nova feature"`)
7. Push para sua branch (`git push origin feature/nova-feature`)
8. Abra um Pull Request

## Convencoes de Commit

Usamos [Conventional Commits](https://www.conventionalcommits.org/):

| Tipo | Descricao | Exemplo |
|------|-----------|---------|
| `feat` | Nova feature | `feat: adicionar filtro por dia da semana` |
| `fix` | Correcao de bug | `fix: corrigir geocodificacao de bairros` |
| `docs` | Documentacao | `docs: atualizar guia de deploy` |
| `style` | Formatacao | `style: aplicar ruff format` |
| `refactor` | Refatoracao | `refactor: extrair funcao de normalizacao` |
| `test` | Testes | `test: adicionar teste para vulnerability_score` |
| `chore` | Manutencao | `chore: atualizar dependencias` |

## Estrutura de Pastas

```
safestreet-pipeline/
├── src/                    # Codigo fonte
│   ├── data/              # Ingestao e preprocessamento
│   ├── db/                # Camada de banco
│   ├── spatial/           # Processamento espacial
│   ├── dashboard/         # Interface
│   └── utils/             # Utilitarios
├── tests/                  # Testes
├── scripts/                # Scripts auxiliares
├── docs/                   # Documentacao
└── data/                   # Dados (gitignore)
```

## Regras de Codigo

### Formatacao

```bash
# Verificar estilo
make lint

# Corrigir automaticamente
ruff check src/ tests/ --fix
ruff format src/ tests/
```

### Type Hints

```bash
# Verificar tipos
make typecheck
```

### Testes

```bash
# Executar todos
make test

# Com cobertura
pytest --cov=src --cov-report=html

# Teste especifico
pytest tests/test_analytics.py -v
```

## Adicionando Nova Feature

### 1. Criar modulo

```python
# src/data/nova_feature.py
from __future__ import annotations

from loguru import logger


def nova_funcao(param: str) -> str:
    """Descricao curta."""
    logger.info("Executando nova_funcao com {}", param)
    return param
```

### 2. Adicionar teste

```python
# tests/test_nova_feature.py
from src.data.nova_feature import nova_funcao


def test_nova_funcao() -> None:
    result = nova_funcao("teste")
    assert result == "teste"
```

### 3. Atualizar pipeline

```python
# No pipeline_etl.py ou modulo relevante
from src.data.nova_feature import nova_funcao
```

## Adicionando Nova Fonte de Dados

1. Criar modulo em `src/data/` com funcoes de extracao
2. Adicionar schema no `src/db/models.py`
3. Criar funcoes de insert em `src/db/queries.py`
4. Integrar no `src/pipeline_etl.py`
5. Documentar em `docs/data-sources.md`
6. Adicionar testes

## Issues e PRs

- Use Issues para reportar bugs ou sugerir features
- PRs devem incluir testes e documentacao
- PRs sem testes serao rejeitados
- Cada PR deve resolver uma Issue (ou ser descrito claramente)

## Perguntas?

Abra uma Issue com a tag `question`.
