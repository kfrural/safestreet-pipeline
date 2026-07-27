from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.data.ingestion import load_csv, load_dataframe


def test_load_csv(tmp_path: Path) -> None:
    file_path = tmp_path / "test.csv"
    pd.DataFrame({"a": [1, 2, 3]}).to_csv(file_path, index=False)
    df = load_csv(file_path)
    assert len(df) == 3


def test_load_csv_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        load_csv(Path("/nonexistent/file.csv"))


def test_load_dataframe_invalid_extension(tmp_path: Path) -> None:
    file_path = tmp_path / "test.xyz"
    file_path.touch()
    with pytest.raises(ValueError, match="não suportado"):
        load_dataframe(file_path)
