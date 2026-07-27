from __future__ import annotations

import statistics as _stats


def compute_confidence_score(
    crime_count: int,
    infra_features: dict,
    years_of_data: int = 1,
) -> float:
    crime_score = min(crime_count / 50, 1.0) * 40

    infra_keys = [
        "lighting_density",
        "bus_stop_density",
        "camera_count",
        "nightlife_density",
    ]
    infra_count = sum(1 for k in infra_keys if (infra_features.get(k) or 0) > 0)
    infra_score = (infra_count / len(infra_keys)) * 30

    year_score = min(years_of_data / 7, 1.0) * 30

    return round(crime_score + infra_score + year_score, 1)


def classify_confidence(score: float) -> str:
    if score >= 80:
        return "Alta"
    if score >= 50:
        return "Media"
    return "Baixa"


def generate_insights(
    h3_data: list[dict],
    ibge_summary: dict,
    sinistralidade: dict | None = None,
) -> list[str]:
    if not h3_data:
        return ["Sem dados suficientes para gerar insights."]

    insights: list[str] = []

    total_crimes = sum(c.get("crime_count", 0) for c in h3_data)
    avg_crimes = total_crimes / len(h3_data) if h3_data else 0

    high_risk = [c for c in h3_data if (c.get("crime_count") or 0) > avg_crimes * 2]
    if high_risk:
        insights.append(
            f"{len(high_risk)} celulas H3 concentram mais de 2x a media de crimes "
            f"({avg_crimes:.1f}/celula), totalizando "
            f"{sum(c.get('crime_count', 0) for c in high_risk)} ocorrencias."
        )

    low_lit_cells = [
        c for c in h3_data
        if (c.get("crime_count") or 0) > avg_crimes
        and (c.get("lighting_density") or 0) < 0.001
    ]
    if low_lit_cells:
        pct = len(low_lit_cells) / len(h3_data) * 100
        insights.append(
            f"{pct:.1f}% das celulas com alta criminalidade possuem baixa "
            f"densidade de iluminacao, sugerindo deficit de infraestrutura."
        )

    camera_rich = [
        c for c in h3_data
        if (c.get("camera_count") or 0) > 0
        and (c.get("crime_count") or 0) > avg_crimes
    ]
    if camera_rich:
        insights.append(
            f"{len(camera_rich)} celulas possuem cameras mas mesmo assim "
            f"registram crime acima da media, indicando que a presenca de "
            f"cameras nao e suficiente para reduzir a criminalidade."
        )

    nightlife_risk = [
        c for c in h3_data
        if (c.get("nightlife_density") or 0) > 0.005
        and (c.get("crime_count") or 0) > avg_crimes * 1.5
    ]
    if nightlife_risk:
        insights.append(
            f"{len(nightlife_risk)} celulas com alta densidade de nightlife "
            f"apresentam criminalidade 50% acima da media, sugerindo correlacao "
            f"entre vida noturna e risco."
        )

    pop = ibge_summary.get("populacao_2022") or ibge_summary.get("populacao")
    if pop and total_crimes:
        try:
            pop_num = float(str(pop).replace(".", "").replace(",", "."))
            sinistralidade = total_crimes / pop_num * 100_000
            insights.append(
                f"Indice de sinistralidade estimado: {sinistralidade:.1f} "
                f"crimes por 100 mil habitantes (Censo 2022: {pop} hab)."
            )
        except (ValueError, TypeError):
            pass

    vuln_scores = [
        c.get("vulnerability_score", 0)
        for c in h3_data
        if c.get("vulnerability_score") is not None
    ]
    if vuln_scores:
        avg_vuln = _stats.mean(vuln_scores)
        high_vuln = [s for s in vuln_scores if s > avg_vuln * 1.5]
        insights.append(
            f"Score de vulnerabilidade medio: {avg_vuln:.3f}. "
            f"{len(high_vuln)} celulas estao 50% acima da media."
        )

    return insights if insights else ["Nenhum insight significativo identificado."]
