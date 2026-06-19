from __future__ import annotations

import streamlit as st
from loguru import logger

from src.config import settings
from src.db.queries import get_h3_cells
from src.dashboard.components.map_viz import create_vulnerability_map
from src.spatial.postgis_ops import (
    calculate_lighting_density,
    calculate_nearest_light_distance,
    create_spatial_indexes,
)

st.set_page_config(
    page_title=settings.dashboard_title,
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _render_sidebar() -> None:
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/marker.png", width=60)
        st.title("SafeStreet")
        st.markdown("---")
        st.markdown("**Pipeline de Inteligência Espacial**")
        st.markdown("Análise de Vulnerabilidade Urbana Noturna")
        st.markdown("---")

        st.subheader("Processamento")
        refresh = st.button(" Atualizar Dados", use_container_width=True)
        if refresh:
            with st.spinner("Processando..."):
                try:
                    create_spatial_indexes()
                    calculate_lighting_density()
                    calculate_nearest_light_distance()
                    st.success("Dados atualizados com sucesso!")
                    st.rerun()
                except Exception as e:
                    logger.error("Erro ao atualizar dados: {}", e)
                    st.error(f"Erro: {e}")

        st.markdown("---")
        st.caption(f"H3 Resolução: {settings.h3_resolution}")
        st.caption(f"Cidade: {settings.osm_city_name}")


def _render_dashboard() -> None:
    st.title(settings.dashboard_title)
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    data = get_h3_cells()

    with col1:
        total_crimes = sum(row.get("crime_count", 0) for row in data)
        st.metric("Total de Crimes Noturnos", f"{total_crimes:,}")

    with col2:
        total_cells = len(data)
        st.metric("Células H3 Analisadas", f"{total_cells:,}")

    with col3:
        high_risk = sum(
            1 for row in data if (row.get("vulnerability_score") or 0) >= 0.7
        )
        st.metric("Zonas de Alto Risco", high_risk)

    with col4:
        moran_clusters = sum(
            1 for row in data if row.get("moran_cluster") == "HH"
        )
        st.metric("Clusters Moran HH", moran_clusters)

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["Mapa de Vulnerabilidade", "Dados Tabulares", "Sobre"])

    with tab1:
        if data:
            m = create_vulnerability_map(data)
            st.components.v1.html(m._repr_html_(), height=600)
        else:
            st.info("Nenhum dado disponível. Execute o pipeline primeiro.")

    with tab2:
        if data:
            import pandas as pd
            df = pd.DataFrame(data)
            st.dataframe(
                df,
                column_config={
                    "h3_index": "Índice H3",
                    "crime_count": "Crimes",
                    "lighting_density": "Dens. Iluminação",
                    "dist_nearest_lit": "Dist. Ilum (m)",
                    "vulnerability_score": "Score Vulnerab.",
                    "moran_cluster": "Cluster Moran",
                },
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Nenhum dado disponível.")

    with tab3:
        st.markdown("""
        ## SafeStreet

        **Pipeline de Inteligência Espacial e Análise de Vulnerabilidade Urbana Noturna**

        Este dashboard apresenta os resultados do pipeline de análise espacial que:

        1. **Ingere** dados criminais de fontes públicas
        2. **Extrai** infraestrutura urbana do OpenStreetMap
        3. **Indexa** ocorrências em células hexagonais (Uber H3)
        4. **Calcula** scores de vulnerabilidade
        5. **Valida** dependência espacial via Índice de Moran (PySAL)

        ### Interpretação das Cores

        -  **Verde:** Baixa vulnerabilidade
        -  **Amarelo:** Média vulnerabilidade
        -  **Laranja:** Alta vulnerabilidade
        -  **Vermelho:** Crítico
        """)


def main() -> None:
    _render_sidebar()
    _render_dashboard()


if __name__ == "__main__":
    main()
