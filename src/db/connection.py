from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from loguru import logger

try:
    try:
        from sqlalchemy.engine import Engine
    except ImportError:
        from sqlalchemy import Engine
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import SQLAlchemyError
    _SQLA_AVAILABLE = True
except Exception as e:
    _SQLA_AVAILABLE = False
    Engine = Any  # type: ignore
    SQLAlchemyError = Exception  # type: ignore
    logger.warning("SQLAlchemy indisponivel: {}", e)

from src.config import settings

_engine: Any | None = None


def create_db_engine() -> Any | None:
    if not _SQLA_AVAILABLE:
        return None
    try:
        logger.info("Conectando ao banco: {}", settings.postgres_host)
        return create_engine(
            settings.database_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
    except Exception as e:
        logger.warning("Nao foi possivel inicializar conexao com banco: {}", e)
        return None


def get_engine() -> Any | None:
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine


class _LazyEngineProxy:
    def __getattr__(self, name: str) -> Any:
        eng = get_engine()
        if eng is None:
            raise RuntimeError("Banco de dados nao configurado ou indisponivel.")
        return getattr(eng, name)


engine = _LazyEngineProxy()


@contextmanager
def get_connection() -> Generator[Any, None, None]:
    eng = get_engine()
    if eng is None:
        raise RuntimeError("Banco de dados nao configurado ou indisponivel.")
    conn = eng.connect()
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
        eng = get_engine()
        if eng is None:
            return False
        with get_connection() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Conexão com banco OK")
        return True
    except Exception as e:
        logger.info("Banco offline ou nao configurado: {}", e)
        return False
