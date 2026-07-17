from __future__ import annotations

from typing import Any

import folium
import pandas as pd
from folium import plugins

from src.config import CityConfig

CATEGORY_COLORS = {
    "Violencia": "#dc3545",
    "Roubo/Furto": "#fd7e14",
    "Trafico/Armas": "#6f42c1",
    "Outros": "#6c757d",
}

CATEGORY_ICONS = {
    "Violencia": "exclamation-triangle",
    "Roubo/Furto": "warning",
    "Trafico/Armas": "bomb",
    "Outros": "info-sign",
}


def create_vulnerability_map(
    h3_data: list[dict[str, Any]],
    city_config: CityConfig | None = None,
    layers: dict[str, bool] | None = None,
    tiles: str = "cartodb darkmatter",
    crime_locations: list[dict[str, Any]] | None = None,
) -> folium.Map:
    if city_config:
        center_lat = city_config.center_lat
        center_lon = city_config.center_lon
        zoom = city_config.zoom_start
    else:
        center_lat = -8.0476
        center_lon = -34.8770
        zoom = 12

    layers = layers or {"h3": True, "lighting": True, "bus": True, "metro": True, "cameras": True}

    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles=tiles)

    df = pd.DataFrame(h3_data)

    if layers["h3"] and not df.empty and "h3_index" in df.columns:
        import h3 as h3_lib

        h3_group = folium.FeatureGroup(name="Celulas H3 (Vulnerabilidade)")

        for _, row in df.iterrows():
            try:
                boundary = h3_lib.cell_to_boundary(row["h3_index"])
                coords = [(lat, lng) for lat, lng in boundary]
            except Exception:
                continue

            score = row.get("vulnerability_score") or 0
            color = _score_color(score)
            moran = row.get("moran_cluster") or "N/A"

            popup_html = (
                f"<div style='font-family: monospace; font-size: 12px;'>"
                f"<b>H3:</b> {row['h3_index']}<br>"
                f"<b>Ocorrencias:</b> {row.get('crime_count', 0)}<br>"
                f"<b>Vulnerabilidade:</b> {score:.3f}<br>"
                f"<b>Dens. Iluminacao:</b> {(row.get('lighting_density') or 0):.2f}<br>"
                f"<b>Dens. Onibus:</b> {(row.get('bus_stop_density') or 0):.2f}<br>"
                f"<b>Dens. Metro:</b> {(row.get('metro_density') or 0):.2f}<br>"
                f"<b>Cameras:</b> {row.get('camera_count', 0)}<br>"
                f"<b>Dist. Luz (m):</b> {(row.get('dist_nearest_lit') or 0):.1f}<br>"
                f"<b>Dist. Onibus (m):</b> {(row.get('dist_nearest_bus') or 0):.1f}<br>"
                f"<b>Dist. Metro (m):</b> {(row.get('dist_nearest_metro') or 0):.1f}<br>"
                f"<b>Cluster Moran:</b> {moran}"
                f"</div>"
            )

            folium.Polygon(
                locations=coords,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.6,
                weight=1,
                popup=folium.Popup(popup_html, max_width=300),
            ).add_to(h3_group)

        h3_group.add_to(m)

    if crime_locations:
        crime_df = pd.DataFrame(crime_locations)
        if not crime_df.empty and "latitude" in crime_df.columns:
            for cat, color in CATEGORY_COLORS.items():
                cat_df = crime_df[crime_df["crime_category"] == cat]
                if cat_df.empty:
                    continue
                fg = folium.FeatureGroup(name=f"Crimes - {cat}")
                for _, row in cat_df.iterrows():
                    popup_html = (
                        f"<div style='font-family: monospace; font-size: 11px;'>"
                        f"<b>Tipo:</b> {cat}<br>"
                        f"<b>Natureza:</b> {row.get('nature', 'N/A')}<br>"
                        f"<b>Bairro:</b> {row.get('neighborhood', 'N/A')}<br>"
                        f"<b>Hora:</b> {row.get('time', 'N/A')}"
                        f"</div>"
                    )
                    folium.CircleMarker(
                        location=[row["latitude"], row["longitude"]],
                        radius=3,
                        color=color,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.6,
                        weight=1,
                        popup=folium.Popup(popup_html, max_width=250),
                    ).add_to(fg)
                fg.add_to(m)

    plugins.Fullscreen().add_to(m)
    plugins.MousePosition().add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    legend_html = (
        '<div style="position:fixed;bottom:30px;left:30px;z-index:1000;'
        "background:rgba(0,0,0,0.7);padding:10px;border-radius:5px;"
        'font-family:monospace;font-size:12px;">'
        "<b>Vulnerabilidade</b><br>"
        '<i style="background:#28a745;width:12px;height:12px;'
        'display:inline-block;"></i> Baixa (0-0.2)<br>'
        '<i style="background:#ffc107;width:12px;height:12px;'
        'display:inline-block;"></i> Media (0.2-0.4)<br>'
        '<i style="background:#fd7e14;width:12px;height:12px;'
        'display:inline-block;"></i> Alta (0.4-0.7)<br>'
        '<i style="background:#dc3545;width:12px;height:12px;'
        'display:inline-block;"></i> Critica (0.7+)<br>'
        "<br><b>Crimes</b><br>"
        '<i style="background:#dc3545;width:12px;height:12px;'
        'display:inline-block;border-radius:50%;"></i> Violencia<br>'
        '<i style="background:#fd7e14;width:12px;height:12px;'
        'display:inline-block;border-radius:50%;"></i> Roubo/Furto<br>'
        '<i style="background:#6f42c1;width:12px;height:12px;'
        'display:inline-block;border-radius:50%;"></i> Trafico/Armas<br>'
        '<i style="background:#6c757d;width:12px;height:12px;'
        'display:inline-block;border-radius:50%;"></i> Outros'
        "</div>"
    )
    m.get_root().html.add_child(folium.Element(legend_html))

    return m


def _score_color(score: float) -> str:
    if score >= 0.7:
        return "#dc3545"
    if score >= 0.4:
        return "#fd7e14"
    if score >= 0.2:
        return "#ffc107"
    return "#28a745"
