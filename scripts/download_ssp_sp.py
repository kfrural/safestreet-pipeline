from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

LABCIDADE_URL = (
    "https://raw.githubusercontent.com/labcidade/boletins-ssp/"
    "master/Compila%C3%A7%C3%A3o%20de%20boletins%20de%20ocorr%C3%AAncia%"
    "20registrados%20pela%20SSP/MDIP_2013-19.csv"
)


def download_labcidade(output_path: Path) -> Path:
    print("Baixando dados SSP-SP de labcidade/boletins-ssp...")
    resp = requests.get(LABCIDADE_URL, timeout=120)
    resp.raise_for_status()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(resp.content)
    print(f"  -> {len(resp.content):,} bytes salvos em {output_path}")
    return output_path


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    col_map = {}
    for col in df.columns:
        c = col.strip().replace("\ufeff", "")
        if c == "LATITUDE":
            col_map[col] = "latitude"
        elif c == "LONGITUDE":
            col_map[col] = "longitude"
        elif c == "DATAOCORRENCIA":
            col_map[col] = "data"
        elif c == "HORAOCORRENCIA":
            col_map[col] = "horario"
        elif c == "NUM_BO":
            col_map[col] = "num_bo"
        elif c == "CIDADE":
            col_map[col] = "cidade"
        elif c == "BAIRRO":
            col_map[col] = "bairro"
        elif c == "LOGRADOURO":
            col_map[col] = "endereco"
        elif c == "RUBRICA":
            col_map[col] = "natureza"
        elif c == "DELEGACIA_NOME":
            col_map[col] = "delegacia"
        elif c == "ESPECIE":
            col_map[col] = "especie"
        elif c == "ANO_BO":
            col_map[col] = "ano_bo"

    df = df.rename(columns=col_map)

    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce", dayfirst=True)

    if "horario" in df.columns:
        df["horario"] = df["horario"].astype(str).str[:5]

    for c in ("latitude", "longitude"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "."), errors="coerce")

    return df


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Download dados SSP-SP")
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument(
        "--city-filter",
        type=str,
        default="S.PAULO",
        help="Filtrar por cidade (CIDADE). Use 'all' para todas.",
    )
    args = parser.parse_args()

    output_dir = Path("data/raw")
    csv_path = output_dir / "mdip_2013_19.csv"

    if not csv_path.exists():
        download_labcidade(csv_path)

    print(f"Carregando {csv_path}...")
    df = pd.read_csv(csv_path, sep=";", encoding="latin-1", low_memory=False)
    df.columns = [c.strip().replace("\ufeff", "") for c in df.columns]
    df = normalize_columns(df)
    print(f"Total de registros: {len(df)}")

    if args.city_filter.lower() != "all" and "cidade" in df.columns:
        df = df[df["cidade"] == args.city_filter]
        print(f"Filtro cidade={args.city_filter}: {len(df)} registros")

    if "latitude" in df.columns and "longitude" in df.columns:
        valid = df["latitude"].notna() & df["longitude"].notna()
        print(f"Com coordenadas: {valid.sum()}/{len(df)}")

    out = Path(args.output) if args.output else output_dir / "ssp_sp_crimes.csv"
    df.to_csv(out, index=False)
    print(f"Salvo: {out} ({len(df)} registros)")


if __name__ == "__main__":
    main()
