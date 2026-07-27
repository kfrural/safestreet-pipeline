# Arquitetura do Sistema

## Visao Geral

SafeStreet segue uma arquitetura modular em camadas, com separacao clara de responsabilidades:

```
┌─────────────────────────────────────────────────────────────┐
│                    Camada de Apresentacao                    │
│              Streamlit Dashboard (src/dashboard/)            │
│         Mapa Folium, Metricas, Tabelas, Metodologia         │
├─────────────────────────────────────────────────────────────┤
│                    Camada de Analise                         │
│    Moran's I Global, LISA, Classificacao de Clusters        │
│              Vulnerability Score (src/analytics.py)          │
├─────────────────────────────────────────────────────────────┤
│                  Camada de Processamento Espacial            │
│     Indexacao H3, Operacoes PostGIS, Spatial Joins          │
│              (src/spatial/)                                  │
├─────────────────────────────────────────────────────────────┤
│                    Camada de Dados                           │
│    Ingestao, Extracao OSM, Preprocessamento, Geocodificacao │
│              (src/data/)                                     │
├─────────────────────────────────────────────────────────────┤
│                  Camada de Armazenamento (PostGIS)           │
│         Modelos ORM, Indices GiST, Queries Espaciais        │
│              (src/db/)                                       │
└─────────────────────────────────────────────────────────────┘
```

## Modulos

### `src/data/` - Ingestao e Preprocessamento

| Modulo | Responsabilidade |
|--------|------------------|
| `ingestion.py` | Carregamento de CSV/Excel com deteccao automatica de formato |
| `preprocessing.py` | Filtros temporais (18h-06h), de vitimas, de natureza |
| `osm_extractor.py` | Wrappers para OSMnx: iluminacao, transporte publico, malha viaria |
| `geocoder.py` | Geocodificacao por bairro via centroides OSMnx |

### `src/db/` - Camada de Persistencia

| Modulo | Responsabilidade |
|--------|------------------|
| `connection.py` | Engine SQLAlchemy, pool de conexoes, health check |
| `models.py` | ORM: CrimeRecord, InfrastructurePoint, H3Cell (GeoAlchemy2) |
| `queries.py` | Batch inserts, queries de densidade, retrieval de celulas H3 |

### `src/spatial/` - Processamento Espacial

| Modulo | Responsabilidade |
|--------|------------------|
| `h3_indexer.py` | Conversao lat/lon para H3, criacao de grid hexagonal |
| `postgis_ops.py` | Indices GiST, lighting_density, nearest_light, vulnerability_score, Moran clusters |
| `spatial_joins.py` | Join espacial por buffer, contagem por H3 |

### `src/analytics.py` - Analise Estatistica Espacial

| Funcao | Descricao |
|--------|-----------|
| `compute_moran_global()` | Moran's I Global com permutacoes |
| `compute_moran_local()` | LISA (Local Indicators of Spatial Association) |
| `classify_lisa_clusters()` | Classificacao HH/LH/LL/HL/NS por significancia |
| `build_spatial_weights()` | Pesos espaciais baseados em vizinhanca H3 k-ring |

### `src/dashboard/` - Camada de Apresentacao

| Modulo | Responsabilidade |
|--------|------------------|
| `app.py` | Aplicacao Streamlit: sidebar, metricas, tabs |
| `components/map_viz.py` | Mapa Folium com hexagonos H3 coloridos por vulnerabilidade |

### `src/utils/` - Utilitarios

| Modulo | Responsabilidade |
|--------|------------------|
| `logger.py` | Configuracao Loguru (console + arquivo rotativo) |
| `validators.py` | Filtros de horario, natureza, validacao de GeoDataFrame |

## Fluxo de Dados

```
CSV CTTU (dados brutos)
    │
    ▼
[Download] scripts/download_data.py → data/raw/
    │
    ▼
[Geocodificacao] src/data/geocoder.py
    │  - OSMnx geometries_from_place("Recife", admin_level=10)
    │  - Calculo de centroides por bairro
    │  - Cache em data/external/bairros_recife_centroides.json
    │
    ▼
[Preprocessamento] src/data/preprocessing.py
    │  - Filtro noturno (18h-06h)
    │  - Filtro de vitimas (vitimas > 0)
    │  - Atribuicao de coordenadas
    │
    ▼
[Indexacao H3] src/spatial/h3_indexer.py
    │  - geo_to_h3(lat, lon, resolution=9)
    │  - add_h3_column(gdf)
    │
    ▼
[Ingestao PostGIS] src/db/queries.py
    │  - insert_crime_records_batch()
    │  - insert_infrastructure_batch()
    │
    ▼
[Extracao OSM] src/data/osm_extractor.py
    │  - fetch_lighting_infrastructure("Recife, Brazil")
    │  - Tags: highway=street_lamp
    │
    ▼
[Processamento Espacial] src/spatial/postgis_ops.py
    │  - create_spatial_indexes() (GiST)
    │  - calculate_lighting_density()
    │  - calculate_nearest_light_distance()
    │  - calculate_vulnerability_score()
    │  - calculate_moran_clusters()
    │
    ▼
[Dashboard] src/dashboard/app.py
       - Metricas: acidentes, celulas, alto risco, clusters HH
       - Mapa: hexagonos H3 coloridos
       - Tabela: dados filtraveis
       - Metodologia: explicacao cientifica
```

## Schema do Banco de Dados

### Tabela `crime_records`

| Coluna | Tipo | Constraints |
|--------|------|-------------|
| `id` | Integer | PK, autoincrement |
| `occurrence_id` | String(50) | UNIQUE |
| `nature` | String(100) | NOT NULL |
| `date` | DateTime | NOT NULL |
| `time` | String(5) | NOT NULL |
| `geometry` | Geometry(POINT, 4326) | NOT NULL |
| `h3_index` | String(20) | nullable |

### Tabela `infrastructure_points`

| Coluna | Tipo | Constraints |
|--------|------|-------------|
| `id` | Integer | PK, autoincrement |
| `osm_id` | String(20) | UNIQUE |
| `infra_type` | String(50) | NOT NULL |
| `geometry` | Geometry(POINT, 4326) | NOT NULL |
| `h3_index` | String(20) | nullable |

### Tabela `h3_cells`

| Coluna | Tipo | Constraints |
|--------|------|-------------|
| `id` | Integer | PK, autoincrement |
| `h3_index` | String(20) | UNIQUE, NOT NULL |
| `resolution` | Integer | NOT NULL |
| `crime_count` | Integer | default 0 |
| `lighting_density` | Float | default 0.0 |
| `dist_nearest_lit` | Float | nullable |
| `vulnerability_score` | Float | nullable |
| `moran_cluster` | String(10) | nullable |

## Decisoes de Design

1. **H3 Resolution 9**: Tamanho aproximado de quarteirao urbano (~107m de aresta), ideal para analise de seguranca publica
2. **Geocodificacao por bairro**: Alternativa viavel a geocodificacao por endereco (rate-limit do Nominatim)
3. **Vulnerability Score**: Formula composta que considera densidade de acidentes, falta de iluminacao e distancia ate luz mais proxima
4. **Moran's I + LISA**: Validacao estatistica da dependencia espacial, identificando clusters de alto risco
5. **PostGIS + GeoAlchemy2**: Suporte natimo a operacoes espaciais com ORM Python
