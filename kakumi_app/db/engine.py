"""
KAKUMI — Database engine wrapper.

Provides DATABASE_URL resolution and a thin wrapper over
sqlalchemy.create_engine with configurable pool settings.

Singleton pattern: module-level _engine_instance ensures one engine
per process. Lazy init on first .get_engine() call.
"""

import os
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.pool import NullPool, QueuePool


def get_db_url() -> str:
    """Return DATABASE_URL from env, or ``sqlite:///kakumi.db`` fallback.

    Resolution chain:
    1. ``os.getenv("DATABASE_URL")`` — if non-empty, return as-is.
    2. Fallback: ``"sqlite:///kakumi.db"``.

    Empty string (``""``) is treated as unset —→ SQLite fallback.
    """
    url = os.getenv("DATABASE_URL", "").strip()
    return url or "sqlite:///kakumi.db"


def is_sqlite_url(url: str) -> bool:
    """Return ``True`` if *url* is a SQLite dialect."""
    return url.startswith("sqlite")


_engine_instance: Optional[sa.Engine] = None


class DatabaseEngine:
    """Thin wrapper over ``sqlalchemy.create_engine`` with pool configuration.

    Parameters
    ----------
    url : str, optional
        Database URL. Defaults to :func:`get_db_url`.
    pool_size : int
        Pool size for PostgreSQL (ignored for SQLite). Default 5.
    echo : bool
        Echo SQL statements. Default False.
    pool_timeout : int
        Pool timeout seconds for PostgreSQL (ignored for SQLite). Default 30.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        pool_size: int = 5,
        echo: bool = False,
        pool_timeout: int = 30,
    ):
        self.url = url or get_db_url()
        self.pool_size = pool_size
        self.echo = echo
        self.pool_timeout = pool_timeout
        self._engine: Optional[sa.Engine] = None

    @property
    def is_postgres(self) -> bool:
        """``True`` when URL starts with ``postgresql``."""
        return self.url.startswith("postgresql")

    def get_engine(self) -> sa.Engine:
        """Return cached engine, creating it lazily on first call."""
        if self._engine is None:
            kwargs: dict[str, object] = {
                "url": self.url,
                "echo": self.echo,
            }
            if self.is_postgres:
                kwargs["pool_size"] = self.pool_size
                kwargs["pool_timeout"] = self.pool_timeout
                kwargs["poolclass"] = QueuePool
            else:
                kwargs["poolclass"] = NullPool

            self._engine = sa.create_engine(**kwargs)  # type: ignore[arg-type]
        return self._engine

    def dispose(self) -> None:
        """Dispose engine. Safe to call multiple times."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None


def get_global_engine(
    url: Optional[str] = None,
    pool_size: int = 5,
    echo: bool = False,
    pool_timeout: int = 30,
) -> sa.Engine:
    """Return singleton engine for the process.

    Tests call :func:`reset_engine` then this again to create a fresh
    engine per test.
    """
    global _engine_instance
    if _engine_instance is None:
        eng = DatabaseEngine(
            url=url,
            pool_size=pool_size,
            echo=echo,
            pool_timeout=pool_timeout,
        )
        _engine_instance = eng.get_engine()
    return _engine_instance


def reset_engine() -> None:
    """Dispose and reset the singleton engine. Used by conftest."""
    global _engine_instance
    if _engine_instance is not None:
        _engine_instance.dispose()
        _engine_instance = None