from __future__ import annotations

import json

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from loguru import logger

from src.config import get_city, settings
from src.dashboard.components.map_viz import create_vulnerability_map
from src.db.cached_queries import (
    load_available_months,
    load_available_years,
    load_city_stats,
    load_correlation_data,
    load_crime_by_infra,
    load_crime_by_transit,
    load_crime_categories,
    load_crime_category_list,
    load_crime_locations_filtered,
    load_h3_cells,
    load_heatmap_hour_weekday,
    load_heatmap_monthly,
    load_neighborhood_crime_summary,
    load_neighborhood_infra_gaps,
    load_neighborhoods,
    load_seasonal_monthly,
    load_temporal_trend,
    load_top_natures,
    load_vulnerability_gaps,
    load_weekly_cycle,
)

st.set_page_config(
    page_title=settings.dashboard_title,
    page_icon="\U0001f6e1\ufe0f",
    layout="wide",
    initial_sidebar_state="expanded",
)

CATEGORY_COLORS = {
    "Violencia": "#dc3545",
    "Roubo/Furto": "#fd7e14",
    "Trafico/Armas": "#6f42c1",
    "Outros": "#6c757d",
}

MONTH_NAMES = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

DAY_NAMES = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sab"}


DARK_THEME_CSS = """
<style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    [data-testid="stSidebar"] { background-color: #1a1d23; }
    .stTabs [data-baseweb="tab-list"] { background-color: #1a1d23; }
    .stTabs [data-baseweb="tab"] { color: #fafafa; }
    .stTabs [aria-selected="true"] { background-color: #262730; color: #ff4b4b; }
    .stMetric { background-color: #1a1d23; border-radius: 8px; padding: 10px; }
    .stDataFrame { background-color: #1a1d23; }
    h1, h2, h3, h4, h5, h6 { color: #fafafa !important; }
    .stMarkdown p, .stMarkdown li, .stMarkdown span { color: #d1d5db; }
    [data-testid="stMetricValue"] { color: #fafafa; }
    [data-testid="stMetricLabel"] { color: #9ca3af; }
</style>
"""

LIGHT_THEME_CSS = """
<style>
    .stApp { background-color: #ffffff; color: #1a1a2e; }
    [data-testid="stSidebar"] { background-color: #f0f2f6; }
</style>
"""


def _apply_theme() -> None:
    if "theme" not in st.session_state:
        st.session_state.theme = "light"
    if st.session_state.theme == "dark":
        st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)


def _render_onboarding() -> None:
    if st.session_state.get("onboarding_complete"):
        return

    if "onboarding_step" not in st.session_state:
        st.session_state.onboarding_step = 0

    step = st.session_state.onboarding_step
    total_steps = 4

    with st.sidebar:
        st.markdown("---")
        st.markdown("### Bem-vindo ao SafeStreet!")
        st.progress((step + 1) / total_steps)

        steps_content = [
            {
                "title": "O que e o SafeStreet?",
                "text": (
                    "Pipeline de Inteligencia Espacial que analisa "
                    "ocorrencias noturnas da SSP-SP (2013-2019) "
                    "cruzadas com infraestrutura urbana: iluminacao, "
                    "onibus, metro, cameras e vida noturna."
                ),
            },
            {
                "title": "Como usar os filtros",
                "text": (
                    "Use os filtros na sidebar para selecionar ano, "
                    "mes, bairro e tipo de crime. Os dados sao "
                    "atualizados automaticamente ao mudar os filtros."
                ),
            },
            {
                "title": "Mapas e Graficos",
                "text": (
                    "O mapa mostra celulas H3 coloridas por "
                    "vulnerabilidade (verde=baixa, vermelho=alta). "
                    "Existem abas para analise temporal, heatmap, "
                    "estatisticas e analise avancada."
                ),
            },
            {
                "title": "Metricas Principais",
                "text": (
                    "O dashboard mostra: total de ocorrencias, "
                    "celulas H3 analisadas, zonas de alto risco, "
                    "clusters Moran HH, sinistralidade e muito mais."
                ),
            },
        ]

        current = steps_content[step]
        st.markdown(f"**Passo {step + 1}/{total_steps}: {current['title']}**")
        st.markdown(current["text"])

        cols = st.columns(2)
        with cols[0]:
            if step > 0:
                if st.button("Anterior", width="stretch", key="onb_prev"):
                    st.session_state.onboarding_step -= 1
                    st.rerun()
        with cols[1]:
            if step < total_steps - 1:
                if st.button("Proximo", width="stretch", key="onb_next"):
                    st.session_state.onboarding_step += 1
                    st.rerun()
            else:
                if st.button("Comecar!", width="stretch", key="onb_start"):
                    st.session_state.onboarding_complete = True
                    st.rerun()

        if st.button("Pular tutorial", key="onb_skip"):
            st.session_state.onboarding_complete = True
            st.rerun()


def _render_sidebar() -> tuple[str, int | None, int | None, str | None, str | None]:
    selected_city = "sao-paulo"
    selected_year = None
    selected_month = None
    selected_neighborhood = None
    selected_category = None

    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/marker.png", width=60)
        st.title("SafeStreet")
        st.markdown("---")
        st.markdown("**Pipeline de Inteligencia Espacial**")
        st.markdown("Analise de Vulnerabilidade Urbana Noturna")
        st.markdown("---")

        st.subheader("Fonte dos Dados")
        st.caption("SSP-SP - Boletins de Ocorrencia (2013-2019)")
        st.caption("OpenStreetMap - Infraestrutura Urbana")
        st.markdown("---")

        st.subheader("Filtros Temporais")
        years = load_available_years(selected_city)
        if years:
            year_options = [None] + years
            year_labels = {None: "Todos os anos"} | {y: str(y) for y in years}
            selected_year = st.selectbox(
                "Ano:",
                options=year_options,
                format_func=lambda x: year_labels[x],
            )

        months = load_available_months(selected_city) if selected_year is None else []
        if months:
            month_options = [None] + months
            month_labels = {None: "Todos os meses"}
            month_labels.update({m: MONTH_NAMES.get(m, str(m)) for m in months})
            selected_month = st.selectbox(
                "Mes:",
                options=month_options,
                format_func=lambda x: month_labels[x],
            )

        st.markdown("---")
        st.subheader("Filtros Avancados")

        categories = load_crime_category_list(selected_city)
        if categories:
            cat_options = [None] + categories
            cat_labels = {None: "Todas"} | {c: c for c in categories}
            selected_category = st.selectbox(
                "Tipo de Crime:",
                options=cat_options,
                format_func=lambda x: cat_labels.get(x, x),
            )

        neighborhoods = load_neighborhoods(selected_city)
        if neighborhoods:
            n_options = [None] + neighborhoods
            n_labels = {None: "Todos os bairros"} | {n: n for n in neighborhoods}
            selected_neighborhood = st.selectbox(
                "Bairro:",
                options=n_options,
                format_func=lambda x: n_labels.get(x, x),
            )

        st.markdown("---")
        st.subheader("Camadas do Mapa")
        st.session_state.show_h3 = st.checkbox("Celulas H3", value=True)
        st.session_state.show_lighting = st.checkbox("Iluminacao", value=True)
        st.session_state.show_bus = st.checkbox("Paradas de Onibus", value=True)
        st.session_state.show_metro = st.checkbox("Metros", value=True)
        st.session_state.show_cameras = st.checkbox("Cameras", value=True)
        st.session_state.show_crimes = st.checkbox("Crimes", value=True)

        st.markdown("---")
        st.subheader("Processamento")
        refresh = st.button("Atualizar Dados", width="stretch")
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
                    from src.db import cached_queries as _cq
                    for fn_name in dir(_cq):
                        fn = getattr(_cq, fn_name)
                        if callable(fn) and hasattr(fn, "clear"):
                            fn.clear()
                    st.rerun()
                except Exception as e:
                    logger.error("Erro ao atualizar dados: {}", e)
                    st.error(f"Erro: {e}")

        st.markdown("---")
        st.caption(f"H3 Resolucao: {settings.h3_resolution}")

        st.markdown("---")
        st.subheader("Tema")
        theme_option = st.radio(
            "Modo:",
            ["Claro", "Escuro"],
            index=0 if st.session_state.get("theme", "light") == "light" else 1,
            horizontal=True,
            key="theme_radio",
        )
        new_theme = "dark" if theme_option == "Escuro" else "light"
        if st.session_state.get("theme") != new_theme:
            st.session_state.theme = new_theme
            st.rerun()

    _apply_theme()

    return selected_city, selected_year, selected_month, selected_category, selected_neighborhood


def _render_metrics(selected_city: str, year: int | None, month: int | None) -> None:
    city_cfg = get_city(selected_city)
    stats = load_city_stats(selected_city)

    title = city_cfg.name
    if year:
        title += f" ({year})"
    if month:
        title += f" - {MONTH_NAMES.get(month, '')}"

    st.title(f"SafeStreet - {title}")
    st.markdown(
        "Analise espacial de ocorrencias noturnas, "
        "correlacionadas com infraestrutura urbana."
    )
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Ocorrencias Noturnas", f"{int(stats.get('total_crimes', 0)):,}")
    with col2:
        st.metric("Celulas H3 Analisadas", f"{int(stats.get('total_cells', 0)):,}")
    with col3:
        st.metric("Zonas de Alto Risco", int(stats.get("high_risk", 0)))
    with col4:
        st.metric("Clusters Moran HH", int(stats.get("moran_hh", 0)))

    sin_col1, sin_col2 = st.columns(2)
    with sin_col1:
        from pathlib import Path as _Path
        import json as _json

        _ibge_file = _Path(f"data/external/ibge_stats_{selected_city}.json")
        if _ibge_file.exists():
            _ibge = _json.loads(_ibge_file.read_text())
            _pop_raw = _ibge.get("populacao_2022")
            _pop = float(str(_pop_raw).replace(".", "").replace(",", ".")) if _pop_raw else 0
            _total = int(stats.get("total_crimes", 0))
            if _pop and _pop > 0 and _total > 0:
                _rate = (_total / _pop) * 100_000
                st.metric("Sinistralidade", f"{_rate:,.1f} /100k hab")
    with sin_col2:
        pass

    st.markdown("---")


def _render_map_tab(
    selected_city: str, year: int | None, month: int | None,
    category: str | None = None, neighborhood: str | None = None,
) -> None:
    st.subheader("Mapa de Vulnerabilidade")

    data = load_h3_cells(city=selected_city)
    if not data:
        st.info("Nenhum dado disponivel. Execute o pipeline primeiro.")
        return

    city_cfg = get_city(selected_city)

    map_mode = st.radio(
        "Visualizacao:", ["2D (Folium)", "3D (PyDeck)"],
        horizontal=True, key="map_mode",
    )

    if map_mode == "3D (PyDeck)":
        import pydeck as pdk

        df_cells = pd.DataFrame(data)
        df_cells = df_cells[df_cells["crime_count"] > 0].copy()
        for col in ["latitude", "longitude"]:
            if col not in df_cells.columns:
                df_cells[col] = 0.0
        if df_cells.empty:
            st.info("Nenhum dado para visualizacao 3D.")
            return

        layer_3d = pdk.Layer(
            "HexagonLayer",
            data=df_cells,
            get_position=["longitude", "latitude"],
            get_elevation="crime_count * 10",
            elevation_scale=2,
            radius=150,
            pickable=True,
            auto_highlight=True,
            get_fill_color=[
                "255 * (1 - vulnerability_score)",
                "255 * (1 - vulnerability_score) * 0.3",
                "50",
                "200",
            ],
        )

        crime_locs = load_crime_locations_filtered(
            selected_city, year=year, month=month, category=category,
        )
        if neighborhood:
            crime_locs = [c for c in crime_locs if c.get("neighborhood") == neighborhood]

        layers = [layer_3d]
        if crime_locs:
            df_crimes = pd.DataFrame(crime_locs)
            for col in ["latitude", "longitude"]:
                if col not in df_crimes.columns:
                    df_crimes[col] = 0.0
            df_crimes = df_crimes[
                (df_crimes["latitude"] != 0) & (df_crimes["longitude"] != 0)
            ]
            if not df_crimes.empty:
                CATEGORY_COLOR_MAP = {
                    "Violencia": [220, 53, 69, 200],
                    "Roubo/Furto": [253, 126, 20, 200],
                    "Trafico/Armas": [111, 66, 193, 200],
                    "Outros": [108, 117, 125, 200],
                }
                cat_col = "crime_category" if "crime_category" in df_crimes.columns else "category"
                df_crimes["color"] = df_crimes[cat_col].map(
                    lambda c: CATEGORY_COLOR_MAP.get(c, [108, 117, 125, 200])
                )
                crime_layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df_crimes,
                    get_position=["longitude", "latitude"],
                    get_radius=30,
                    get_fill_color="color",
                    pickable=True,
                    opacity=0.8,
                )
                layers.append(crime_layer)

        view = pdk.ViewState(
            latitude=city_cfg.center_lat,
            longitude=city_cfg.center_lon,
            zoom=city_cfg.zoom_start - 1,
            pitch=45,
        )
        tooltip = {
            "text": (
                "Crimes: {crime_count}\n"
                "Vulnerab: {vulnerability_score}\n"
                "Categoria: {crime_category}\n"
                "Bairro: {neighborhood}"
            )
        }
        st.pydeck_chart(pdk.Deck(
            layers=layers,
            initial_view_state=view,
            tooltip=tooltip,
        ), width="stretch", key="chart_3d_map")
        st.caption(f"Hexagonas: {len(df_cells)} | Crimes: {len(crime_locs)}")
        return

    layers = {
        "h3": st.session_state.get("show_h3", True),
        "lighting": st.session_state.get("show_lighting", True),
        "bus": st.session_state.get("show_bus", True),
        "metro": st.session_state.get("show_metro", True),
        "cameras": st.session_state.get("show_cameras", True),
    }

    crime_locs = load_crime_locations_filtered(
        selected_city, year=year, month=month, category=category,
    )
    if neighborhood:
        crime_locs = [c for c in crime_locs if c.get("neighborhood") == neighborhood]

    if crime_locs:
        st.caption(f"Exibindo {len(crime_locs)} ocorrencias filtradas")
    m = create_vulnerability_map(data, city_cfg, layers, crime_locations=crime_locs)
    st.iframe(m._repr_html_(), height=600)


def _render_temporal_tab(selected_city: str, year: int | None, month: int | None) -> None:
    st.subheader("Analise Temporal")

    trend_data = load_temporal_trend(selected_city, year=year, month=month)
    if trend_data:
        trend_df = pd.DataFrame(trend_data)

        st.markdown("#### Tendencia Mensal")
        monthly = trend_df.groupby(["year", "month"])["crime_count"].sum().reset_index()
        monthly["date"] = pd.to_datetime(
            monthly["year"].astype(str) + "-" + monthly["month"].astype(str) + "-01"
        )
        monthly = monthly.sort_values("date")

        fig_trend = px.line(
            monthly,
            x="date",
            y="crime_count",
            markers=True,
            labels={"date": "Periodo", "crime_count": "Qtd Crimes"},
        )
        fig_trend.update_layout(height=350, margin={"t": 30})
        st.plotly_chart(fig_trend, width="stretch", key="chart_trend")

    st.markdown("#### Comparacao Ano a Ano")
    all_years_data = load_temporal_trend(selected_city)
    if all_years_data:
        all_df = pd.DataFrame(all_years_data)
        years_list = sorted(all_df["year"].unique())
        if len(years_list) > 1:
            fig_yoy = go.Figure()
            palette = px.colors.qualitative.Set2
            for i, yr in enumerate(years_list):
                ydata = all_df[all_df["year"] == yr]
                ymonthly = ydata.groupby("month")["crime_count"].sum().reset_index()
                ymonthly = ymonthly.sort_values("month")
                ymonthly["month_name"] = ymonthly["month"].map(MONTH_NAMES)
                fig_yoy.add_trace(go.Scatter(
                    x=ymonthly["month_name"],
                    y=ymonthly["crime_count"],
                    mode="lines+markers",
                    name=str(yr),
                    line=dict(color=palette[i % len(palette)], width=2),
                ))
            fig_yoy.update_layout(
                height=380, margin={"t": 30},
                xaxis_title="Mes", yaxis_title="Crimes",
                legend_title_text="Ano",
            )
            st.plotly_chart(fig_yoy, width="stretch", key="chart_yoy")
        else:
            st.info("Dados de apenas um ano disponiveis. Necessario mais de 1 ano para comparacao.")

    st.markdown("#### Sazonalidade Mensal (Todos os Anos)")
    seasonal = load_seasonal_monthly(selected_city)
    if seasonal:
        s_df = pd.DataFrame(seasonal)
        s_monthly = s_df.groupby("month")["crime_count"].sum().reset_index()
        s_monthly["month_name"] = s_monthly["month"].map(MONTH_NAMES)

        fig_season = px.bar(
            s_monthly,
            x="month_name",
            y="crime_count",
            color="crime_count",
            color_continuous_scale="YlOrRd",
            labels={"month_name": "Mes", "crime_count": "Total Crimes"},
        )
        fig_season.update_layout(height=350, margin={"t": 30}, showlegend=False)
        st.plotly_chart(fig_season, width="stretch", key="chart_season")

    st.markdown("#### Ciclo Semanal")
    weekly = load_weekly_cycle(selected_city, year=year, month=month)
    if weekly:
        w_df = pd.DataFrame(weekly)
        w_df["day_name"] = w_df["day_of_week"].map(DAY_NAMES)
        w_df = w_df.sort_values("day_of_week")

        fig_weekly = px.bar(
            w_df,
            x="day_name",
            y="crime_count",
            color="crime_count",
            color_continuous_scale="Blues",
            labels={"day_name": "Dia da Semana", "crime_count": "Qtd Crimes"},
        )
        fig_weekly.update_layout(height=300, margin={"t": 30}, showlegend=False)
        st.plotly_chart(fig_weekly, width="stretch", key="chart_weekly")


def _render_heatmap_tab(selected_city: str, year: int | None, month: int | None) -> None:
    st.subheader("Heatmap: Hora x Dia da Semana")

    heatmap_data = load_heatmap_hour_weekday(selected_city, year=year, month=month)
    if not heatmap_data:
        st.info("Dados insuficientes para heatmap.")
        return

    hm_df = pd.DataFrame(heatmap_data)
    hm_df["day_name"] = hm_df["day_of_week"].map(DAY_NAMES)
    hm_df["hour_label"] = hm_df["hour"].apply(lambda h: f"{h:02d}:00")

    pivot = hm_df.pivot_table(
        index="day_name",
        columns="hour_label",
        values="crime_count",
        aggfunc="sum",
        fill_value=0,
    )

    day_order = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
    pivot = pivot.reindex([d for d in day_order if d in pivot.index])

    fig_hm = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale="YlOrRd",
            colorbar=dict(title="Qtd"),
        )
    )
    fig_hm.update_layout(
        height=400,
        margin={"t": 30},
        xaxis_title="Hora do Dia",
        yaxis_title="Dia da Semana",
    )
    st.plotly_chart(fig_hm, width="stretch", key="chart_heatmap")

    st.markdown("---")
    st.markdown("#### Evolucao Mensal (Heatmap Animado)")
    monthly_hm = load_heatmap_monthly(selected_city)
    if monthly_hm:
        m_df = pd.DataFrame(monthly_hm)
        m_df["month_label"] = m_df["month"].map(MONTH_NAMES)
        m_df["period"] = m_df["year"].astype(str) + "-" + m_df["month"].astype(str).str.zfill(2)
        m_df["day_name"] = m_df["day_of_week"].map(DAY_NAMES)
        m_df["hour_label"] = m_df["hour"].apply(lambda h: f"{h:02d}:00")

        periods = sorted(m_df["period"].unique())
        if len(periods) > 1:
            frames = []
            for period in periods:
                pm = m_df[m_df["period"] == period]
                pivot = pm.pivot_table(
                    index="day_name", columns="hour_label",
                    values="crime_count", aggfunc="sum", fill_value=0,
                )
                day_order = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
                pivot = pivot.reindex([d for d in day_order if d in pivot.index])
                frames.append(go.Frame(
                    data=go.Heatmap(
                        z=pivot.values, x=pivot.columns,
                        y=pivot.index, colorscale="YlOrRd",
                        colorbar=dict(title="Qtd"),
                        zmin=0,
                    ),
                    name=period,
                ))

            init_pivot = m_df[m_df["period"] == periods[0]].pivot_table(
                index="day_name", columns="hour_label",
                values="crime_count", aggfunc="sum", fill_value=0,
            )
            day_order = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
            init_pivot = init_pivot.reindex(
                [d for d in day_order if d in init_pivot.index]
            )

            fig_anim = go.Figure(
                data=go.Heatmap(
                    z=init_pivot.values, x=init_pivot.columns,
                    y=init_pivot.index, colorscale="YlOrRd",
                    colorbar=dict(title="Qtd"), zmin=0,
                ),
                frames=frames,
            )
            fig_anim.update_layout(
                updatemenus=[{
                    "type": "buttons",
                    "showactive": False,
                    "y": 1.08, "x": 0.5, "xanchor": "center",
                    "buttons": [
                        {"label": "Play", "method": "animate",
                         "args": [None, {"frame": {"duration": 600},
                                         "fromcurrent": True}]},
                        {"label": "Pause", "method": "animate",
                         "args": [[None], {"frame": {"duration": 0},
                                           "mode": "immediate"}]},
                    ],
                }],
                sliders=[{
                    "steps": [
                        {"args": [[p], {"frame": {"duration": 300},
                                        "mode": "immediate"}],
                         "label": p, "method": "animate"}
                        for p in periods
                    ],
                    "transition": {"duration": 300},
                    "x": 0, "y": -0.05, "len": 1.0,
                }],
                height=420, margin={"t": 30, "b": 80},
                xaxis_title="Hora do Dia",
                yaxis_title="Dia da Semana",
            )
            st.plotly_chart(fig_anim, width="stretch", key="chart_heatmap_anim")
        else:
            st.info("Dados de apenas um periodo disponiveis para animacao.")


def _render_statistics_tab(selected_city: str, year: int | None, month: int | None) -> None:
    st.subheader("Analise Estatistica Completa")

    corr_data = load_correlation_data(selected_city)
    if not corr_data:
        st.info("Dados insuficientes.")
        return

    corr_df = pd.DataFrame(corr_data)
    corr_df = corr_df.apply(pd.to_numeric, errors="coerce")

    from src.analytics.statistics import (
        compute_autocorrelation,
        compute_correlation_matrix,
        compute_random_forest_importance,
        compute_spearman_matrix,
        compute_vif,
        run_durbin_watson,
        run_ols_regression,
    )

    label_map = {
        "crime_count": "Crimes",
        "lighting_density": "Dens.Ilum",
        "bus_stop_density": "Dens.Onibus",
        "metro_density": "Dens.Metro",
        "camera_count": "Cameras",
        "nightlife_density": "Nightlife",
        "dist_nearest_lit": "Dist.Ilum",
        "dist_nearest_bus": "Dist.Onibus",
        "dist_nearest_metro": "Dist.Metro",
    }

    numeric_cols = [
        "crime_count", "lighting_density", "bus_stop_density",
        "metro_density", "camera_count", "nightlife_density",
        "dist_nearest_lit", "dist_nearest_metro", "vulnerability_score",
    ]
    available = [c for c in numeric_cols if c in corr_df.columns]

    corr_result = compute_correlation_matrix(corr_df, columns=available)
    if corr_result["matrix"].empty:
        st.warning("Correlacao nao calculada.")
        return

    corr_matrix = corr_result["matrix"]
    p_values = corr_result["p_values"]

    st.markdown("#### 1. Matriz de Correlacao (Pearson)")
    corr_display = corr_matrix.copy()
    corr_display.index = [label_map.get(c, c) for c in corr_display.index]
    corr_display.columns = [label_map.get(c, c) for c in corr_display.columns]

    fig_corr = px.imshow(
        corr_display,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        zmin=-1, zmax=1,
        aspect="auto",
    )
    fig_corr.update_layout(height=500, margin={"t": 30}, coloraxis_colorbar=dict(title="r"))
    st.plotly_chart(fig_corr, width="stretch", key="chart_corr")

    st.markdown("#### 2. Significancia Estatistica (p-valores)")
    sig_data = []
    for i, col1 in enumerate(corr_matrix.columns):
        for j, col2 in enumerate(corr_matrix.columns):
            if i < j:
                r = corr_matrix.iloc[i, j]
                p = p_values.iloc[i, j]
                sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
                sig_data.append({
                    "Var 1": label_map.get(col1, col1),
                    "Var 2": label_map.get(col2, col2),
                    "r (Pearson)": round(r, 4),
                    "p-valor": round(p, 6),
                    "Sig": sig,
                })
    sig_df = pd.DataFrame(sig_data).sort_values("p-valor")
    st.dataframe(sig_df, width="stretch", hide_index=True)

    st.markdown("---")
    st.markdown("#### 3. Correlacao de Spearman (Nao-Parametrica)")
    spearman_result = compute_spearman_matrix(corr_df, columns=available)
    if not spearman_result["matrix"].empty:
        sp_matrix = spearman_result["matrix"].copy()
        sp_matrix.index = [label_map.get(c, c) for c in sp_matrix.index]
        sp_matrix.columns = [label_map.get(c, c) for c in sp_matrix.columns]

        fig_sp = px.imshow(
            sp_matrix,
            text_auto=".2f",
            color_continuous_scale="PRGn_r",
            zmin=-1, zmax=1,
            aspect="auto",
        )
        fig_sp.update_layout(height=450, margin={"t": 30}, coloraxis_colorbar=dict(title="rho"))
        st.plotly_chart(fig_sp, width="stretch", key="chart_spearman")

    st.markdown("---")
    st.markdown("#### 4. Regressao OLS: Crimes ~ Infraestrutura")
    ols_result = run_ols_regression(corr_df)
    if "error" in ols_result:
        st.warning(ols_result["error"])
    else:
        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
        with col_r1:
            st.metric("R²", f"{ols_result['r_squared']:.4f}")
        with col_r2:
            st.metric("R² Ajustado", f"{ols_result['adj_r_squared']:.4f}")
        with col_r3:
            st.metric("F-stat", f"{ols_result['f_statistic']:.4f}")
        with col_r4:
            fp = ols_result["f_p_value"]
            st.metric("F p-value", f"{fp:.2e}")

        coef_data = []
        for name, info in ols_result["coefficients"].items():
            coef_data.append({
                "Variavel": name,
                "Coef": info["coef"],
                "t-stat": info["t_stat"],
                "p-valor": info["p_value"],
                "Sig": info["stars"],
            })
        st.dataframe(pd.DataFrame(coef_data), width="stretch", hide_index=True)

        if ols_result["residuals"] is not None:
            st.markdown("**Diagnostico dos Residuos**")
            resid = ols_result["residuals"]
            dw = run_durbin_watson(resid.values)
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                fig_resid = px.histogram(
                    resid, nbins=50,
                    labels={"value": "Residuo", "count": "Frequencia"},
                    title="Distribuicao dos Residuos",
                )
                fig_resid.update_layout(height=300, margin={"t": 40})
                st.plotly_chart(fig_resid, width="stretch", key="chart_resid")
            with col_d2:
                st.metric("Durbin-Watson", dw["durbin_watson"])
                st.caption(dw["interpretation"])

    st.markdown("---")
    st.markdown("#### 5. Feature Importance (Random Forest)")
    rf_result = compute_random_forest_importance(corr_df)
    if "error" in rf_result:
        st.warning(rf_result["error"])
    else:
        st.metric("R² (treino)", f"{rf_result['r_squared_train']:.4f}")
        rf_features = pd.DataFrame(rf_result["features"])
        rf_features.columns = ["Feature", "Importancia"]
        rf_features["Feature"] = rf_features["Feature"].map(label_map)
        fig_rf = px.bar(
            rf_features, x="Importancia", y="Feature",
            orientation="h", color="Importancia",
            color_continuous_scale="Viridis",
        )
        fig_rf.update_layout(height=350, margin={"t": 30}, showlegend=False)
        fig_rf.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_rf, width="stretch", key="chart_rf")

    st.markdown("---")
    st.markdown("#### 6. Multicolinearidade (VIF)")
    vif_result = compute_vif(corr_df, columns=available)
    if vif_result["vif"]:
        vif_data = [
            {"Variavel": label_map.get(k, k), "VIF": v}
            for k, v in vif_result["vif"].items()
        ]
        vif_df = pd.DataFrame(vif_data).sort_values("VIF", ascending=False)

        def color_vif(val):
            if val > 10:
                return "background-color: #ff6b6b"
            elif val > 5:
                return "background-color: #ffd93d"
            return ""

        st.dataframe(
            vif_df.style.map(color_vif, subset=["VIF"]),
            width="stretch", hide_index=True,
        )
        st.caption("VIF > 10: multicolinearidade critica | VIF > 5: moderada | VIF < 5: ok")

    st.markdown("---")
    st.markdown("#### 7. Autocorrelacao Temporal (ACF)")
    trend_data = load_temporal_trend(selected_city)
    if trend_data:
        trend_df = pd.DataFrame(trend_data)
        monthly = trend_df.groupby(["year", "month"])["crime_count"].sum().reset_index()
        monthly = monthly.sort_values(["year", "month"])
        values = monthly["crime_count"].values

        acf_result = compute_autocorrelation(values, max_lag=12)
        if acf_result:
            acf_df = pd.DataFrame(acf_result)
            fig_acf = px.bar(
                acf_df, x="lag", y="acf",
                color="significant",
                color_discrete_map={True: "#dc3545", False: "#adb5bd"},
                labels={"lag": "Lag (meses)", "acf": "ACF"},
            )
            fig_acf.add_hline(y=1.96 / np.sqrt(len(values)), line_dash="dash", line_color="gray")
            fig_acf.add_hline(y=-1.96 / np.sqrt(len(values)), line_dash="dash", line_color="gray")
            fig_acf.update_layout(height=350, margin={"t": 30})
            st.plotly_chart(fig_acf, width="stretch", key="chart_acf")

    st.markdown("---")
    st.markdown("#### 8. Correlacoes Principais (|r| > 0.15)")
    pairs = []
    cols_in_matrix = corr_matrix.columns.tolist()
    for i, col1 in enumerate(cols_in_matrix):
        for j, col2 in enumerate(cols_in_matrix):
            if i < j:
                r = corr_matrix.iloc[i, j]
                p = p_values.iloc[i, j]
                if abs(r) > 0.15:
                    pairs.append((label_map.get(col1, col1), label_map.get(col2, col2), r, p))
    pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    for f1, f2, r, p in pairs[:8]:
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        direction = "positiva" if r > 0 else "negativa"
        strength = "forte" if abs(r) > 0.5 else "moderada" if abs(r) > 0.3 else "fraca"
        st.markdown(
            f"**{f1}** x **{f2}**: r={r:.3f} (p={p:.4f}) "
            f"- correlacao {strength} {direction} {sig}"
        )

    st.markdown("---")
    st.markdown("#### 9. Modelo Preditivo de Risco")
    from src.analytics.statistics import train_risk_predictor

    pred_result = train_risk_predictor(corr_df)
    if "error" in pred_result:
        st.warning(pred_result["error"])
    else:
        st.info(
            f"Melhor modelo: **{pred_result['best_model']}** "
            f"(R² teste: {pred_result['models'][pred_result['best_model']]['r2_test']:.4f})"
        )

        pred_cols = st.columns(3)
        for idx, (mname, mdata) in enumerate(pred_result["models"].items()):
            with pred_cols[idx]:
                st.markdown(f"**{mname}**")
                st.metric("R² teste", f"{mdata['r2_test']:.4f}")
                st.metric("RMSE", f"{mdata['rmse']:.2f}")
                st.metric("MAE", f"{mdata['mae']:.2f}")
                st.metric("R² CV (media±dp)",
                         f"{mdata['r2_cv_mean']:.3f} ± {mdata['r2_cv_std']:.3f}")

        best_name = pred_result["best_model"]
        best_features = pred_result["models"][best_name]["feature_importance"]
        rf_imp_df = pd.DataFrame(best_features)
        rf_imp_df["feature"] = rf_imp_df["feature"].map(label_map)
        fig_pred = px.bar(
            rf_imp_df, x="importance", y="feature",
            orientation="h", color="importance",
            color_continuous_scale="Plasma",
            title=f"Feature Importance ({best_name})",
        )
        fig_pred.update_layout(height=300, margin={"t": 40}, showlegend=False)
        fig_pred.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_pred, width="stretch", key="chart_pred_importance")

        if pred_result.get("y_test") and pred_result.get("y_pred"):
            scatter_df = pd.DataFrame({
                "Real": pred_result["y_test"],
                "Previsto": pred_result["y_pred"],
            })
            fig_scatter = px.scatter(
                scatter_df, x="Real", y="Previsto",
                title="Real vs Previsto",
                opacity=0.5,
            )
            max_val = max(scatter_df["Real"].max(), scatter_df["Previsto"].max())
            fig_scatter.add_trace(go.Scatter(
                x=[0, max_val], y=[0, max_val],
                mode="lines", line=dict(dash="dash", color="red"),
                name="Ideal",
            ))
            fig_scatter.update_layout(height=350, margin={"t": 40})
            st.plotly_chart(fig_scatter, width="stretch", key="chart_pred_scatter")

    st.markdown("---")
    st.markdown("#### 10. Clusterizacao por Padrao")
    from src.analytics.statistics import cluster_crime_patterns

    cluster_result = cluster_crime_patterns(corr_df)
    if "error" in cluster_result:
        st.warning(cluster_result["error"])
    else:
        cl_cols = st.columns(4)
        with cl_cols[0]:
            st.metric("Clusters K-Means", cluster_result["n_clusters_kmeans"])
        with cl_cols[1]:
            st.metric("Silhouette Score", f"{cluster_result['silhouette_score']:.3f}")
        with cl_cols[2]:
            st.metric("Clusters DBSCAN", cluster_result["n_clusters_dbscan"])
        with cl_cols[3]:
            st.metric("Pts. Ruido DBSCAN", cluster_result["n_noise_dbscan"])

        st.markdown("**Perfis dos Clusters (K-Means)**")
        cluster_rows = []
        for name, info in cluster_result["centroids"].items():
            row = {"Cluster": name, "Tamanho": info["size"]}
            for feat, val in info["means"].items():
                row[label_map.get(feat, feat)] = val
            cluster_rows.append(row)
        st.dataframe(pd.DataFrame(cluster_rows), width="stretch", hide_index=True)

        if cluster_result["inertia_curve"]:
            inertia_df = pd.DataFrame(cluster_result["inertia_curve"])
            fig_elbow = px.line(
                inertia_df, x="k", y="inertia",
                title="Elbow Method (Inercia vs K)",
                markers=True,
            )
            fig_elbow.update_layout(height=280, margin={"t": 40})
            st.plotly_chart(fig_elbow, width="stretch", key="chart_elbow")

    st.markdown("---")
    st.markdown("#### 11. Indice de Sinistralidade")
    from src.analytics.statistics import compute_sinistrality_index
    from pathlib import Path

    ibge_file = Path(f"data/external/ibge_stats_{selected_city}.json")
    population = None
    if ibge_file.exists():
        ibge_data = json.loads(ibge_file.read_text())
        population = ibge_data.get("populacao_2022")

    if population and population > 0:
        total_crimes = int(corr_df["crime_count"].sum())
        sin_result = compute_sinistrality_index(total_crimes, int(population))

        sin_cols = st.columns(4)
        with sin_cols[0]:
            st.metric("Taxa (crimes/100k hab)", f"{sin_result['rate_per_100k']:,.1f}")
        with sin_cols[1]:
            st.metric("Nivel", sin_result.get("level", "N/A"))
        with sin_cols[2]:
            st.metric("Total Crimes", f"{total_crimes:,}")
        with sin_cols[3]:
            st.metric("Populacao", f"{population:,}")

        if total_crimes > 0 and "crime_category" in corr_df.columns:
            cat_sin = corr_df["crime_category"].value_counts()
            cat_rows = []
            for cat, count in cat_sin.items():
                cat_sin_result = compute_sinistrality_index(int(count), int(population))
                cat_rows.append({
                    "Categoria": cat,
                    "Crimes": count,
                    "Crimes/100k hab": f"{cat_sin_result['rate_per_100k']:,.1f}",
                    "Nivel": cat_sin_result.get("level", ""),
                })
            st.dataframe(pd.DataFrame(cat_rows), width="stretch", hide_index=True)
    else:
        st.warning("Dados de populacao IBGE nao disponiveis para calcular sinistralidade.")


def _render_analysis_tab(selected_city: str, year: int | None, month: int | None) -> None:
    st.subheader("Analise de Fatores")

    categories = load_crime_categories(selected_city)
    if not categories:
        st.info("Dados de classificacao nao disponiveis.")
        return

    cat_df = pd.DataFrame(categories)
    cat_df.columns = ["Categoria", "Quantidade", "%"]

    col_a, col_b = st.columns([2, 1])
    with col_a:
        fig_cat = px.bar(
            cat_df, x="Categoria", y="Quantidade",
            color="Categoria", color_discrete_map=CATEGORY_COLORS,
            text="Quantidade",
        )
        fig_cat.update_layout(showlegend=False, height=350, margin={"t": 30})
        fig_cat.update_traces(textposition="outside")
        st.plotly_chart(fig_cat, width="stretch", key="chart_cat")
    with col_b:
        fig_pie = px.pie(
            cat_df, names="Categoria", values="Quantidade",
            color="Categoria", color_discrete_map=CATEGORY_COLORS, hole=0.4,
        )
        fig_pie.update_layout(height=350, margin={"t": 30, "b": 30})
        fig_pie.update_traces(textinfo="percent+label", textfont_size=11)
        st.plotly_chart(fig_pie, width="stretch", key="chart_pie")

    st.markdown("---")
    natures = load_top_natures(selected_city)
    if natures:
        st.subheader("Top Crimes por Categoria")
        natures_df = pd.DataFrame(natures)
        natures_df.columns = ["Categoria", "Natureza", "Qtd"]
        cat_order = ["Violencia", "Roubo/Furto", "Trafico/Armas", "Outros"]
        fig_nature = px.bar(
            natures_df, x="Qtd", y="Natureza",
            color="Categoria", color_discrete_map=CATEGORY_COLORS,
            orientation="h", facet_col="Categoria", facet_col_wrap=2,
            category_orders={"Categoria": cat_order},
        )
        fig_nature.update_layout(height=600, margin={"t": 30}, showlegend=False)
        fig_nature.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_nature, width="stretch", key="chart_nature")

    st.markdown("---")
    st.subheader("Distancia da Infraestrutura")
    infra_data = load_crime_by_infra(selected_city)
    transit_data = load_crime_by_transit(selected_city)

    if infra_data or transit_data:
        col_lit, col_trans = st.columns(2)
        with col_lit:
            st.markdown("**Iluminacao**")
            if infra_data:
                infra_df = pd.DataFrame(infra_data)
                infra_df.columns = ["Categoria", "Distancia", "Qtd"]
                fig_lit = px.bar(
                    infra_df, x="Distancia", y="Qtd", color="Categoria",
                    color_discrete_map=CATEGORY_COLORS, barmode="group",
                    category_orders={"Distancia": ["0-200m", "200-500m", "500-1000m", "1000m+"]},
                )
                fig_lit.update_layout(height=350, margin={"t": 30}, legend_title_text="")
                st.plotly_chart(fig_lit, width="stretch", key="chart_lit")
        with col_trans:
            st.markdown("**Transporte Publico**")
            if transit_data:
                transit_df = pd.DataFrame(transit_data)
                transit_df.columns = ["Categoria", "Distancia", "Qtd"]
                fig_trans = px.bar(
                    transit_df, x="Distancia", y="Qtd", color="Categoria",
                    color_discrete_map=CATEGORY_COLORS, barmode="group",
                    category_orders={"Distancia": ["0-200m", "200-500m", "500-1000m", "1000m+"]},
                )
                fig_trans.update_layout(height=350, margin={"t": 30}, legend_title_text="")
                st.plotly_chart(fig_trans, width="stretch", key="chart_trans")

    st.markdown("---")
    st.subheader("Dados Climaticos")
    from pathlib import Path

    weather_file = Path(f"data/external/weather_stats_{selected_city}.json")
    if weather_file.exists():
        weather_stats = json.loads(weather_file.read_text())
        wc1, wc2, wc3 = st.columns(3)
        with wc1:
            avg_t = weather_stats.get("avg_temp")
            st.metric("Temp Media", f"{avg_t:.1f} C" if avg_t else "N/A")
        with wc2:
            st.metric(
                "Dias Chuva",
                f"{weather_stats.get('rainy_crimes', 0)}",
                f"{weather_stats.get('rain_pct', 0)}% dos crimes",
            )
        with wc3:
            st.metric("Dias Secos", f"{weather_stats.get('dry_crimes', 0)}")

        if "by_rain_category" in weather_stats:
            rain_df = pd.DataFrame(
                list(weather_stats["by_rain_category"].items()),
                columns=["Condicao", "Qtd"],
            )
            fig_rain = px.bar(
                rain_df, x="Condicao", y="Qtd", color="Condicao",
                color_discrete_map={
                    "Seco": "#ffc107", "Chuva leve": "#17a2b8",
                    "Chuva moderada": "#007bff", "Chuva forte": "#dc3545",
                },
            )
            fig_rain.update_layout(height=300, margin={"t": 30}, showlegend=False)
            st.plotly_chart(fig_rain, width="stretch", key="chart_rain")


def _render_data_tab(selected_city: str) -> None:
    st.subheader("Dados Tabulares")
    data = load_h3_cells(city=selected_city)
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
            width="stretch", hide_index=True,
        )

        st.markdown("---")
        st.subheader("Score de Confianca por Celula")
        from src.analytics.insights import classify_confidence, compute_confidence_score

        df_conf = df.copy()
        df_conf["confianca"] = df_conf.apply(
            lambda row: compute_confidence_score(
                int(row.get("crime_count", 0) or 0),
                {
                    "lighting_density": row.get("lighting_density"),
                    "bus_stop_density": row.get("bus_stop_density"),
                    "camera_count": row.get("camera_count"),
                    "nightlife_density": row.get("nightlife_density"),
                },
                years_of_data=7,
            ),
            axis=1,
        )
        df_conf["nivel_confianca"] = df_conf["confianca"].apply(classify_confidence)

        conf_display = df_conf[["h3_index", "crime_count", "confianca", "nivel_confianca"]].copy()
        conf_display.columns = ["Indice H3", "Ocorrencias", "Score Confianca", "Nivel"]

        conf_display["Nivel"] = conf_display["Nivel"].apply(
            lambda x: f":{'red' if x == 'Baixa' else 'orange' if x == 'Media' else 'green'}[{x}]"
        )

        st.dataframe(
            conf_display.sort_values("Score Confianca", ascending=False),
            width="stretch", hide_index=True,
        )

        conf_counts = df_conf["nivel_confianca"].value_counts()
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            st.metric("Alta Confianca", conf_counts.get("Alta", 0))
        with cc2:
            st.metric("Media Confianca", conf_counts.get("Media", 0))
        with cc3:
            st.metric("Baixa Confianca", conf_counts.get("Baixa", 0))

        st.markdown("---")
        st.subheader("Zonas de Alerta")
        gaps = load_vulnerability_gaps(selected_city)
        if gaps:
            gaps_df = pd.DataFrame(gaps)
            gaps_df.columns = [
                "H3", "Crimes", "Dens. Ilum.", "Dist. Ilum (m)",
                "Dens. Onibus", "Cameras", "Dens. Noturno", "Vulnerab.",
            ]
            st.dataframe(gaps_df, width="stretch", hide_index=True)
    else:
        st.info("Nenhum dado disponivel.")


def _render_about_tab(selected_city: str) -> None:
    from pathlib import Path

    city_cfg = get_city(selected_city)
    st.markdown(f"""
    ## SafeStreet - {city_cfg.name}

    **Pipeline de Inteligencia Espacial e Analise de Vulnerabilidade Urbana Noturna**

    1. **Ingere** dados de ocorrencias SSP-SP (2013-2019, 2020-2022 via SPSafe)
    2. **Classifica** crimes por gravidade (Violencia, Roubo/Furto, Trafico/Armas, Outros)
    3. **Extrai** infraestrutura urbana: iluminacao, onibus, metro, cameras, nightlife (OSM)
    4. **Integra** iluminacao oficial GeoSampa/SP Regula (~97k pontos via WFS)
    5. **Integra** dados climaticos historicos (Open-Meteo API)
    6. **Busca** indicadores socioeconomicos IBGE (Censo 2022)
    7. **Busca** dados de aluguel e renda (IBGE SIDRA)
    8. **Analisa** transporte noturno com horarios de funcionamento (OSM)
    9. **Cataloga** venues culturais como proxy de aglomeracao (OSM)
    10. **Analisa** sentimento de noticias de seguranca (RSS + NLP)
    11. **Indexa** ocorrencias em celulas hexagonais (Uber H3 resolucao 9)
    12. **Calcula** scores de vulnerabilidade via PCA (analise de componentes principais)
    13. **Valida** dependencia espacial via Indice de Moran Global e Local (LISA)
    14. **Treina** modelos preditivos (Random Forest + Gradient Boosting)
    15. **Clusteriza** padroes de criminalidade (K-Means + DBSCAN)
    16. **Calcula** indice de sinistralidade (crimes/100k habitantes)
    """)

    ibge_file = Path(f"data/external/ibge_stats_{selected_city}.json")
    if ibge_file.exists():
        ibge_data = json.loads(ibge_file.read_text())
        ic1, ic2, ic3 = st.columns(3)
        with ic1:
            pop = ibge_data.get("populacao_2022", "N/A")
            pop_str = f"{pop:,}" if isinstance(pop, (int, float)) else pop
            st.metric("Populacao (Censo 2022)", pop_str)
        with ic2:
            dens = ibge_data.get("densidade_demografica", "N/A")
            st.metric("Densidade (hab/km2)", f"{dens}" if dens else "N/A")
        with ic3:
            lit = ibge_data.get("taxa_alfabetizacao_15plus", "N/A")
            st.metric("Alfabetizacao 15+ anos", f"{lit}%" if lit else "N/A")
    else:
        st.caption("Dados IBGE nao disponiveis. Execute o pipeline para buscar.")

    st.markdown("---")
    st.subheader("Dados de Renda (IBGE SIDRA - Censo 2022)")
    rental_file = Path(f"data/external/rental_stats_{selected_city}.json")
    if rental_file.exists():
        rental_data = json.loads(rental_file.read_text())
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            avg_inc = rental_data.get("avg_monthly_income")
            st.metric("Renda per Capita Media", f"R$ {avg_inc:,.0f}" if avg_inc else "N/A")
        with rc2:
            med_inc = rental_data.get("median_monthly_income")
            st.metric("Renda per Capita Mediana", f"R$ {med_inc:,.0f}" if med_inc else "N/A")
        with rc3:
            pop = rental_data.get("population_2022")
            st.metric("Populacao 2022", f"{pop:,}" if pop else "N/A")
    else:
        st.caption("Dados de renda nao disponiveis. Execute o pipeline para buscar.")

    st.markdown("---")
    st.subheader("Transporte Noturno (OSM)")
    transport_file = Path(f"data/external/transport_night_{selected_city}.json")
    if transport_file.exists():
        transport_data = json.loads(transport_file.read_text())
        for infra, info in transport_data.items():
            if info.get("total", 0) > 0:
                st.markdown(
                    f"**{infra}**: {info['total']} pontos | "
                    f"{info.get('night_open', 0)} abrem a noite"
                )
    else:
        st.caption("Dados de transporte noturno nao disponiveis.")

    st.markdown("---")
    st.subheader("Sentimento de Noticias (RSS + NLP)")
    sentiment_file = Path(f"data/external/sentiment_{selected_city}.json")
    if sentiment_file.exists():
        sentiment_data = json.loads(sentiment_file.read_text())
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.metric("Headlines Analisadas", sentiment_data.get("total", 0))
        with sc2:
            avg_s = sentiment_data.get("avg_score", 0)
            st.metric("Sentimento Medio", f"{avg_s:+.3f}")
        with sc3:
            labels = sentiment_data.get("labels", {})
            st.metric("Negativas", labels.get("negativo", 0))
    else:
        st.caption("Dados de sentimento nao disponiveis.")

    st.markdown("---")
    st.subheader("Comparacao com Media Nacional (IBGE)")
    from src.data.ibge import get_national_comparison

    try:
        comparison = get_national_comparison(cache_dir=Path("data/external"))
        nat = comparison.get("nacional", {})
        sp = comparison.get("sao_paulo", {})

        if nat and sp:
            categories_radar = []
            sp_vals = []
            nat_vals = []

            sp_pop = sp.get("populacao")
            nat_pop = nat.get("populacao")
            if sp_pop and nat_pop:
                try:
                    sp_pop_n = float(str(sp_pop).replace(".", "").replace(",", "."))
                    nat_pop_n = float(str(nat_pop).replace(".", "").replace(",", "."))
                    categories_radar.append("Populacao (log)")
                    sp_vals.append(np.log10(sp_pop_n))
                    nat_vals.append(np.log10(nat_pop_n))
                except (ValueError, TypeError):
                    pass

            sp_dens = sp.get("densidade")
            nat_dens = nat.get("densidade")
            if sp_dens and nat_dens:
                try:
                    sp_d = float(str(sp_dens).replace(",", "."))
                    nat_d = float(str(nat_dens).replace(",", "."))
                    categories_radar.append("Densidade (log)")
                    sp_vals.append(np.log10(max(sp_d, 0.1)))
                    nat_vals.append(np.log10(max(nat_d, 0.1)))
                except (ValueError, TypeError):
                    pass

            sp_lit = sp.get("taxa_alfabetizacao")
            nat_lit = nat.get("taxa_alfabetizacao")
            if sp_lit and nat_lit:
                try:
                    sp_l = float(str(sp_lit).replace(",", "."))
                    nat_l = float(str(nat_lit).replace(",", "."))
                    categories_radar.append("Alfabetizacao")
                    sp_vals.append(sp_l)
                    nat_vals.append(nat_l)
                except (ValueError, TypeError):
                    pass

            if len(categories_radar) >= 2:
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=sp_vals + [sp_vals[0]],
                    theta=categories_radar + [categories_radar[0]],
                    fill="toself", name="Sao Paulo",
                    line_color="#dc3545",
                ))
                fig_radar.add_trace(go.Scatterpolar(
                    r=nat_vals + [nat_vals[0]],
                    theta=categories_radar + [categories_radar[0]],
                    fill="toself", name="Brasil",
                    line_color="#007bff",
                ))
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True)),
                    showlegend=True, height=400,
                    margin={"t": 40},
                )
                st.plotly_chart(fig_radar, width="stretch", key="chart_radar_national")

                rc1, rc2 = st.columns(2)
                with rc1:
                    st.markdown(f"**Sao Paulo** - Pop: {sp_pop}, Dens: {sp_dens} hab/km2")
                with rc2:
                    st.markdown(f"**Brasil** - Pop: {nat_pop}, Dens: {nat_dens} hab/km2")
            else:
                st.caption("Dados insuficientes para comparacao radar.")
        else:
            st.caption("Dados de comparacao nacional nao disponiveis.")
    except Exception as e:
        st.caption(f"Erro ao carregar comparacao: {e}")

    st.markdown("---")
    st.subheader("Insights Automaticos (Linguagem Natural)")
    from src.analytics.insights import generate_insights

    h3_data = load_h3_cells(city=selected_city)
    ibge_file = Path(f"data/external/ibge_stats_{selected_city}.json")
    ibge_summary = {}
    if ibge_file.exists():
        ibge_summary = json.loads(ibge_file.read_text())

    if h3_data:
        insights = generate_insights(h3_data, ibge_summary)
        for insight in insights:
            st.markdown(f"- {insight}")
    else:
        st.info("Execute o pipeline para gerar insights automaticos.")

    st.markdown("""
    ### Interpretacao das Cores

    - **Verde:** Baixa vulnerabilidade
    - **Amarelo:** Media vulnerabilidade
    - **Laranja:** Alta vulnerabilidade
    - **Vermelho:** Critico
    """)

    st.markdown("---")
    st.subheader("Exportar Relatorio")
    if st.button("Gerar Relatorio PDF", width="stretch", key="btn_pdf"):
        with st.spinner("Gerando relatorio..."):
            pdf_bytes = _generate_pdf_report(selected_city)
            if pdf_bytes:
                st.download_button(
                    label="Baixar Relatorio PDF",
                    data=pdf_bytes,
                    file_name=f"safestreet_{selected_city}_relatorio.pdf",
                    mime="application/pdf",
                    width="stretch",
                )
                st.success("Relatorio gerado com sucesso!")
            else:
                st.error("Erro ao gerar relatorio.")


def _generate_pdf_report(city: str) -> bytes | None:
    from pathlib import Path

    try:
        from fpdf import FPDF
    except ImportError:
        return None

    stats = load_city_stats(city)
    city_cfg = get_city(city)
    corr_data = load_correlation_data(city)

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 14)
            title = f"SafeStreet - Relatorio {city_cfg.name}"
            self.cell(0, 10, title, new_x="LMARGIN",
                      new_y="NEXT", align="C")
            self.set_font("Helvetica", "", 9)
            sub = "Pipeline de Inteligencia Espacial"
            self.cell(0, 6, sub, new_x="LMARGIN",
                      new_y="NEXT", align="C")
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.cell(0, 10, f"Pagina {self.page_no()}/{{nb}}", align="C")

    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "1. Resumo Geral", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, (
        f"Cidade: {city_cfg.name}\n"
        f"Ocorrencias noturnas: {int(stats.get('total_crimes', 0)):,}\n"
        f"Celulas H3 analisadas: {int(stats.get('total_cells', 0)):,}\n"
        f"Zonas de alto risco: {int(stats.get('high_risk', 0)):,}\n"
        f"Clusters Moran HH: {int(stats.get('moran_hh', 0)):,}"
    ))
    pdf.ln(3)

    ibge_file = Path(f"data/external/ibge_stats_{city}.json")
    if ibge_file.exists():
        ibge_data = json.loads(ibge_file.read_text())
        pop = ibge_data.get("populacao_2022", 0)
        if pop and pop > 0:
            total = int(stats.get("total_crimes", 0))
            rate = (total / pop) * 100_000
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "2. Sinistralidade", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, (
                f"Populacao (Censo 2022): {pop:,}\n"
                f"Total crimes: {total:,}\n"
                f"Taxa: {rate:.1f} crimes por 100 mil habitantes"
            ))
            pdf.ln(3)

    if corr_data:
        corr_df = pd.DataFrame(corr_data)
        corr_df = corr_df.apply(pd.to_numeric, errors="coerce")

        from src.analytics.statistics import (
            compute_correlation_matrix,
            run_ols_regression,
            train_risk_predictor,
            cluster_crime_patterns,
        )

        numeric_cols = [
            "crime_count", "lighting_density", "bus_stop_density",
            "metro_density", "camera_count", "nightlife_density",
            "dist_nearest_lit", "dist_nearest_metro", "vulnerability_score",
        ]
        available = [c for c in numeric_cols if c in corr_df.columns]

        corr_result = compute_correlation_matrix(corr_df, columns=available)
        if not corr_result["matrix"].empty:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "3. Correlacoes Principais (|r| > 0.15)", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)

            label_map = {
                "crime_count": "Crimes", "lighting_density": "Dens.Ilum",
                "bus_stop_density": "Dens.Onibus", "metro_density": "Dens.Metro",
                "camera_count": "Cameras", "nightlife_density": "Nightlife",
                "dist_nearest_lit": "Dist.Ilum", "dist_nearest_metro": "Dist.Metro",
                "vulnerability_score": "Vulnerab.",
            }
            cm = corr_result["matrix"]
            pv = corr_result["p_values"]
            pairs = []
            for i, c1 in enumerate(cm.columns):
                for j, c2 in enumerate(cm.columns):
                    if i < j:
                        r = cm.iloc[i, j]
                        p = pv.iloc[i, j]
                        if abs(r) > 0.15:
                            sig = (
                                "***" if p < 0.001
                                else "**" if p < 0.01
                                else "*" if p < 0.05
                                else ""
                            )
                            pairs.append((label_map.get(c1, c1), label_map.get(c2, c2), r, p, sig))
            pairs.sort(key=lambda x: abs(x[2]), reverse=True)
            for v1, v2, r, p, sig in pairs[:10]:
                pdf.multi_cell(0, 5, f"  {v1} x {v2}: r={r:.3f} (p={p:.4f}) {sig}")
            pdf.ln(3)

        ols_result = run_ols_regression(corr_df)
        if "error" not in ols_result:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "4. Regressao OLS", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, (
                f"R²: {ols_result['r_squared']:.4f} | "
                f"R² ajustado: {ols_result['adj_r_squared']:.4f} | "
                f"F-stat: {ols_result['f_statistic']:.4f} | "
                f"F p-value: {ols_result['f_p_value']:.2e}"
            ))
            pdf.ln(2)

            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, "Coeficientes:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            for name, info in ols_result["coefficients"].items():
                line = (
                    f"  {name}: coef={info['coef']:.4f}"
                    f" t={info['t_stat']:.4f}"
                    f" p={info['p_value']:.6f}"
                    f" {info['stars']}"
                )
                pdf.multi_cell(0, 5, line)
            pdf.ln(3)

        pred_result = train_risk_predictor(corr_df)
        if "error" not in pred_result:
            best = pred_result["best_model"]
            bm = pred_result["models"][best]
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "5. Modelo Preditivo", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, (
                f"Melhor modelo: {best}\n"
                f"R² teste: {bm['r2_test']:.4f} | RMSE: {bm['rmse']:.2f} | MAE: {bm['mae']:.2f}\n"
                f"R² CV (media±dp): {bm['r2_cv_mean']:.3f} ± {bm['r2_cv_std']:.3f}"
            ))
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, "Feature Importance:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            for fi in bm["feature_importance"][:5]:
                pdf.multi_cell(0, 5,
                    f"  {label_map.get(fi['feature'], fi['feature'])}: {fi['importance']:.4f}"
                )
            pdf.ln(3)

        cluster_result = cluster_crime_patterns(corr_df)
        if "error" not in cluster_result:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "6. Clusterizacao", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, (
                f"K-Means: {cluster_result['n_clusters_kmeans']} clusters | "
                f"Silhouette: {cluster_result['silhouette_score']:.3f}\n"
                f"DBSCAN: {cluster_result['n_clusters_dbscan']} clusters | "
                f"Pts. ruido: {cluster_result['n_noise_dbscan']}"
            ))
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, "Perfis dos Clusters:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            for name, info in cluster_result["centroids"].items():
                parts = [
                    f"{label_map.get(k, k)}={v:.2f}"
                    for k, v in info["means"].items()
                ]
                means_str = ", ".join(parts)
                line = f"  {name} (n={info['size']}): {means_str}"
                pdf.multi_cell(0, 5, line)
            pdf.ln(3)

    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 5,
        "\nRelatorio gerado automaticamente pelo SafeStreet Pipeline\n"
        "Dados: SSP-SP (2013-2019) | OpenStreetMap | GeoSampa | Open-Meteo | IBGE SIDRA"
    )

    return bytes(pdf.output())


def _render_advanced_tab(selected_city: str) -> None:
    st.subheader("Visualizacoes Avancadas")

    st.markdown("#### Sankey: Fluxo Crimes -> Risco -> Infraestrutura")
    nb_summary = load_neighborhood_crime_summary(selected_city)
    nb_gaps = load_neighborhood_infra_gaps(selected_city)

    if nb_summary and nb_gaps:
        gap_df = pd.DataFrame(nb_gaps)
        gap_df["risk_level"] = pd.cut(
            gap_df["total_crimes"],
            bins=[0, 50, 150, 500, float("inf")],
            labels=["Baixo", "Medio", "Alto", "Critico"],
        )
        gap_map = dict(zip(gap_df["neighborhood"], gap_df["risk_level"]))

        summary_df = pd.DataFrame(nb_summary)
        if not summary_df.empty:
            top_cats = summary_df.groupby("crime_category")["crime_count"].sum()
            top_cats = top_cats.nlargest(6).index.tolist()
            summary_df = summary_df[summary_df["crime_category"].isin(top_cats)]

            top_neigh = summary_df.groupby("neighborhood")["crime_count"].sum()
            top_neigh = top_neigh.nlargest(10).index.tolist()
            summary_df = summary_df[summary_df["neighborhood"].isin(top_neigh)]

            labels = []
            label_idx = {}

            for nb in summary_df["neighborhood"].unique():
                label_idx[nb] = len(labels)
                labels.append(nb)
            for cat in summary_df["crime_category"].unique():
                label_idx[f"C:{cat}"] = len(labels)
                labels.append(cat)
            risk_levels = ["Baixo", "Medio", "Alto", "Critico"]
            for r in risk_levels:
                label_idx[f"R:{r}"] = len(labels)
                labels.append(f"Risco {r}")

            sources, targets, values, link_colors = [], [], [], []
            risk_color_map = {
                "Baixo": "rgba(40,167,69,0.4)",
                "Medio": "rgba(255,193,7,0.4)",
                "Alto": "rgba(255,127,80,0.4)",
                "Critico": "rgba(220,53,69,0.4)",
            }
            for _, row in summary_df.iterrows():
                nb = row["neighborhood"]
                cat = row["crime_category"]
                cnt = row["crime_count"]
                risk = str(gap_map.get(nb, "Medio"))
                sources.append(label_idx[nb])
                targets.append(label_idx[f"C:{cat}"])
                values.append(cnt)
                link_colors.append("rgba(100,100,200,0.3)")

            for nb in summary_df["neighborhood"].unique():
                risk = str(gap_map.get(nb, "Medio"))
                nb_crimes = summary_df[summary_df["neighborhood"] == nb]["crime_count"].sum()
                nb_first_cat = (
                    summary_df[summary_df["neighborhood"] == nb]
                    ["crime_category"].iloc[0]
                )
                sources.append(label_idx[f"C:{nb_first_cat}"])
                targets.append(label_idx[f"R:{risk}"])
                values.append(nb_crimes)
                link_colors.append(risk_color_map.get(risk, "rgba(150,150,150,0.3)"))

            fig_sankey = go.Figure(go.Sankey(
                node=dict(
                    pad=15, thickness=20,
                    line=dict(color="black", width=0.5),
                    label=labels,
                    color="lightblue",
                ),
                link=dict(
                    source=sources, target=targets,
                    value=values, color=link_colors,
                ),
            ))
            fig_sankey.update_layout(height=450, margin={"t": 30})
            st.plotly_chart(fig_sankey, width="stretch", key="chart_sankey")
        else:
            st.info("Dados insuficientes para Sankey.")
    else:
        st.info("Dados insuficientes para Sankey.")

    st.markdown("---")
    st.markdown("#### Treemap: Bairros > Categorias > Naturezas")
    all_locs = load_crime_locations_filtered(selected_city)
    if all_locs:
        locs_df = pd.DataFrame(all_locs)
        if "neighborhood" in locs_df.columns and "crime_category" in locs_df.columns:
            locs_df = locs_df[
                locs_df["neighborhood"].notna()
                & (locs_df["neighborhood"] != "")
                & (locs_df["neighborhood"] != "nan")
            ]
            top_nb = locs_df["neighborhood"].value_counts().nlargest(15).index
            locs_df = locs_df[locs_df["neighborhood"].isin(top_nb)]

            if not locs_df.empty:
                treemap_data = locs_df.groupby(
                    ["neighborhood", "crime_category", "nature"]
                ).size().reset_index(name="count")
                treemap_data = treemap_data.sort_values("count", ascending=False)

                fig_treemap = px.treemap(
                    treemap_data,
                    path=["neighborhood", "crime_category", "nature"],
                    values="count",
                    color="count",
                    color_continuous_scale="YlOrRd",
                )
                fig_treemap.update_layout(height=550, margin={"t": 30})
                st.plotly_chart(fig_treemap, width="stretch", key="chart_treemap")
            else:
                st.info("Dados insuficientes para treemap.")
        else:
            st.info("Colunas necessarias nao disponiveis.")
    else:
        st.info("Nenhum dado de localizacao disponivel.")

    st.markdown("---")
    st.markdown("#### Network: Similaridade entre Bairros")
    nb_gaps_data = load_neighborhood_infra_gaps(selected_city)
    if nb_gaps_data and len(nb_gaps_data) > 2:
        import networkx as nx

        gdf_nb = pd.DataFrame(nb_gaps_data)
        numeric_cols = ["avg_lighting", "avg_bus", "avg_dist_lit", "avg_dist_bus"]
        available_nb = [c for c in numeric_cols if c in gdf_nb.columns]
        if available_nb:
            from sklearn.preprocessing import StandardScaler

            scaler = StandardScaler()
            features = scaler.fit_transform(gdf_nb[available_nb].fillna(0))

            G = nx.Graph()
            for i, (_, row) in enumerate(gdf_nb.iterrows()):
                G.add_node(row["neighborhood"], crimes=row["total_crimes"])

            threshold = 1.5
            edges_added = 0
            for i in range(len(gdf_nb)):
                for j in range(i + 1, len(gdf_nb)):
                    dist = float(np.linalg.norm(features[i] - features[j]))
                    if dist < threshold:
                        w = max(0, 1 - dist / threshold)
                        G.add_edge(
                            gdf_nb.iloc[i]["neighborhood"],
                            gdf_nb.iloc[j]["neighborhood"],
                            weight=w,
                        )
                        edges_added += 1

            if edges_added > 0:
                pos = nx.spring_layout(G, k=2, seed=42)
                edge_x, edge_y = [], []
                for e in G.edges():
                    x0, y0 = pos[e[0]]
                    x1, y1 = pos[e[1]]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])

                node_x = [pos[n][0] for n in G.nodes()]
                node_y = [pos[n][1] for n in G.nodes()]
                node_text = list(G.nodes())
                node_crimes = [G.nodes[n].get("crimes", 0) for n in G.nodes()]

                fig_net = go.Figure()
                fig_net.add_trace(go.Scatter(
                    x=edge_x, y=edge_y, mode="lines",
                    line=dict(width=0.5, color="gray"),
                ))
                fig_net.add_trace(go.Scatter(
                    x=node_x, y=node_y, mode="markers+text",
                    text=node_text, textposition="top center",
                    marker=dict(
                        size=[max(8, c * 0.3) for c in node_crimes],
                        color=node_crimes,
                        colorscale="YlOrRd",
                        colorbar=dict(title="Crimes"),
                    ),
                ))
                fig_net.update_layout(
                    height=500, margin={"t": 30, "b": 30, "l": 30, "r": 30},
                    showlegend=False,
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                )
                st.plotly_chart(fig_net, width="stretch", key="chart_network")
                st.caption(
                    f"Nos: {G.number_of_nodes()} bairros | "
                    f"Arestas: {G.number_of_edges()} conexoes (distancia < {threshold})"
                )
            else:
                st.info("Nenhuma conexao encontrada entre bairros.")
        else:
            st.info("Dados insuficientes para network graph.")
    else:
        st.info("Necessario pelo menos 3 bairros com dados.")


def main() -> None:
    try:
        from src.db.connection import engine
        from src.db.models import Base

        Base.metadata.create_all(engine)
    except Exception as e:
        logger.warning("Nao foi possivel criar tabelas: {}", e)

    _render_onboarding()

    result = _render_sidebar()
    selected_city, selected_year, selected_month = result[:3]
    selected_category, selected_neighborhood = result[3], result[4]
    _render_metrics(selected_city, selected_year, selected_month)

    tab_names = [
        "Mapa", "Temporal", "Heatmap", "Estatistica",
        "Analise", "Dados", "Avancado", "Sobre",
    ]
    tabs = st.tabs(tab_names)
    tab_map, tab_temporal, tab_heatmap = tabs[0], tabs[1], tabs[2]
    tab_stats, tab_analysis, tab_data = tabs[3], tabs[4], tabs[5]
    tab_adv, tab_about = tabs[6], tabs[7]

    with tab_map:
        _render_map_tab(selected_city, selected_year, selected_month,
                        selected_category, selected_neighborhood)
    with tab_temporal:
        _render_temporal_tab(selected_city, selected_year, selected_month)
    with tab_heatmap:
        _render_heatmap_tab(selected_city, selected_year, selected_month)
    with tab_stats:
        _render_statistics_tab(selected_city, selected_year, selected_month)
    with tab_analysis:
        _render_analysis_tab(selected_city, selected_year, selected_month)
    with tab_data:
        _render_data_tab(selected_city)
    with tab_adv:
        _render_advanced_tab(selected_city)
    with tab_about:
        _render_about_tab(selected_city)


if __name__ == "__main__":
    main()
