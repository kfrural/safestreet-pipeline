from __future__ import annotations

import json
from pathlib import Path

import requests
from loguru import logger

SIDRA_BASE = "https://apisidra.ibge.gov.br/values"
SAO_PAULO_IBGE = "3550308"

TABLES = {
    "population": {
        "table": "4714",
        "vars": "93,6318,614",
        "desc": "Populacao, Area, Densidade (Censo 2022)",
    },
    "pop_estimate": {
        "table": "6579",
        "vars": "9324",
        "desc": "Estimativa populacional (2001-2025)",
    },
    "literacy": {
        "table": "9543",
        "vars": "2513",
        "classifications": "c2/6794/c86/95251/c287/100362",
        "desc": "Taxa de alfabetizacao 15+ anos (Censo 2022)",
    },
    "age_pyramid": {
        "table": "9514",
        "vars": "93",
        "classifications": "c2/0/c287/0/c286/0",
        "desc": "Populacao por sexo e idade (Censo 2022)",
    },
    "households": {
        "table": "1434",
        "vars": "96,137",
        "desc": "Domicilios e moradores (Censo 2010)",
    },
    "households_income": {
        "table": "3261",
        "vars": "96",
        "desc": "Domicilios por classe de renda (Censo 2010)",
    },
    "race": {
        "table": "9605",
        "vars": "93",
        "classifications": "c86/0",
        "desc": "Populacao por cor/raça (Censo 2022)",
    },
}


def _fetch_sidra(
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

    logger.info("IBGE SIDRA: {}", url)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("Erro IBGE SIDRA: {}", e)
        return []

    if len(data) < 2:
        return []

    header = data[0]
    rows = data[1:]

    records = []
    for row in rows:
        record = {}
        for key, val in row.items():
            if key == "NC":
                continue
            h_name = header.get(key, key)
            record[h_name] = val
        records.append(record)

    return records


def _fetch_sidra_national(
    table: str,
    variables: str,
    period: str = "last",
    classifications: str | None = None,
) -> list[dict]:
    parts = [f"t/{table}", "n1/0", f"v/{variables}", f"p/{period}"]
    if classifications:
        parts.append(classifications)
    url = f"{SIDRA_BASE}/{'/'.join(parts)}"

    logger.info("IBGE SIDRA nacional: {}", url)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("Erro IBGE SIDRA nacional: {}", e)
        return []

    if len(data) < 2:
        return []

    header = data[0]
    rows = data[1:]

    records = []
    for row in rows:
        record = {}
        for key, val in row.items():
            if key == "NC":
                continue
            h_name = header.get(key, key)
            record[h_name] = val
        records.append(record)

    return records


def fetch_ibge_indicators(cache_dir: Path | None = None) -> dict:
    cache_path = cache_dir / "ibge_sao_paulo.json" if cache_dir else None

    if cache_path and cache_path.exists():
        logger.info("Carregando indicadores IBGE do cache: {}", cache_path)
        return json.loads(cache_path.read_text())

    indicators = {}

    pop_data = _fetch_sidra(
        TABLES["population"]["table"],
        SAO_PAULO_IBGE,
        TABLES["population"]["vars"],
    )
    if pop_data:
        indicators["population"] = pop_data
        logger.info("IBGE populacao: {}", pop_data)

    est_data = _fetch_sidra(
        TABLES["pop_estimate"]["table"],
        SAO_PAULO_IBGE,
        TABLES["pop_estimate"]["vars"],
        period="all",
    )
    if est_data:
        indicators["population_estimate"] = est_data
        logger.info("IBGE estimativa populacional: {} registros", len(est_data))

    lit_data = _fetch_sidra(
        TABLES["literacy"]["table"],
        SAO_PAULO_IBGE,
        TABLES["literacy"]["vars"],
        classifications=TABLES["literacy"]["classifications"],
    )
    if lit_data:
        indicators["literacy"] = lit_data
        logger.info("IBGE alfabetizacao: {}", lit_data)

    age_data = _fetch_sidra(
        TABLES["age_pyramid"]["table"],
        SAO_PAULO_IBGE,
        TABLES["age_pyramid"]["vars"],
        classifications=TABLES["age_pyramid"]["classifications"],
        period="last",
    )
    if age_data:
        indicators["age_pyramid"] = age_data
        logger.info("IBGE piramide etaria: {} registros", len(age_data))

    hh_data = _fetch_sidra(
        TABLES["households"]["table"],
        SAO_PAULO_IBGE,
        TABLES["households"]["vars"],
    )
    if hh_data:
        indicators["households"] = hh_data
        logger.info("IBGE domicilios: {}", hh_data)

    race_data = _fetch_sidra(
        TABLES["race"]["table"],
        SAO_PAULO_IBGE,
        TABLES["race"]["vars"],
        classifications=TABLES["race"]["classifications"],
    )
    if race_data:
        indicators["race"] = race_data
        logger.info("IBGE cor/raça: {}", race_data)

    inc_data = _fetch_sidra(
        TABLES["households_income"]["table"],
        SAO_PAULO_IBGE,
        TABLES["households_income"]["vars"],
    )
    if inc_data:
        indicators["income_classes"] = inc_data
        logger.info("IBGE classes de renda: {}", inc_data)

    if cache_dir and indicators:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(indicators, default=str, ensure_ascii=False))
        logger.info("Indicadores IBGE salvos: {}", cache_path)

    return indicators


def compute_ibge_summary(indicators: dict) -> dict:
    summary = {
        "municipio": "Sao Paulo (SP)",
        "codigo_ibge": SAO_PAULO_IBGE,
    }

    if "population" in indicators and indicators["population"]:
        pop = indicators["population"][0]
        summary["populacao_2022"] = pop.get("Populacao residente", pop.get("V", ""))
        summary["area_km2"] = pop.get("Area da unidade territorial (quilometros quadrados)", "")
        summary["densidade_demografica"] = pop.get(
            "Densidade demografica (habitante por kilometro quadrado)", ""
        )

    if "literacy" in indicators and indicators["literacy"]:
        lit = indicators["literacy"][0]
        summary["taxa_alfabetizacao_15plus"] = lit.get("Taxa de alfabetizacao", "")

    if "households" in indicators and indicators["households"]:
        hh = indicators["households"][0]
        summary["domicilios_2010"] = hh.get("Domicilios particulares permanentes", "")
        summary["moradores_2010"] = hh.get("Moradores em domicilios particulares permanentes", "")

    if "population_estimate" in indicators["population_estimate"]:
        estimates = indicators["population_estimate"]
        latest = max(estimates, key=lambda x: x.get("Periodo", ""))
        summary["estimativa_pop_2025"] = latest.get("Valor", "")
        summary["estimativa_ano"] = latest.get("Periodo", "")

    return summary


def get_ibge_summary_for_city(
    city_key: str,
    cache_dir: Path | None = None,
) -> dict:
    if city_key != "sao-paulo":
        logger.warning("IBGE: dados disponiveis apenas para Sao Paulo")
        return {}

    indicators = fetch_ibge_indicators(cache_dir)
    return compute_ibge_summary(indicators)


NATIONAL_LEVEL = "0"


def fetch_national_indicators(cache_dir: Path | None = None) -> dict:
    cache_path = cache_dir / "ibge_national.json" if cache_dir else None

    if cache_path and cache_path.exists():
        return json.loads(cache_path.read_text())

    indicators = {}

    pop_data = _fetch_sidra_national(
        TABLES["population"]["table"],
        TABLES["population"]["vars"],
    )
    if pop_data:
        indicators["population"] = pop_data

    lit_data = _fetch_sidra_national(
        TABLES["literacy"]["table"],
        TABLES["literacy"]["vars"],
        classifications=TABLES["literacy"]["classifications"],
    )
    if lit_data:
        indicators["literacy"] = lit_data

    inc_data = _fetch_sidra_national(
        TABLES["households_income"]["table"],
        TABLES["households_income"]["vars"],
    )
    if inc_data:
        indicators["income_classes"] = inc_data

    if cache_dir and indicators:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(indicators, default=str, ensure_ascii=False))

    return indicators


def compute_national_summary(indicators: dict) -> dict:
    summary: dict = {}

    if "population" in indicators and indicators["population"]:
        pop = indicators["population"][0]
        summary["populacao"] = pop.get("Populacao residente", pop.get("V", ""))
        summary["area_km2"] = pop.get("Area da unidade territorial (quilometros quadrados)", "")
        summary["densidade"] = pop.get(
            "Densidade demografica (habitante por kilometro quadrado)", ""
        )

    if "literacy" in indicators and indicators["literacy"]:
        lit = indicators["literacy"][0]
        summary["taxa_alfabetizacao"] = lit.get("Taxa de alfabetizacao", "")

    return summary


def get_national_comparison(cache_dir: Path | None = None) -> dict:
    national = fetch_national_indicators(cache_dir)
    sp = fetch_ibge_indicators(cache_dir)

    nat_summary = compute_national_summary(national)
    sp_summary = compute_ibge_summary(sp)

    return {
        "nacional": nat_summary,
        "sao_paulo": {
            "populacao": sp_summary.get("populacao_2022"),
            "densidade": sp_summary.get("densidade_demografica"),
            "taxa_alfabetizacao": sp_summary.get("taxa_alfabetizacao_15plus"),
        },
    }
