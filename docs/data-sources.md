# Fontes de Dados e API

## Dados de Acidentes de Transito (CTTU Recife)

### Fonte

- **Portal:** dados.recife.pe.gov.br
- **Dataset:** acidentes-de-transito-com-e-sem-vitimas
- **Responsavel:** CTTU (Companhia de Transito e Transporte Urbano do Recife)
- **Licenca:** ODbL (Open Database License)
- **Atualizacao:** Trimestral
- **Granularidade:** Por ano (2015-2024)

### Endpoints

```
Base URL: https://dados.recife.pe.gov.br

CKAN API:
  GET /api/3/action/package_show?id=acidentes-de-transito-com-e-sem-vitimas
  GET /api/3/action/datastore_search?resource_id={resource_id}&limit={n}

Download Direto:
  GET /dataset/{dataset_id}/resource/{resource_id}/download/acidentes-de-transito-{year}.csv
```

### Resource IDs por Ano

| Ano | Resource ID | Tamanho |
|-----|-------------|---------|
| 2024 | `87ac4237-f5f9-44d2-bcf1-927aaa0a2d31` | ~1.5 MB |
| 2023 | `dbb9165a-7539-4fdd-943a-acffe12df3e0` | ~1.1 MB |
| 2022 | `c2281788-2e8c-472c-8812-67c4f85e9272` | ~993 KB |
| 2021 | `31ee35d9-6f8e-4694-9492-efe96e902b07` | ~804 KB |
| 2020 | `b2594588-2aa8-42c4-b96d-246102ecde3c` | ~1.5 MB |
| 2019 | `c9fe4a98-0f61-4e81-9c4b-a22f8dc6f1a2` | ~4.9 MB |
| 2018 | `a7b72334-9229-4e52-a6cb-8006de4942e3` | ~4.0 MB |
| 2017 | `d364e034-7e00-41a7-b557-0b16c21814e7` | ~3.1 MB |
| 2016 | `edc820d6-0f01-4fd2-b8a4-5a8c95f7e743` | ~3.2 MB |
| 2015 | `58816e1f-18bc-4335-82bf-80ff080cb0e5` | ~1.5 MB |

### Schema dos Dados

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `Protocolo` | Text | Numero do protocolo de atendimento |
| `data` | Timestamp | Data do acidente |
| `hora` | Text | Hora do acidente (HH:MM:SS) |
| `natureza` | Text | "COM VITIMA" ou "SEM VITIMA" |
| `situacao` | Text | Status do atendimento |
| `bairro` | Text | Bairro do acidente |
| `endereco` | Text | Endereco do acidente |
| `tipo` | Text | Tipo de acidente (COLISAO, ATROPELAMENTO, etc.) |
| `auto` | Text | Qtd. automoveis envolvidos |
| `moto` | Text | Qtd. motos envolvidas |
| `pedestre` | Text | Qtd. pedestres envolvidos |
| `vitimas` | Text | Qtd. victimas (nao fatais) |
| `vitimasfatais` | Text | Qtd. victimas fatais |

### Observacoes

- Os dados de 2015 estao disponiveis a partir de junho
- A partir de 2019, a coluna `vitimasfatais` foi adicionada
- A partir de 2017, `vitimas` contem apenas victimas nao fatais
- Os numeros usam virgula como separador decimal (ex: "1,0")

## Infraestrutura de Iluminacao (OpenStreetMap)

### Fonte

- **API:** Overpass API
- **Endpoint:** https://overpass-api.de/api/interpreter
- **Tags:** `highway=street_lamp`

### Query Overpass

```
[out:json];
area["name"="Recife"]["admin_level"="8"]->.searchArea;
(
  node["highway"="street_lamp"](area.searchArea);
);
out body;
```

### Resposta

```json
{
  "elements": [
    {
      "type": "node",
      "id": 123456,
      "lat": -8.0476,
      "lon": -34.8770,
      "tags": {
        "highway": "street_lamp"
      }
    }
  ]
}
```

## Geocodificacao por Bairro (OSMnx)

### Metodo

1. `ox.geometries_from_place("Recife, Brazil", tags={"admin_level": "10"})`
2. Extração do atributo `name` (nome do bairro)
3. Calculo do centroid via `geometry.centroid`
4. Cache em `data/external/bairros_recife_centroides.json`

### Formato do Cache

```json
{
  "BOA VIAGEM": [-8.0512, -34.8832],
  "ARRUDA": [-8.0623, -34.8901],
  "CASA AMARELA": [-8.0312, -34.9201]
}
```

## Como Baixar os Dados

### Usando o Script

```bash
# Baixar apenas 2024 (padrao)
python scripts/download_data.py

# Baixar multiplos anos
python scripts/download_data.py 2023 2024

# Usando Makefile
make download
make download YEARS="2023 2024"
```

### Usando curl

```bash
# Download direto
curl -o data/raw/acidentes_transito_recife_2024.csv \
  "https://dados.recife.pe.gov.br/dataset/fdd001d5-05ba-46cd-9edf-5c5a6b58351f/resource/87ac4237-f5f9-44d2-bcf1-927aaa0a2d31/download/acidentes-de-transito-2024.csv"

# Via CKAN API
curl "https://dados.recife.pe.gov.br/api/3/action/datastore_search?resource_id=87ac4237-f5f9-44d2-bcf1-927aaa0a2d31&limit=5"
```

## Outras Fontes Consultadas

| Fonte | Disponibilidade | Observacao |
|-------|-----------------|------------|
| SDS-PE (Secretaria de Defesa Social) | Apenas PDFs/PowerBI | Sem dados pontuais |
| SINESP/MJSP (nacional) | CSV por municipio | Sem lat/lon |
| dados.pe.gov.br (estado) | Nenhum dataset de seguranca | Apenas dados administrativos |
