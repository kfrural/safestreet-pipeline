from __future__ import annotations

import streamlit as st
from loguru import logger

from src.config import CITIES, get_city, list_cities, settings
from src.dashboard.components.map_viz import create_vulnerability_map
from src.db.queries import (
    get_cities_with_data,
    get_correlation_data,
    get_crime_by_infra_proximity,
    get_crime_by_transit_proximity,
    get_crime_categories,
    get_crime_locations,
    get_h3_cells,
    get_top_natures,
    get_vulnerability_gaps,
)

st.set_page_config(
    page_title=settings.dashboard_title,
    page_icon="\U0001f6e1\ufe0f",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _render_sidebar() -> str:
    selected_city = "sao-paulo"
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/marker.png", width=60)
        st.title("SafeStreet")
        st.markdown("---")
        st.markdown("**Pipeline de Inteligencia Espacial**")
        st.markdown("Analise de Vulnerabilidade Urbana Noturna")
        st.markdown("---")

        st.subheader("Cidade")
        available = get_cities_with_data()
        all_cities = list_cities()
        options = [c for c in all_cities if c in available] + [
            c for c in all_cities if c not in available
        ]
        if "sao-paulo" in options:
            options.remove("sao-paulo")
            options.insert(0, "sao-paulo")
        labels = {k: f"{CITIES[k].name} ({CITIES[k].state})" for k in options}
        default_idx = options.index(selected_city) if selected_city in options else 0
        selected_key = st.selectbox(
            "Selecione a cidade:",
            options=options,
            format_func=lambda k: labels[k],
            index=default_idx,
        )
        selected_city = selected_key

        st.markdown("---")
        st.subheader("Fonte dos Dados")
        city_cfg = get_city(selected_city)
        if city_cfg.data_source == "cttu":
            st.caption("CTTU Recife - Acidentes de Transito")
        elif city_cfg.data_source == "ssp_sp":
            st.caption("SSP-SP - Boletins de Ocorrencia")
        st.caption("OpenStreetMap - Infraestrutura Urbana")

        st.markdown("---")
        st.subheader("Camadas do Mapa")
        st.session_state.show_h3 = st.checkbox("Celulas H3", value=True)
        st.session_state.show_lighting = st.checkbox("Iluminacao", value=True)
        st.session_state.show_bus = st.checkbox("Paradas de Onibus", value=True)
        st.session_state.show_metro = st.checkbox("Metros", value=True)
        st.session_state.show_cameras = st.checkbox("Cameras", value=True)

        st.markdown("---")
        st.subheader("Processamento")
        refresh = st.button("Atualizar Dados", use_container_width=True)
        if refresh:
            with st.spinner("Processando..."):
                try:
                    from src.spatial.postgis_ops import (
                        calculate_moran_clusters,
                        calculate_nearest_infra_distance,
                        calculate_vulnerability_score,
                        create_spatial_indexes,
                        populate_h3_cells,
                    )

                    create_spatial_indexes()
                    populate_h3_cells(selected_city, settings.h3_resolution)
                    calculate_nearest_infra_distance(selected_city)
                    calculate_vulnerability_score(selected_city)
                    calculate_moran_clusters(selected_city)
                    st.success("Dados atualizados com sucesso!")
                    st.rerun()
                except Exception as e:
                    logger.error("Erro ao atualizar dados: {}", e)
                    st.error(f"Erro: {e}")

        st.markdown("---")
        st.caption(f"H3 Resolucao: {settings.h3_resolution}")
        st.caption(f"Cidade: {city_cfg.name}")

    return selected_city


def _render_dashboard(selected_city: str) -> None:
    city_cfg = get_city(selected_city)

    st.title(f"SafeStreet - {city_cfg.name}")
    st.markdown(
        f"Analise espacial de ocorrencias noturnas em {city_cfg.name}, "
        "correlacionadas com infraestrutura urbana."
    )
    st.markdown("---")

    data = get_h3_cells(city=selected_city)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_crimes = sum(row.get("crime_count", 0) for row in data)
        st.metric("Ocorrencias Noturnas", f"{total_crimes:,}")

    with col2:
        total_cells = len(data)
        st.metric("Celulas H3 Analisadas", f"{total_cells:,}")

    with col3:
        high_risk = sum(1 for row in data if (row.get("vulnerability_score") or 0) >= 0.7)
        st.metric("Zonas de Alto Risco", high_risk)

    with col4:
        moran_clusters = sum(1 for row in data if row.get("moran_cluster") == "HH")
        st.metric("Clusters Moran HH", moran_clusters)

    st.markdown("---")

    tab_map, tab_analysis, tab_data, tab_about = st.tabs(
        ["Mapa de Vulnerabilidade", "Analise de Fatores", "Dados Tabulares", "Sobre"]
    )

    with tab_map:
        if data:
            layers = {
                "h3": st.session_state.get("show_h3", True),
                "lighting": st.session_state.get("show_lighting", True),
                "bus": st.session_state.get("show_bus", True),
                "metro": st.session_state.get("show_metro", True),
                "cameras": st.session_state.get("show_cameras", True),
            }
            crime_locs = get_crime_locations(selected_city)
            m = create_vulnerability_map(data, city_cfg, layers, crime_locations=crime_locs)
            st.components.v1.html(m._repr_html_(), height=600)
        else:
            st.info("Nenhum dado disponivel. Execute o pipeline primeiro.")

    with tab_analysis:
        import pandas as pd
        import plotly.express as px

        categories = get_crime_categories(selected_city)
        if not categories:
            st.info("Dados de classificacao nao disponiveis. Execute o pipeline primeiro.")
        else:
            cat_df = pd.DataFrame(categories)
            cat_df.columns = ["Categoria", "Quantidade", "%"]

            st.subheader("Distribuicao dos Crimes por Gravidade")
            col_a, col_b = st.columns([2, 1])
            with col_a:
                colors = {
                    "Violencia": "#dc3545",
                    "Roubo/Furto": "#fd7e14",
                    "Trafico/Armas": "#6f42c1",
                    "Outros": "#6c757d",
                }
                fig_cat = px.bar(
                    cat_df,
                    x="Categoria",
                    y="Quantidade",
                    color="Categoria",
                    color_discrete_map=colors,
                    text="Quantidade",
                )
                fig_cat.update_layout(showlegend=False, height=350, margin={"t": 30})
                fig_cat.update_traces(textposition="outside")
                st.plotly_chart(fig_cat, use_container_width=True)
            with col_b:
                fig_pie = px.pie(
                    cat_df,
                    names="Categoria",
                    values="Quantidade",
                    color="Categoria",
                    color_discrete_map=colors,
                    hole=0.4,
                )
                fig_pie.update_layout(height=350, margin={"t": 30, "b": 30})
                fig_pie.update_traces(textinfo="percent+label", textfont_size=11)
                st.plotly_chart(fig_pie, use_container_width=True)

            st.markdown("---")

            corr_data = get_correlation_data(selected_city)
            if corr_data:
                corr_df = pd.DataFrame(corr_data)
                corr_df = corr_df.apply(pd.to_numeric, errors="coerce")

                st.subheader("Matriz de Correlacao")
                st.markdown(
                    "Correlacao de Pearson entre fatores de vulnerabilidade. "
                    "Valores proximos de **1** indicam correlacao positiva, "
                    "**-1** correlacao negativa."
                )

                numeric_cols = [
                    "crime_count",
                    "lighting_density",
                    "bus_stop_density",
                    "metro_density",
                    "camera_count",
                    "nightlife_density",
                    "dist_nearest_lit",
                    "dist_nearest_bus",
                    "dist_nearest_metro",
                    "vulnerability_score",
                ]
                available_numeric = [c for c in numeric_cols if c in corr_df.columns]
                corr_matrix = corr_df[available_numeric].corr()

                label_map = {
                    "crime_count": "Crimes",
                    "lighting_density": "Dens. Ilum.",
                    "bus_stop_density": "Dens. Onibus",
                    "metro_density": "Dens. Metro",
                    "camera_count": "Cameras",
                    "nightlife_density": "Nightlife",
                    "dist_nearest_lit": "Dist. Ilum.",
                    "dist_nearest_bus": "Dist. Onibus",
                    "dist_nearest_metro": "Dist. Metro",
                    "vulnerability_score": "Vulnerab.",
                }
                corr_matrix.index = [label_map.get(c, c) for c in corr_matrix.index]
                corr_matrix.columns = [label_map.get(c, c) for c in corr_matrix.columns]

                fig_corr = px.imshow(
                    corr_matrix,
                    text_auto=".2f",
                    color_continuous_scale="RdBu_r",
                    zmin=-1,
                    zmax=1,
                    aspect="auto",
                )
                fig_corr.update_layout(
                    height=450,
                    margin={"t": 30},
                    coloraxis_colorbar=dict(title="r"),
                )
                st.plotly_chart(fig_corr, use_container_width=True)

                st.markdown("---")

                st.subheader("Correlacoes Principais")
                pairs = []
                for i in range(len(available_numeric)):
                    for j in range(i + 1, len(available_numeric)):
                        r = corr_matrix.iloc[i, j]
                        if abs(r) > 0.15:
                            pairs.append((corr_matrix.index[i], corr_matrix.columns[j], r))
                pairs.sort(key=lambda x: abs(x[2]), reverse=True)
                for f1, f2, r in pairs[:6]:
                    direction = "positiva" if r > 0 else "negativa"
                    strength = "forte" if abs(r) > 0.5 else "moderada" if abs(r) > 0.3 else "fraca"
                    emoji = "🔴" if r > 0.3 else "🔵" if r < -0.3 else "⚪"
                    st.markdown(
                        f"{emoji} **{f1}** x **{f2}**: r={r:.3f} "
                        f"(correlacao {strength} {direction})"
                    )

                st.markdown("---")

                st.subheader("Crime vs Iluminacao (Scatter)")
                st.markdown("Cada ponto e uma celula H3. Tamanho = vulnerabilidade.")
                fig_scatter = px.scatter(
                    corr_df,
                    x="crime_count",
                    y="lighting_density",
                    size="vulnerability_score",
                    color="vulnerability_score",
                    color_continuous_scale="YlOrRd",
                    size_max=20,
                    labels={
                        "crime_count": "Qtd Crimes",
                        "lighting_density": "Densidade Iluminacao",
                        "vulnerability_score": "Vulnerabilidade",
                    },
                )
                fig_scatter.update_layout(height=400, margin={"t": 30})
                st.plotly_chart(fig_scatter, use_container_width=True)

                col_s1, col_s2 = st.columns(2)

                with col_s1:
                    st.markdown("**Crime vs Dist. Iluminacao**")
                    fig_s2 = px.scatter(
                        corr_df,
                        x="crime_count",
                        y="dist_nearest_lit",
                        color="vulnerability_score",
                        color_continuous_scale="YlOrRd",
                        labels={
                            "crime_count": "Qtd Crimes",
                            "dist_nearest_lit": "Dist. Ilum. (m)",
                            "vulnerability_score": "Vulnerab.",
                        },
                        trendline="ols",
                    )
                    fig_s2.update_layout(height=350, margin={"t": 30})
                    st.plotly_chart(fig_s2, use_container_width=True)

                with col_s2:
                    st.markdown("**Crime vs Dist. Transporte**")
                    fig_s3 = px.scatter(
                        corr_df,
                        x="crime_count",
                        y="dist_nearest_bus",
                        color="vulnerability_score",
                        color_continuous_scale="YlOrRd",
                        labels={
                            "crime_count": "Qtd Crimes",
                            "dist_nearest_bus": "Dist. Onibus (m)",
                            "vulnerability_score": "Vulnerab.",
                        },
                        trendline="ols",
                    )
                    fig_s3.update_layout(height=350, margin={"t": 30})
                    st.plotly_chart(fig_s3, use_container_width=True)

            st.markdown("---")

            st.subheader("Dados Climaticos")
            import json
            from pathlib import Path as _Path

            weather_file = _Path(f"data/external/weather_stats_{selected_city}.json")
            if weather_file.exists():
                weather_stats = json.loads(weather_file.read_text())
                wc1, wc2, wc3 = st.columns(3)
                with wc1:
                    st.metric(
                        "Temp Media",
                        f"{weather_stats.get('avg_temp', 'N/A')} C"
                        if weather_stats.get("avg_temp")
                        else "N/A",
                    )
                with wc2:
                    st.metric(
                        "Dias Chuva",
                        f"{weather_stats.get('rainy_crimes', 0)}",
                        f"{weather_stats.get('rain_pct', 0)}% dos crimes",
                    )
                with wc3:
                    st.metric(
                        "Dias Secos",
                        f"{weather_stats.get('dry_crimes', 0)}",
                    )

                if "by_rain_category" in weather_stats:
                    rain_df = pd.DataFrame(
                        list(weather_stats["by_rain_category"].items()),
                        columns=["Condicao", "Qtd"],
                    )
                    fig_rain = px.bar(
                        rain_df,
                        x="Condicao",
                        y="Qtd",
                        color="Condicao",
                        color_discrete_map={
                            "Seco": "#ffc107",
                            "Chuva leve": "#17a2b8",
                            "Chuva moderada": "#007bff",
                            "Chuva forte": "#dc3545",
                        },
                    )
                    fig_rain.update_layout(height=300, margin={"t": 30}, showlegend=False)
                    st.plotly_chart(fig_rain, use_container_width=True)

                st.markdown(
                    f"- Crimes em dias de chuva: **{weather_stats.get('rain_pct', 0)}%** do total"
                )
            else:
                st.info("Dados climaticos nao disponiveis para esta cidade.")

            st.markdown("---")

            infra_data = get_crime_by_infra_proximity(selected_city)
            transit_data = get_crime_by_transit_proximity(selected_city)

            if infra_data or transit_data:
                st.subheader("Crimes por Distancia da Infraestrutura")
                col_lit, col_trans = st.columns(2)

                with col_lit:
                    st.markdown("**Distancia da Iluminacao**")
                    if infra_data:
                        infra_df = pd.DataFrame(infra_data)
                        infra_df.columns = ["Categoria", "Distancia", "Qtd"]
                        fig_lit = px.bar(
                            infra_df,
                            x="Distancia",
                            y="Qtd",
                            color="Categoria",
                            color_discrete_map=colors,
                            barmode="group",
                            category_orders={
                                "Distancia": [
                                    "0-200m",
                                    "200-500m",
                                    "500-1000m",
                                    "1000m+",
                                ]
                            },
                        )
                        fig_lit.update_layout(height=350, margin={"t": 30}, legend_title_text="")
                        st.plotly_chart(fig_lit, use_container_width=True)

                with col_trans:
                    st.markdown("**Distancia do Transporte Publico**")
                    if transit_data:
                        transit_df = pd.DataFrame(transit_data)
                        transit_df.columns = ["Categoria", "Distancia", "Qtd"]
                        fig_trans = px.bar(
                            transit_df,
                            x="Distancia",
                            y="Qtd",
                            color="Categoria",
                            color_discrete_map=colors,
                            barmode="group",
                            category_orders={
                                "Distancia": [
                                    "0-200m",
                                    "200-500m",
                                    "500-1000m",
                                    "1000m+",
                                ]
                            },
                        )
                        fig_trans.update_layout(height=350, margin={"t": 30}, legend_title_text="")
                        st.plotly_chart(fig_trans, use_container_width=True)

            st.markdown("---")

            natures = get_top_natures(selected_city)
            if natures:
                st.subheader("Top Crimes por Categoria")
                natures_df = pd.DataFrame(natures)
                natures_df.columns = ["Categoria", "Natureza", "Qtd"]

                cat_order = ["Violencia", "Roubo/Furto", "Trafico/Armas", "Outros"]
                fig_nature = px.bar(
                    natures_df,
                    x="Qtd",
                    y="Natureza",
                    color="Categoria",
                    color_discrete_map=colors,
                    orientation="h",
                    facet_col="Categoria",
                    facet_col_wrap=2,
                    category_orders={"Categoria": cat_order},
                )
                fig_nature.update_layout(height=600, margin={"t": 30}, showlegend=False)
                fig_nature.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_nature, use_container_width=True)

            st.markdown("---")

            gaps = get_vulnerability_gaps(selected_city)
            if gaps:
                st.subheader("Zonas de Alerta: Alto Crimes + Pouca Infraestrutura")
                st.markdown(
                    "Celulas com alta criminalidade e pouca iluminacao "
                    "- potenciais areas de intervencao."
                )
                gaps_df = pd.DataFrame(gaps)
                gaps_df.columns = [
                    "H3",
                    "Crimes",
                    "Dens. Ilum.",
                    "Dist. Ilum (m)",
                    "Dens. Onibus",
                    "Cameras",
                    "Dens. Noturno",
                    "Vulnerab.",
                ]
                st.dataframe(
                    gaps_df,
                    use_container_width=True,
                    hide_index=True,
                )

            st.markdown("---")

            st.subheader("Insights Automáticos")
            top_cat = cat_df.iloc[0]
            st.markdown(
                f"- **{top_cat['Categoria']}** e a categoria mais comum "
                f"({top_cat['Quantidade']} ocorrencias, {top_cat['%']}%)"
            )

            if corr_data and len(corr_df) > 5:
                r_lit = corr_df["crime_count"].corr(corr_df["lighting_density"])
                direction = "menor" if r_lit < 0 else "maior"
                st.markdown(
                    f"- Correlacao crimes x iluminacao: **r={r_lit:.3f}** "
                    f"- celulas com {direction} iluminacao tendem a "
                    f"{'ter menos' if r_lit < 0 else 'ter mais'} crimes"
                )

                r_dist = corr_df["crime_count"].corr(corr_df["dist_nearest_lit"])
                if r_dist > 0:
                    st.markdown(
                        f"- Correlacao crimes x dist. iluminacao: "
                        f"**r={r_dist:.3f}** - areas mais distantes da "
                        f"iluminacao concentram mais crimes"
                    )

            if gaps:
                gap_count = len(gaps)
                total_crimes_gap = sum(g["crime_count"] for g in gaps)
                st.markdown(
                    f"- **{gap_count} zonas** com alto crimes e sem "
                    f"iluminacao adequate ({total_crimes_gap} ocorrencias)"
                )

    with tab_data:
        if data:
            df = pd.DataFrame(data)
            display_cols = {
                "h3_index": "Indice H3",
                "crime_count": "Ocorrencias",
                "lighting_density": "Dens. Iluminacao",
                "bus_stop_density": "Dens. Onibus",
                "metro_density": "Dens. Metro",
                "camera_count": "Cameras",
                "nightlife_density": "Dens. Nightlife",
                "dist_nearest_lit": "Dist. Ilum (m)",
                "dist_nearest_bus": "Dist. Onibus (m)",
                "dist_nearest_metro": "Dist. Metro (m)",
                "vulnerability_score": "Score Vulnerab.",
                "moran_cluster": "Cluster Moran",
            }
            available_cols = {k: v for k, v in display_cols.items() if k in df.columns}
            st.dataframe(
                df[list(available_cols.keys())].rename(columns=available_cols),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Nenhum dado disponivel.")

    with tab_about:
        st.markdown(f"""
        ## SafeStreet - {city_cfg.name}

        **Pipeline de Inteligencia Espacial e Analise de Vulnerabilidade Urbana Noturna**

        Este dashboard apresenta os resultados do pipeline de analise espacial que:

        1. **Ingere** dados de ocorrencias da {city_cfg.name}
        2. **Classifica** crimes por gravidade (Violencia, Roubo/Furto, Trafico/Armas, Outros)
        3. **Extrai** infraestrutura urbana: iluminação, onibus, metro,
           cameras e nightlife do OpenStreetMap
        4. **Integra** dados climaticos historicos (Open-Meteo API)
        5. **Indexa** ocorrencias em celulas hexagonais (Uber H3)
        6. **Calcula** scores de vulnerabilidade multi-fator
        7. **Valida** dependencia espacial via Indice de Moran (PySAL)

        ### Fonte dos Dados

        - **Acidentes de Transito:** CTTU Recife via dados.recife.pe.gov.br (ODbL)
        - **Crimes:** SSP-SP via labcidade/boletins-ssp (CC-BY)
        - **Infraestrutura:** OpenStreetMap via Overpass API

        ### Metodologia

        1. Filtro temporal: apenas ocorrencias noturnas (18h-06h)
        2. Classificacao por gravidade baseada na rubrica/natureza do boletim
        3. Indexacao hexagonal H3 (resolucao 9, ~quarteirao urbano)
        4. Calculo de densidade de infraestrutura por celula
        5. Score de vulnerabilidade multi-fator:
           - Densidade de ocorrencias
           - Densidade de iluminação (inversamente proporcional ao risco)
           - Distancia ate iluminação mais proxima
           - Distancia ate parada de onibus mais proxima
           - Distancia ate estacao de metro mais proxima
        6. Moran's I Global e Local (LISA) para validacao estatistica

        ### Classificacao de Crimes

        - **Violencia:** Homicidio, lesao corporal, morte, latrocinio
        - **Roubo/Furto:** Roubo, furto, receptacao, extorsao
        - **Trafico/Armas:** Drogas, porte ilegal de arma, disparo
        - **Outros:** Resistencia, localizacao, associacao criminosa

        ### Interpretacao das Cores

        - 🟢 **Verde:** Baixa vulnerabilidade
        - 🟡 **Amarelo:** Media vulnerabilidade
        - 🟠 **Laranja:** Alta vulnerabilidade
        - 🔴 **Vermelho:** Critico
        """)


def main() -> None:
    try:
        from src.db.connection import engine
        from src.db.models import Base

        Base.metadata.create_all(engine)
    except Exception as e:
        logger.warning("Nao foi possivel criar tabelas: {}", e)
    selected_city = _render_sidebar()
    _render_dashboard(selected_city)


if __name__ == "__main__":
    main()
