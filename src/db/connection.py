from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from loguru import logger
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from src.config import settings


def create_db_engine() -> Engine:
    logger.info("Conectando ao banco: {}", settings.postgres_host)
    return create_engine(
        settings.database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


engine = create_db_engine()


@contextmanager
def get_connection() -> Generator[Any, None, None]:
    conn = engine.connect()
    try:
        yield conn
        conn.commit()
    except SQLAlchemyError as e:
        conn.rollback()
        logger.error("Erro de banco de dados: {}", e)
        raise
    finally:
        conn.close()


def check_connection() -> bool:
    try:
        with get_connection() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Conexão com banco OK")
        return True
    except SQLAlchemyError as e:
        logger.error("Falha na conexão: {}", e)
        return False
