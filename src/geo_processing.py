from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from src.pipeline_etl import run_pipeline
from src.utils.logger import setup_logger


def run_geo_processing(city_key: str = "recife", crime_file: Path | None = None) -> None:
    logger.info("=" * 60)
    logger.info("SafeStreet - Modulo de Processamento Geoespacial")
    logger.info("=" * 60)

    run_pipeline(city_key, crime_file)

    logger.info("Processamento geoespacial concluido com sucesso")
    logger.info("=" * 60)


if __name__ == "__main__":
    setup_logger(level="DEBUG" if "--debug" in sys.argv else "INFO")
    city = "recife"
    crime_file = None
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--city" and i + 1 < len(args):
            city = args[i + 1]
        if arg == "--input" and i + 1 < len(args):
            crime_file = Path(args[i + 1])
    run_geo_processing(city, crime_file)
