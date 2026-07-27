# SafeStreet: Spatial Intelligence Pipeline & Urban Nighttime Vulnerability Analysis

[![CI](https://github.com/kfrural/safestreet-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/kfrural/safestreet-pipeline/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PostGIS](https://img.shields.io/badge/PostgreSQL-PostGIS-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgis.net/)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**SafeStreet** is an end-to-end spatial intelligence platform that fuses Geographic Data Engineering, Spatial Databases and Data Science to answer a critical safety question: **Does urban infrastructure act as an inhibitor or facilitator of nighttime crime?** By merging SSP-SP crime records (2013-2022) with OpenStreetMap infrastructure and official street lighting data from the City of Sao Paulo, the ecosystem isolates nighttime criminality and statistically validates the correlation between infrastructure gaps and high-risk zones.

---

## Data Sources

| Source | Type | Granularity | License |
|--------|------|-------------|---------|
| **SSP-SP** via labcidade/boletins-ssp + SPSafe (Zenodo) | Nighttime crime records | Point (neighborhood + coordinates) | Public |
| **GeoSampa / SP Regula** (WFS) | Official public lighting | ~97k points | Public |
| **OpenStreetMap** (Overpass API) | Bus stops, metro, cameras, nightlife, transit schedules, cultural venues | Point | ODbL |
| **IBGE SIDRA API** | Socioeconomic indicators (Census 2022), income per capita | Municipal | Public |
| **Open-Meteo Archive API** | Historical weather data | Daily | Free |
| **RSS News Feeds** | Security sentiment analysis (Folha, G1) | Headlines | Public |

---

## Analysis Pipeline

### Data Ingestion (Fases 1 & 6)
1. **Ingest** SSP-SP crime records (2013-2019 labcity, 2020-2022 SPSafe/Zenodo)
2. **Classify** crimes by severity (Violencia, Roubo/Furto, Trafico/Armas, Outros)
3. **Extract** urban infrastructure: lighting, bus stops, metro, cameras, nightlife (OSM)
4. **Integrate** official GeoSampa lighting (~97k points via WFS)
5. **Fetch** socioeconomic indicators IBGE (Census 2022)
6. **Fetch** income per capita data (IBGE SIDRA table 10295)
7. **Fetch** historical weather data (Open-Meteo API)
8. **Analyze** nighttime transit via OSM opening_hours parsing
9. **Catalog** cultural venues as proximity/cluster proxy (OSM)
10. **Analyze** news sentiment via RSS + keyword-based NLP

### Analytics (Fases 2 & 5)
11. **Index** occurrences into hexagonal cells (Uber H3 Resolution 9)
12. **Calculate** vulnerability scores via PCA
13. **Validate** spatial dependence via Global and Local Moran's I (LISA)
14. **Train** predictive models (Random Forest + Gradient Boosting)
15. **Cluster** crime patterns (K-Means + DBSCAN)
16. **Calculate** sinistrality index (crimes/100k inhabitants)
17. **Generate** natural language insights from data patterns
18. **Compute** data confidence scores per hexagonal cell

### Visualization (Fases 3, 5 & 7)
19. **Interactive dashboard** with 8 tabs (Mapa, Temporal, Heatmap, Estatistica, Analise, Dados, Avancado, Sobre)
20. **3D map** with PyDeck HexagonLayer + crime ScatterplotLayer
21. **Animated heatmap** with play/pause and month slider
22. **Sankey diagram** neighborhood > crime category > risk level
23. **Network graph** of neighborhood similarity based on infrastructure
24. **Treemap** hierarchy: neighborhood > category > crime nature
25. **National comparison** radar chart (Sao Paulo vs Brazil averages)
26. **Onboarding wizard** for first-time users
27. **Dark/light theme** toggle for presentations
28. **PDF report** generation via fpdf2

---

## Quick Start

### Prerequisites

* Docker and Docker Compose installed
* Python 3.11 or higher

### Docker (Recommended)

```bash
git clone https://github.com/kfrural/safestreet-pipeline.git
cd safestreet-pipeline
cp .env.example .env    # Edit with your credentials
make run-all

# Dashboard: http://localhost:8501
# API docs:  http://localhost:8000/docs
```

### Local Setup

```bash
# Install dependencies
make dev-install

# Start PostGIS
make db-up

# Download and process SSP-SP data
make download-sp
make pipeline-sp

# Start dashboard and/or API
make dashboard
make api
```

### Available Commands

| Command | Description |
|---------|-------------|
| `make download-sp` | Download SSP-SP data (default year: 2024) |
| `make pipeline-sp` | Run full ETL pipeline |
| `make pipeline-incremental` | Incremental pipeline (skip existing data) |
| `make dashboard` | Start Streamlit dashboard (port 8501) |
| `make api` | Start FastAPI server (port 8000) |
| `make run-all` | Start full stack via Docker |
| `make test` | Run tests with coverage |
| `make lint` | Run linter (ruff) |

---

## Dashboard Tabs

| Tab | Content |
|-----|---------|
| **Mapa** | Vulnerability map with H3 cells, lighting, transit, cameras, crimes. Toggle 2D (Folium) / 3D (PyDeck) |
| **Temporal** | Monthly trend, year-over-year comparison, seasonality, weekly cycle |
| **Heatmap** | Hour x weekday with Plotly Heatmap + animated monthly evolution |
| **Estatistica** | Pearson, Spearman, OLS regression, RF importance, VIF, ACF, predictive model, clustering, sinistrality |
| **Analise** | Crime categories, top crime types, infrastructure distance, weather data, transit analysis, sentiment |
| **Dados** | H3 cell data table, vulnerability gaps, **data confidence scores** |
| **Avancado** | Sankey diagram, network graph, treemap |
| **Sobre** | Methodology, IBGE indicators, **national comparison radar**, **rental/income data**, **nighttime transit stats**, **news sentiment**, **auto-generated insights**, PDF report export |

---

## API REST (FastAPI)

Endpoints at `http://localhost:8000/docs`:

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /cities` | Cities with data |
| `GET /cities/{city}/stats` | General statistics |
| `GET /cities/{city}/h3-cells` | H3 cells with vulnerability |
| `GET /cities/{city}/crimes` | Crime locations |
| `GET /cities/{city}/categories` | Crime categories |
| `GET /cities/{city}/temporal` | Temporal trend |
| `GET /cities/{city}/correlations` | Correlation data |
| `GET /cities/{city}/gaps` | Vulnerability gaps |
| `GET /cities/{city}/years` | Available years |

---

## Project Structure

```
safestreet-pipeline/
├── src/
│   ├── config.py               # Centralized settings (Pydantic)
│   ├── pipeline_etl.py         # ETL orchestrator with incremental mode
│   ├── analytics/
│   │   ├── spatial.py          # Moran's I, LISA, spatial weights
│   │   ├── statistics.py       # PCA, correlation, OLS, RF, clustering, sinistrality
│   │   └── insights.py         # Confidence scores, natural language insights
│   ├── data/
│   │   ├── ssp_sp.py           # SPSafe download (Zenodo)
│   │   ├── lighting.py         # GeoSampa lighting via WFS
│   │   ├── ibge.py             # IBGE SIDRA API (municipal + national)
│   │   ├── osm_infra.py        # OSM infrastructure (with Overpass retry)
│   │   ├── weather.py          # Open-Meteo API
│   │   ├── nightlife.py        # OSM nightlife POIs
│   │   ├── rental.py           # IBGE income per capita (table 10295)
│   │   ├── transport_night.py  # Nighttime transit analysis (opening_hours)
│   │   ├── events.py           # Cultural venues from OSM
│   │   └── sentiment.py        # RSS news sentiment analysis (NLP)
│   ├── db/
│   │   ├── connection.py       # SQLAlchemy engine
│   │   ├── models.py           # ORM: CrimeRecord, InfrastructurePoint, H3Cell
│   │   ├── queries.py          # SQL queries
│   │   └── cached_queries.py   # Streamlit @st.cache_data wrappers
│   ├── spatial/
│   │   ├── h3_indexer.py       # Uber H3 indexing
│   │   └── postgis_ops.py      # PostGIS ops, vulnerability, Moran
│   ├── api/
│   │   └── app.py              # FastAPI REST API
│   ├── dashboard/
│   │   ├── app.py              # Streamlit dashboard (8 tabs)
│   │   └── components/
│   │       └── map_viz.py      # Folium map
│   └── utils/
│       ├── classifiers.py      # Crime classification
│       ├── logger.py           # Loguru setup
│       └── validators.py       # Validators
├── scripts/
│   ├── download_ssp_sp.py      # SSP-SP data download
│   ├── init_db.sql             # PostGIS initialization
│   └── run_pipeline.sh         # Pipeline runner
├── tests/
├── docker-compose.yml          # 5 services: postgis, pipeline, dashboard, api, scheduler
├── Dockerfile
├── Makefile
├── .github/workflows/ci.yml   # CI/CD: lint + test
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Language** | Python 3.11 |
| **Database** | PostgreSQL 16 + PostGIS 3.4 |
| **Spatial Indexing** | Uber H3 (Res. 9) |
| **Spatial Analysis** | PySAL (esda, libpysal) |
| **ML** | scikit-learn (RF, Gradient Boosting, K-Means, DBSCAN) |
| **Crime Data** | SPSafe (Zenodo) + labcidade/boletins-ssp |
| **Lighting** | GeoSampa WFS (~97k official points) |
| **Infrastructure** | OSMnx + Overpass API |
| **Socioeconomic** | IBGE SIDRA API (Census 2022) |
| **Weather** | Open-Meteo Archive API |
| **Sentiment** | RSS feeds + keyword-based NLP |
| **Dashboard** | Streamlit + Plotly + Folium + PyDeck |
| **API** | FastAPI + uvicorn |
| **Containerization** | Docker Compose (5 services) |
| **CI/CD** | GitHub Actions |
| **Quality** | ruff (E,F) + pytest |
| **PDF Reports** | fpdf2 |

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Open data sources are used under their respective public licenses (OpenStreetMap ODbL, IBGE public data, SSP-SP public data, Open-Meteo free tier).
