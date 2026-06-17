# SafeStreet: Pipeline de Inteligência Espacial e Análise de Vulnerabilidade Urbana Noturna

---

##  Por Que Este Projeto Existe?

A segurança pública urbana é um desafio complexo que frequentemente sofre com abordagens puramente reativas. No entanto, o espaço urbano possui características físicas intrínsecas que podem atuar como facilitadores ou inibidores da criminalidade. Entre essas variáveis de infraestrutura, a **iluminação pública** desempenha um papel psicológico e prático determinante na mitigação de crimes patrimoniais e de rua (como roubos e furtos a pedestres) durante o período noturno.

Mapeamentos de criminalidade convencionais costumam gerar apenas mapas de calor estáticos (*Kernel Density Estimation*) que mostram onde os crimes ocorrem, sem correlacioná-los com o ambiente ao redor. O **SafeStreet** foi projetado para preencher essa lacuna. Unindo engenharia de dados e análise estatística espacial rigorosa, o projeto isola ocorrências que acontecem estritamente sob a cobertura da noite e investiga se há uma relação de causa e efeito com o déficit de iluminação.

O objetivo prático é transformar dados brutos em uma **ferramenta de otimização de recursos urbanos**. Em vez de distribuir iluminação de forma homogênea, o algoritmo aponta quais coordenadas geográficas específicas apresentam a maior urgência de intervenção, maximizando o retorno de investimentos em segurança pública e smart cities.

---

##  Desenvolvimento Técnico Ponta a Ponta

Para responder a esse problema, foi arquitetada e implementada uma solução robusta dividida em quatro grandes pilares de engenharia e ciência de dados espaciais:

### 1. Engenharia de Dados & Ingestão Automatizada

* **Filtragem de Ocorrências:** Ingestão de bases de dados de segurança pública via Python, isolando registros ocorridos entre 18h00 e 06h00 e filtrando naturezas criminais diretamente impactadas pela visibilidade urbana.


* **Extração de Infraestrutura Baseada em Grafos:** Conexão direta com a API Overpass do **OpenStreetMap** através da biblioteca `OSMnx` para mapear, em tempo real, as coordenadas de postes de luz (`highway=lighting`) e nós de transporte público da região analisada.



### 2. Armazenamento e Indexação Espacial

* **Infraestrutura Espacial com PostGIS:** Modelagem e carga dos dados geográficos em um banco de dados relacional **PostgreSQL com a extensão PostGIS**.


* **Otimização de Queries:** Implementação de índices espaciais `GiST` (*Generalized Search Tree*), permitindo que cálculos de proximidade, intersecções e junções espaciais (*Spatial Joins*) entre milhões de pontos criminais e luminárias ocorram em milissegundos.



### 3. Geoprocessamento & Modelagem de Discretização Espacial

* **Malha Hexagonal Dinâmica (Uber H3):** Para anular as distorções territoriais causadas pelo uso de bairros políticos (que possuem formatos e tamanhos discrepantes), a área urbana foi segmentada em hexágonos uniformes utilizando o índice espacial **H3 da Uber**.


* **Agregação e Métricas:** Processamento de contagem agregada de incidentes por célula e cálculo da distância métrica de rede entre cada crime e o ponto de iluminação eficiente mais próximo.



### 4. Análise Estatística Espacial (Data Science Core)

* **Validação Científica do Risco:** Utilização da biblioteca `PySAL` para rejeitar a hipótese de que a distribuição dos crimes é puramente aleatória através do teste do **Índice de Moran Global**.


* **Mapeamento de Clusters (LISA):** Aplicação do indicador de associação espacial **Moran Local (LISA)** para identificar estatisticamente *hotspots* do tipo Alto-Alto (alta criminalidade cercada por alta criminalidade) que possuem correlação matemática com zonas de baixa densidade de iluminação pública.



### 5. Camada de Entrega e Visualização Analítica

* **Dashboard Interativo:** Desenvolvimento de uma interface de usuário responsiva utilizando **Streamlit**.


* **Renderização Dinâmica:** Integração de mapas interativos via `Folium` e `Plotly Mapbox`, permitindo que tomadores de decisão apliquem filtros temporais por tipo de delito, analisem o *Índice de Vulnerabilidade Noturna* calculado e identifiquem os quarteirões prioritários para manutenção urbana.



---

##  Como Executar o Projeto

### Pré-requisitos

* Docker e Docker Compose instalados.
* Python 3.9 ou superior.

```bash
# 1. Clonar o repositório e instalar dependências
git clone https://github.com/kfrural/safestreet-pipeline.git
cd safestreet
pip install -r requirements.txt

# 2. Inicializar o banco PostGIS via Docker
docker-compose up -d

# 3. Executar pipelines e inicializar a aplicação
python src/pipeline_etl.py
python src/geo_processing.py
streamlit run app.py

```

---

##  Contribuições e Contato

Sinta-se à vontade para abrir uma *issue* ou enviar um *pull request* com melhorias no pipeline estatístico ou novos cruzamentos de dados urbanos.

---

Nota: Para uma visão detalhada do escopo inicial e dos objetivos de negócio, consulte o documento formal gerado [proposta_projeto_safestreet.pdf](https://www.google.com/search?q=proposta_projeto_safestreet.pdf).
