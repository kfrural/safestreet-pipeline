from __future__ import annotations

import json
from pathlib import Path

import requests
from loguru import logger

SIDRA_BASE = "https://apisidra.ibge.gov.br/values"
SAO_PAULO_IBGE = "3550308"

RENTAL_TABLES = {
    "income_per_capita": {
        "table": "10295",
        "vars": "13431,13534",
        "desc": "Rendimento mensal per capita medio e mediano (Censo 2022)",
    },
    "household_income": {
        "table": "9514",
        "vars": "93",
        "classifications": "c2/0/c287/0",
        "desc": "Populacao por sexo e idade (Censo 2022) - proxy de estrutura etaria",
    },
}


def _fetch_sidra_table(
    table: str,
    municipality: str,
    variables: str,
    period: str = "last",
    classifications: str | None = None,
) -> list[dict]:
    parts = [f"t/{table}", f"n6/{municipality}", f"v/{variables}", f"p/{period}"]
    if classifications:
        parts.append(classifications)
    url = f"{SIDRA_BASE}/{'/'.join(parts)}"

    logger.info("IBGE SIDRA rental: {}", url)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("Erro IBGE SIDRA rental: {}", e)
        return []

    if len(data) < 2:
        return []

    header = data[0]
    records = []
    for row in data[1:]:
        record = {}
        for key, val in row.items():
            if key == "NC":
                continue
            h_name = header.get(key, key)
            record[h_name] = val
        records.append(record)

    return records


def fetch_rental_data(cache_dir: Path | None = None) -> dict:
    cache_path = cache_dir / "rental_sao_paulo.json" if cache_dir else None

    if cache_path and cache_path.exists():
        logger.info("Carregando dados de aluguel do cache: {}", cache_path)
        return json.loads(cache_path.read_text())

    indicators = {}

    for name, cfg in RENTAL_TABLES.items():
        data = _fetch_sidra_table(
            cfg["table"],
            SAO_PAULO_IBGE,
            cfg["vars"],
            classifications=cfg.get("classifications"),
        )
        if data:
            indicators[name] = data
            logger.info("IBGE {}: {} registros", name, len(data))

    if cache_dir and indicators:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(indicators, default=str, ensure_ascii=False))
        logger.info("Dados de aluguel salvos: {}", cache_path)

    return indicators


def compute_rental_summary(indicators: dict) -> dict:
    summary: dict = {}

    if "income_per_capita" in indicators and indicators["income_per_capita"]:
        income_data = indicators["income_per_capita"]
        for item in income_data:
            var_name = item.get("Variavel", item.get("D2N", ""))
            val_str = item.get("Valor", "0")
            try:
                val = float(str(val_str).replace(",", "."))
            except (ValueError, TypeError):
                continue
            if "medio" in var_name.lower():
                summary["avg_monthly_income"] = round(val, 2)
            elif "mediano" in var_name.lower():
                summary["median_monthly_income"] = round(val, 2)

    if "household_income" in indicators and indicators["household_income"]:
        hh_data = indicators["household_income"]
        total_pop = 0
        for item in hh_data:
            val_str = item.get("Valor", "0")
            try:
                val = float(str(val_str).replace(",", "."))
                total_pop += val
            except (ValueError, TypeError):
                continue
        if total_pop > 0:
            summary["population_2022"] = int(total_pop)

    return summary


def get_rental_summary_for_city(
    city_key: str,
    cache_dir: Path | None = None,
) -> dict:
    if city_key != "sao-paulo":
        logger.warning("Dados de aluguel disponiveis apenas para Sao Paulo")
        return {}

    indicators = fetch_rental_data(cache_dir)
    return compute_rental_summary(indicators)
