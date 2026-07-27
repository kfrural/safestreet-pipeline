# Metodologia Cientifica

## Pergunta de Pesquisa

**A infraestrutura urbana de iluminacao publica atua como fator inibidor ou facilitador da sinistralidade noturna em Recife?**

## Hipotese

Areas com menor densidade de iluminacao publica apresentam maiores concentracoes de acidentes de transito noturnos com victimas, configurando clusters espaciais estatisticamente significativos.

## Dados Utilizados

1. **Acidentes de transito noturnos** (CTTU Recife, 2024): acidentes com victimas entre 18h e 06h
2. **Infraestrutura de iluminacao** (OpenStreetMap): pontos de iluminacao publica (`street_lamp`)
3. **Geocodificacao**: centroides dos bairros de Recife via OSMnx

## Metodologia

### 1. Filtragem Temporal

Apenas acidentes ocorridos no periodo noturno (18h00 as 06h00) sao considerados, pois e nesse periodo que a iluminacao publica tem impacto direto na seguranca viaria.

```python
def is_nighttime(occurrence_time: time) -> bool:
    return occurrence_time >= time(18, 0) or occurrence_time < time(6, 0)
```

### 2. Discretizacao Espacial (Uber H3)

Para evitar o **Problema da Unidade de Area Modificavel (MAUP)** associado a divisoes politicas (bairros), utilizamos o sistema de indexacao hexagonal **Uber H3** na **Resolucao 9**.

| Propriedade | Valor |
|-------------|-------|
| Resolucao | 9 |
| Area do hexagono | ~107 m de aresta |
| Area aproximada | ~0.102 km² |
| Equivalencia | Aproximadamente um quarteirao urbano |

**Vantagens do H3:**
- Grade uniforme sem vies de divisao politica
- Indexacao rapida O(1) por lat/lon
- Vizinhanca natural (k-ring) para analise espacial
- Compativel com PostgreSQL via conversao

### 3. Indice de Moran Global

O **Indice de Moran Global** testa se ha dependencia espacial nos dados. A hipotese nula (H0) e de que os valores estao distribuidos aleatoriamente no espaco.

**Formula:**

```
I = (N / S0) * (sum_i sum_j w_ij * (x_i - x_bar) * (x_j - x_bar)) / (sum_i (x_i - x_bar)^2)
```

Onde:
- N = numero de observacoes
- S0 = soma dos pesos espaciais
- w_ij = peso espacial entre i e j
- x_bar = media dos valores

**Interpretacao:**
- I > 0: agrupamento positivo (valores similares proximos)
- I < 0: agrupamento negativo (valores dissimilares proximos)
- I ~ 0: distribuicao aleatoria

**Significancia:** p-value < 0.05 (999 permutacoes)

### 4. Indice de Moran Local (LISA)

O **LISA** identifica clusters locais de associacao espacial, classificando cada celula em quadrantes:

| Cluster | Significado | Interpretacao |
|---------|-------------|---------------|
| **HH** (High-High) | Alto valor cercado de altos | Hotspot critico |
| **LH** (Low-High) | Baixo valor cercado de altos | Ilha de seguranca |
| **LL** (Low-Low) | Baixo valor cercado de baixos | Area segura |
| **HL** (High-Low) | Alto valor cercado de baixos | Ponto isolado de risco |
| **NS** (Not Significant) | Sem padrao espacial | Aleatorio |

**Foco do projeto:** Clusters **HH** (Alto-Alto) indicam areas onde alta sinistralidade coincide com baixa iluminacao.

### 5. Score de Vulnerabilidade

O `vulnerability_score` e calculado como:

```
vulnerability_score = (crime_count / max_crime) * (1 - lighting_density / max_lighting) * (1 / (1 + dist_nearest_lit / 1000))
```

Onde:
- `crime_count`: numero de acidentes na celula H3
- `lighting_density`: razao entre pontos de iluminacao e acidentes
- `dist_nearest_lit`: distancia em metros ate o ponto de iluminacao mais proximo

**Normalizacao:** O score final e limitado entre 0 e 1 using `GREATEST(0, LEAST(1, ...))`.

### 6. Pesos Espaciais

Os pesos espaciais sao construidos usando **vizinhanca H3 k-ring** (k=1), que inclui os 6 vizinhos diretos de cada hexagono. A matriz de pesos e convertida para formato **Queen** do PySAL.

## Pipeline Analitico

```
Dados CTTU (CSV)
    │
    ├── Filtro noturno (18h-06h)
    ├── Filtro de victimas (vitimas > 0)
    ├── Geocodificacao por bairro
    │
    ▼
Indexacao H3 (Res. 9)
    │
    ├── Insercao no PostGIS
    ├── Extracao OSM (iluminacao)
    │
    ▼
Calculo por Celula H3
    │
    ├── crime_count (contagem de acidentes)
    ├── lighting_density (razao iluminacao/acidentes)
    ├── dist_nearest_lit (distancia euclidiana)
    ├── vulnerability_score (formula composta)
    │
    ▼
Analise Espacial
    │
    ├── Construcao de pesos (H3 k-ring)
    ├── Moran's I Global (significancia)
    ├── LISA Local (classificacao HH/LH/LL/HL/NS)
    │
    ▼
Dashboard Streamlit
    ├── Mapa de vulnerabilidade (Folium)
    ├── Metricas resumidas
    ├── Tabela de dados
    └── Documentacao metodologica
```

## Limitacoes

1. **Geocodificacao por bairro**: Coordenadas sao centroides, nao pontos exatos de ocorrencia
2. **Dados de acidentes, nao crimes**: O dataset disponivel e de sinistralidade viaria, nao criminalidade
3. **Viés de relato**: Apenas acidentes atendidos pela CTTU estao registrados
4. **Resolucao temporal**: Hora exata pode variar entre minutos do registro real
5. **Autocorrelacao espacial**: Resultados de Moran sao validos apenas para a amostra analisada

## Referencias

- Anselin, L. (1995). Local indicators of spatial association - LISA. *Geographical Analysis*, 27(2), 93-115.
- Moran, P. A. P. (1950). Notes on continuous stochastic phenomena. *Biometrika*, 37(1/2), 17-23.
- Uber Technologies. (2018). H3: Uber's Hexagonal Hierarchical Spatial Index. https://h3geo.org/
- Rey, S. J., & Anselin, L. (2010). PySAL: A Python Library for Spatial Analysis. *Journal of Statistical Software*, 35(1), 1-29.
