"""Download SSP-SP 2020+ via SPSafe dataset (Zenodo).

Usage:
    python scripts/download_ssp_sp_2020.py [--years 2020 2021 2022] [--merge]
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.ssp_sp import (
    download_spsafe_dataset,
    merge_ssp_datasets,
    normalize_spsafe_columns,
)
from src.utils.logger import setup_logger


def main() -> None:
    setup_logger(level="INFO")

    years = [2020, 2021, 2022]
    merge = False

    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--years" and i + 1 < len(args):
            years = [int(y) for y in args[i + 1].split(",")]
        if arg == "--merge":
            merge = True

    dest_dir = Path("data/raw/spsafe")
    dest_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Baixando SPSafe para anos: {}", years)
    extracted = download_spsafe_dataset(dest_dir, years=years)

    if not extracted:
        logger.error("Nenhum arquivo extraido do SPSafe")
        return

    for name, path in extracted.items():
        df = pd.read_csv(path, encoding="utf-8", low_memory=False)
        df = normalize_spsafe_columns(df)
        sp_mask = df["cidade"].str.upper().str.contains(
            "SAO PAULO|S.PAULO|SÃO PAULO", na=False,
        )
        sp_df = df[sp_mask]
        sp_df.to_csv(path, index=False)
        logger.info(
            "SPSafe {} (SP): {} de {} registros",
            name, len(sp_df), len(df),
        )

    if merge:
        existing = Path("data/raw/ssp_sp_crimes.csv")
        if existing.exists():
            logger.info("Mesclando com dados existentes...")
            merged = merge_ssp_datasets(existing, dest_dir, years=years)
            merged.to_csv(existing, index=False)
            logger.info(
                "Merge concluido: {} registros totais", len(merged),
            )
        else:
            logger.warning(
                "Arquivo {} nao encontrado para merge", existing,
            )

    logger.info("Download SSP-SP 2020+ concluido!")
