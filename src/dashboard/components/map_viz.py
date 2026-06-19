from __future__ import annotations

from typing import Any

import folium
import pandas as pd
from folium import plugins


def create_vulnerability_map(
    h3_data: list[dict[str, Any]],
    tiles: str = "cartodb darkmatter",
) -> folium.Map:
    center_lat = -8.0476
    center_lon = -34.8770

    m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles=tiles)

    df = pd.DataFrame(h3_data)

    if not df.empty and "h3_index" in df.columns:
        from h3 import h3_to_geo_boundary

        for _, row in df.iterrows():
            boundary = h3_to_geo_boundary(row["h3_index"])
            coords = [(lat, lng) for lat, lng in boundary]

            score = row.get("vulnerability_score", 0)
            color = _score_color(score)

            folium.Polygon(
                locations=coords,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.6,
                weight=1,
                popup=folium.Popup(
                    f"<b>H3:</b> {row['h3_index']}<br>"
                    f"<b>Crimes:</b> {row.get('crime_count', 0)}<br>"
                    f"<b>Vulnerabilidade:</b> {score:.3f}<br>"
                    f"<b>Cluster Moran:</b> {row.get('moran_cluster', 'N/A')}"
                ),
            ).add_to(m)

    plugins.Fullscreen().add_to(m)
    plugins.MousePosition().add_to(m)

    return m


def _score_color(score: float) -> str:
    if score >= 0.7:
        return "#dc3545"
    if score >= 0.4:
        return "#fd7e14"
    if score >= 0.2:
        return "#ffc107"
    return "#28a745"
