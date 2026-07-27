# SafeStreet - Backlog de Melhorias

> Sugestoes de evolucao do sistema, priorizadas por impacto e viabilidade.
> Foco: Sao Paulo (SSP-SP 2013-2019)

---

## Fase 1 - Dados e Precisao

- [x] **Integrar dados meteorologicos** - cruzar crimes com chuva,
  temperatura via Open-Meteo Archive API com cache CSV
- [x] **Dados de cameras por tipo** - cameras do OpenStreetMap via Overpass
- [x] **Integrar nightlife POIs** - bares, pubs, baladas do OSM como
  proxy de atividade noturna por celula H3
- [x] **Integrar dados de iluminacao real** - download dos ~613k pontos
  oficiais da SP Regula via WFS GeoSampa com cache parquet
- [x] **Historico temporal** - download SPSafe (2020-2022) via Zenodo
  com merge ao dataset labcity (2013-2019); script para 2023+ via
  scraping do portal SSP-SP
- [x] **Dados socioeconomicos IBGE** - indicadores via SIDRA API
  (populacao, area, densidade, alfabetizacao, piramide etaria,
  domicilios, cor/raça) com cache JSON

## Fase 2 - Analise Avancada

- [x] **Score de vulnerabilidade via PCA** - analise de componentes
  principais para gerar score calibrado data-driven
- [x] **Testes de correlacao** - Pearson com p-valores, Spearman
  (nao-parametrica), significancia estatistica
- [x] **Regressao OLS multipla** - crimes ~ infraestrutura com R²,
  R² ajustado, testes t, F-test
- [x] **Analise de sazonalidade** - padrao mensal de criminalidade
  (todos os meses consolidados)
- [x] **Tendencia temporal** - evolucao mes a mes dos crimes
- [x] **Ciclo semanal** - distribuicao por dia da semana
- [x] **Heatmap hora x dia** - visualizacao espaco-temporal completa
- [x] **Modelo preditivo** - treinar ML (Random Forest + Gradient
  Boosting) para prever risco de uma area baseado em features de
  infraestrutura; metricas R², RMSE, MAE, cross-validation 5-fold;
  scatter real vs previsto e feature importance
- [x] **Clusterizacao por padrao** - K-Means com elbow method e
  silhouette score; DBSCAN para detectar clusters de crimes com
  padroes similares; centroids com perfis de media por cluster
- [x] **Indice de Sinistralidade** - calcular indice padronizado por
  populacao (crimes/100k habitantes) via IBGE SIDRA; breakdown por
  categoria de crime com niveis (muito baixo ~ muito alto)

## Fase 3 - Dashboard Interativo

- [x] **Filtro temporal no dashboard** - seletor de ano e mes
  com dados reais do banco
- [x] **Matriz de correlacao interativa** - heatmap Plotly com
  p-valores e significancia estatistica
- [x] **Scatter com trendline OLS** - crime vs iluminacao com
  metricas de regressao
- [x] **Heatmap Plotly** - hora x dia da semana com Go.Heatmap
- [x] **Analise temporal** - aba dedicada com tendencia, sazonalidade,
  ciclo semanal
- [x] **Comparacao com dados de anos anteriores** - overlay de
  tendencias ano a ano (chart interativo com todas as linhas de ano)
- [x] **Dashboard mobile** - layout responsivo com `layout="wide"`,
  colunas que empilham em telas estreitas, `width="stretch"` em todos
  os componentes
- [x] **Exportar relatorio PDF** - gerar relatorio automatico com
  resumo geral, sinistralidade, correlacoes, OLS, modelo preditivo,
  clusterizacao e download via `st.download_button` (fpdf2)
- [x] **Filtros avancados** - filtrar por tipo de crime (seletor)
  e por bairro (seletor) diretamente na sidebar; filtros aplicados
  ao mapa e localizacoes de crime

## Fase 4 - Infraestrutura e Escala

- [x] **Pipeline incremental** - flag `--incremental` para pular
  fetch de crimes/infra ja existentes; re-computacao espacial
  sempre executada; Makefile target `make pipeline-incremental`
- [x] **Cache de queries** - modulo `src/db/cached_queries.py` com
  `@st.cache_data(ttl=300)` para todas as queries read-only;
  invalidacao automatica no botao "Atualizar Dados"
- [x] **Celery/Redis** - substituido por scheduler Docker que roda
  pipeline incremental a cada 6h via loop shell
- [x] **API REST** - FastAPI em `src/api/app.py` com endpoints:
  /health, /cities, /cities/{city}/stats, /cities/{city}/h3-cells,
  /cities/{city}/crimes, /cities/{city}/categories,
  /cities/{city}/temporal, /cities/{city}/correlations,
  /cities/{city}/gaps, /cities/{city}/years; CORS habilitado
- [x] **Docker Compose completo** - 5 servicos: postgis, pipeline,
  dashboard (port 8501), api (port 8000), scheduler (incremental 6h)
- [x] **CI/CD** - GitHub Actions com jobs de lint (ruff E,F + format)
  e test (pytest com PostGIS service container); cache pip

## Fase 5 - Visualizacao Premium

- [x] **Mapa 3D** - toggle 2D/3D no Mapa tab usando PyDeck HexagonLayer;
  elevacao = crime_count * 10, cor = vulnerabilidade, pitch 45 graus
- [x] **Heatmap animado** - evolucao mensal com botoes Play/Pause e
  slider por periodo (ano-mes); Go.Heatmap com animation_frame
- [x] **Grafico de Sankey** - fluxo bairro -> categoria de crime ->
  nivel de risco no tab Avancado; cores por nivel de risco
- [x] **Network graph** - grafo de similaridade entre bairros baseado
  em features de infraestrutura (distancia euclidiana padronizada);
  nos proporcionais ao crime_count, layout spring
- [x] **Treemap** - visao hierarquica bairro > categoria > natureza
  com Plotly px.treemap; top 15 bairros

## Fase 6 - Dados Externos

- [x] **Dados climaticos** - Open-Meteo API com cache e estatisticas
- [x] **Dados de aluguel** - IBGE SIDRA table 9514 (valor do aluguel
  mensal, Censo 2022) e table 4714 (renda per capita); cache JSON;
  metricas no dashboard (aluguel medio, renda per capita)
- [x] **Dados de transporte noturno** - parsing de opening_hours do
  OSM para bus_stop e metro_station; classificacao 24h / abre a noite /
  fecha a noite; stats por infra_type no dashboard
- [x] **Eventos culturais** - venues OSM (cinema, teatro, estadio,
  arena, arts_centre, events_venue, conference_centre, stadium);
  contagem por tipo; integra ao pipeline ETL
- [x] **Noticias e redes sociais** - NLP basico com keyword matching
  (positivo/negativo) em RSS feeds (Folha, EM, UOL); analise de
  sentimento com score [-1, +1]; headlines no dashboard

## Fase 7 - UX e Apresentacao

- [x] **Onboarding interativo** - wizard multi-step com 4 passos
  (welcome, filtros, mapas, metricas); progress bar; botoes
  Proximo/Anterior/Comecar/Pular; armazenado em session_state;
  so aparece na primeira visita
- [x] **Comparacao com media nacional** - radar chart Plotly
  comparando SP vs Brasil (populacao log, densidade log,
  alfabetizacao); dados IBGE SIDRA nacional; metricas lado a lado
- [x] **Score de confianca** - metrica por celula H3 baseada em
  completude: 40% crimes (normalizado a 50), 30% infraestrutura
  (4 tipos), 30% anos de dados; classificacao Alta/Media/Baixa;
  resumo de contagem no dashboard
- [x] **Linguagem natural** - 6 templates com dados reais: celulas
  alto risco, deficit iluminacao, cameras insuficientes, nightlife
  correlacionado, sinistralidade/100k, score vulnerabilidade medio;
  modulo src/analytics/insights.py
- [x] **Modo escuro/claro** - toggle no sidebar (Claro/Escuro);
  CSS customizado para dark mode (background #0e1117, cards #1a1d23);
  persiste em session_state

## Melhorias de Codigo

- [x] **Refatorar analytics para pacote** - separar em spatial.py
  (Moran/LISA) e statistics.py (PCA, correlacao, OLS)
- [x] **Remover Recife** - focar apenas em Sao Paulo para qualidade
  dos dados
- [x] **PCA-calibrated vulnerability score** - substituir formula
  arbitraria por analise de componentes principais
- [x] **Correlacao de Spearman** - correlacao nao-parametrica na aba
  de estatisticas com matriz Plotly
- [x] **Feature Importance (Random Forest)** - ranking de importancia
  das variaveis para prever crimes
- [x] **VIF - Multicolinearidade** - calculo de VIF por variavel com
  cores de alerta (vermelho > 10, amarelo > 5)
- [x] **Autocorrelacao temporal (ACF)** - funcao de autocorrelacao nos
  dados mensais para detectar sazonalidade
- [x] **Teste de Durbin-Watson** - diagnostico de autocorrelacao nos
  residuos da regressao OLS
- [x] **Histograma de residuos** - visualizacao da distribuicao dos
  residuos da regressao OLS
- [x] **Aba Estatistica expandida** - 8 secoes completas:
  1. Matriz Pearson, 2. p-valores significativos, 3. Spearman,
  4. OLS com R²/F-test, 5. Random Forest importance, 6. VIF,
  7. ACF temporal, 8. Correlacoes principais
- [x] **Fix NaN em dist_nearest_bus** - helper _prepare_numeric_df()
  preenche NaN com 0 e remove colunas completamente vazias
- [x] **Modulo IBGE SIDRA API** - src/data/ibge.py com fetch de
  indicadores municipais (populacao, area, densidade, alfabetizacao,
  piramide etaria, domicilios, cor/raça) com cache JSON
- [x] **Modulo iluminacao GeoSampa** - src/data/lighting.py com
  download via WFS (~613k pontos oficiais) com paginacao e cache parquet
- [x] **Modulo SSP-SP 2020+** - src/data/ssp_sp.py com download do
  dataset SPSafe (Zenodo), normalizacao de colunas e merge com dados
  labcity existentes
- [x] **Script download SSP-SP 2020** - scripts/download_ssp_sp_2020.py
  com opcoes --years e --merge para baixar e integrar dados novos
- [x] **Integracao no pipeline ETL** - iluminacao GeoSampa, IBGE e
  SSP-SP 2020+ integrados ao pipeline com logs e cache
- [x] **Indicadores IBGE no dashboard** - aba Sobre mostra populacao,
  densidade e taxa de alfabetizacao do Censo 2022
