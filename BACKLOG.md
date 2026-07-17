# SafeStreet - Backlog de Melhorias

> Sugestoes de evolucao do sistema, priorizadas por impacto e viabilidade.

---

## Fase 1 - Dados e Precisao

- [ ] **Integrar dados de iluminacao real** - mapear postes de luz via
  dados abertos da prefeitura (ou imageamento noturno via satellite) em
  vez de depender apenas do OSM
- [ ] **Adicionar dados de fluxo de pedestres** - usar dados de
  celularidade (Google Mobility, Apple Mobility) como proxy de
  movimentacao noturna
- [x] **Integrar dados meteorologicos** - cruzar crimes com chuva,
  temperatura, fase da lua (noites sem lua = mais escuras)
- [ ] **Dados de cameras por tipo** - categorizar cameras por
  funcionamento (funcional/defeituosa) usando dados de manutencao
  publica
- [ ] **Historico temporal** - importar SSP-SP de anos mais recentes
  (2020-2026) para analise de tendencia

## Fase 2 - Analise Avancada

- [ ] **Modelo preditivo** - treinar ML (Random Forest / XGBoost) para
  prever risco de uma area baseado em features de infraestrutura
- [ ] **Analise de series temporais** - detectar tendencias e
  sazonalidade nos crimes (dia da semana, mes, feriados)
- [ ] **Clusterizacao por padrao** - usar DBSCAN ou K-Means para
  descobrir clusters de crimes com padroes similares (roubo+noite vs
  droga+tarde)
- [ ] **Analise de rede** - mapear relacoes entre crimes do mesmo BO
  (multiplas vitimas, mesmo suspeito)
- [ ] **Indice de Sinistralidade** - calcular indice padronizado por
  populacao da area (crimes/100k habitantes)

## Fase 3 - Dashboard Interativo

- [ ] **Filtro temporal no dashboard** - slider para filtrar por
  hora do dia, dia da semana, periodo do ano
- [ ] **Comparacao entre cidades** - aba que compara metricas lado a
  lado entre Recife e Sao Paulo
- [ ] **Dashboard mobile** - layout responsivo para visualizacao no
  celular
- [ ] **Exportar relatorio PDF** - gerar relatorio automatico com
  graficos e insights da cidade selecionada
- [ ] **Filtros avancados** - filtrar por bairro, tipo de crime,
  faixa horaria diretamente no mapa
- [ ] **Street View integrado** - clique em um ponto e veja a
  iluminacao real da rua via Google Street View
- [ ] **Time-lapse temporal** - animacao mostrando evolucao dos crimes
  ao longo dos meses/anos

## Fase 4 - Infraestrutura e Escala

- [ ] **Pipeline incremental** - em vez de truncate+reinsert, fazer
  upsert inteligente apenas dos dados novos
- [ ] **Cache de queries** - usar `@st.cache_data` do Streamlit para
  nao recalcular a cada interacao
- [ ] **Celery/Redis** - rodar pipeline ETL em background com
  notificacao de conclusao
- [ ] **API REST** - endpoints FastAPI para consultar dados
  programaticamente (GET /crimes, GET /vulnerability, GET /correlations)
- [ ] **Docker Compose completo** - incluir dashboard, pipeline e
  scheduler no docker-compose
- [ ] **CI/CD** - GitHub Actions para rodar testes e deploy automatico

## Fase 5 - Visualizacao Premium

- [ ] **Mapa 3D** - usar PyDeck para visualizar crimes como barras
  3D sobre o mapa (altura = quantidade de crimes)
- [ ] **Heatmap animado** - heatmap que evolui ao longo do tempo
- [ ] **Grafico de Sankey** - fluxo crimes -> categoria -> zona de risco
  -> tipo de infraestrutura faltante
- [ ] **Network graph** - grafo mostrando relacao entre bairros com
  padroes criminais similares
- [ ] **Treemap** - visao hierarquica: cidade > bairro > categoria >
  natureza

## Fase 6 - Dados Externos

- [ ] **Dados IBGE** - cruzar com dados socioeconomicos (renda,
  escolaridade, populacao) por bairro
- [ ] **Dados de aluguel** - preco do metro quadrado como proxy de
  nivel socioeconomico
- [ ] **Dados de transporte** - rotas de onibus noturnas, linhas de
  metro funcionando a noite
- [ ] **Eventos culturais** - shows, jogos de futebol, festas como
  fator de aglomeracao
- [ ] **Noticias e redes sociais** - NLP para extrair sentimento
  sobre seguranca por regiao

## Fase 7 - UX e Apresentacao

- [ ] **Onboarding interativo** - tutorial guiado ao abrir o dashboard
  pela primeira vez
- [ ] **Comparacao com media nacional** - benchmarking da cidade contra
  medias brasileiras
- [ ] **Score de confianca** - indicador da qualidade dos dados por
  regiao (ex: "dados confiaveis" vs "poucos registros")
- [ ] **Linguagem natural** - gerar textos automaticos tipo "A regiao
  X concentra 3x mais crimes que a media, com 40% menos iluminacao"
- [ ] **Modo escuro/claro** - tema alternativo para apresentacoes em
  projetor
