from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger


def load_csv(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    logger.info("Carregando dados de {}", path)
    df = pd.read_csv(path, **kwargs)
    logger.info("Registros carregados: {}", len(df))
    return df


def load_excel(path: str | Path, sheet_name: str = "Sheet1", **kwargs: Any) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    logger.info("Carregando planilha {} de {}", sheet_name, path)
    df = pd.read_excel(path, sheet_name=sheet_name, **kwargs)
    logger.info("Registros carregados: {}", len(df))
    return df


def load_dataframe(
    path: str | Path,
    file_type: str | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    path = Path(path)
    ext = file_type or path.suffix.lower()

    loaders = {
        ".csv": load_csv,
        ".xlsx": load_excel,
        ".xls": load_excel,
    }

    loader = loaders.get(ext)
    if loader is None:
        raise ValueError(f"Formato não suportado: {ext}")

    return loader(path, **kwargs)
