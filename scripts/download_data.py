from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
import requests

CKAN_BASE = "https://dados.recife.pe.gov.br"
DATASET_ID = "acidentes-de-transito-com-e-sem-vitimas"

RESOURCE_IDS: dict[int, str] = {
    2024: "87ac4237-f5f9-44d2-bcf1-927aaa0a2d31",
    2023: "dbb9165a-7539-4fdd-943a-acffe12df3e0",
    2022: "c2281788-2e8c-472c-8812-67c4f85e9272",
    2021: "31ee35d9-6f8e-4694-9492-efe96e902b07",
    2020: "b2594588-2aa8-42c4-b96d-246102ecde3c",
    2019: "c9fe4a98-0f61-4e81-9c4b-a22f8dc6f1a2",
    2018: "a7b72334-9229-4e52-a6cb-8006de4942e3",
    2017: "d364e034-7e00-41a7-b557-0b16c21814e7",
    2016: "edc820d6-0f01-4fd2-b8a4-5a8c95f7e743",
    2015: "58816e1f-18bc-4335-82bf-80ff080cb0e5",
}


def download_via_ckan_api(resource_id: str, limit: int | None = None) -> pd.DataFrame:
    url = f"{CKAN_BASE}/api/3/action/datastore_search"
    params: dict[str, int | str] = {"resource_id": resource_id, "limit": limit or 10000}
    all_records: list[dict] = []

    while True:
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        records = data["result"]["records"]
        all_records.extend(records)
        if len(records) < (limit or 10000) or limit:
            break
        params["offset"] = params.get("offset", 0) + len(records)

    df = pd.DataFrame(all_records)
    if "_id" in df.columns:
        df = df.drop(columns=["_id"])
    return df


def download_via_csv_url(year: int) -> pd.DataFrame:
    url = f"{CKAN_BASE}/dataset/{DATASET_ID}/resource/{RESOURCE_IDS[year]}/download/acidentes-de-transito-{year}.csv"
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    return pd.read_csv(io.StringIO(resp.text), sep=";", low_memory=False)


def main() -> None:
    years = [int(y) for y in sys.argv[1:]] if len(sys.argv) > 1 else [2024]
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    for year in years:
        if year not in RESOURCE_IDS:
            print(f"Ano {year} não disponível. Anos disponíveis: {sorted(RESOURCE_IDS.keys())}")
            continue

        output_path = output_dir / f"acidentes_transito_recife_{year}.csv"
        if output_path.exists():
            print(f"Arquivo já existe: {output_path}")
            continue

        print(f"Baixando dados de {year}...")
        try:
            df = download_via_ckan_api(RESOURCE_IDS[year])
        except Exception:
            print("Fallback para download direto via CSV...")
            df = download_via_csv_url(year)

        df.to_csv(output_path, index=False)
        print(f"Salvo: {output_path} ({len(df)} registros)")


if __name__ == "__main__":
    main()
