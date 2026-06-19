# Architecture

## Overview

SafeStreet follows a modular layered architecture:

```
┌──────────────────────────────────────────────┐
│              Presentation Layer              │
│         Streamlit Dashboard (app.py)         │
├──────────────────────────────────────────────┤
│              Analytics Layer                 │
│   Spatial Stats (PySAL), Vulnerability Score │
├──────────────────────────────────────────────┤
│            Spatial Processing Layer          │
│   H3 Indexing, PostGIS Ops, Spatial Joins   │
├──────────────────────────────────────────────┤
│              Data Layer                      │
│   Ingestion, OSM Extraction, Preprocessing   │
├──────────────────────────────────────────────┤
│           Storage Layer (PostGIS)            │
│    spatial models, GiST indexes, queries     │
└──────────────────────────────────────────────┘
```

## Modules

- `src/data/` - Data ingestion and preprocessing
- `src/db/` - Database connection, models, and queries
- `src/spatial/` - H3 indexing and PostGIS spatial operations
- `src/dashboard/` - Streamlit dashboard with map visualization
- `src/utils/` - Logging and validation utilities

## Data Flow

1. Raw crime CSVs are ingested and filtered (nighttime, valid natures)
2. OSM infrastructure data is fetched via Overpass API
3. Both datasets are indexed with Uber H3 (resolution 9)
4. Data is loaded into PostGIS with spatial indexes
5. Lighting density and vulnerability scores are calculated
6. PySAL computes Moran's I and LISA clusters
7. Results are visualized in Streamlit dashboard
