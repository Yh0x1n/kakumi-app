import os

import reflex as rx


def _stamp_head_if_fresh_pg(connection) -> str | None:
    """Stamp alembic head on a fresh PostgreSQL connection.

    Returns the head revision if stamped, None otherwise.
    """
    dialect = connection.dialect.name
    if dialect != "postgresql":
        return None

    from sqlalchemy import inspect

    if "alembic_version" in inspect(connection).get_table_names():
        return None

    from pathlib import Path

    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory

    alembic_ini = Path(__file__).parent / "alembic.ini"
    if not alembic_ini.exists():
        return None

    from alembic.config import Config as AlembicConfig

    cfg = AlembicConfig(str(alembic_ini))
    script = ScriptDirectory.from_config(cfg)
    mc = MigrationContext.configure(connection)
    mc.stamp(script, "heads")
    return str(script.get_current_head())


# Monkey-patch Model._alembic_upgrade so ``reflex db migrate`` auto-stamps
# a fresh PG database before running any migration — Reflex bypasses env.py
# when it creates its own EnvironmentContext internally.
_original_alembic_upgrade = rx.Model._alembic_upgrade


@classmethod  # type: ignore[misc]
def _alembic_upgrade_with_stamp(cls, connection, to_rev: str = "head"):
    head = _stamp_head_if_fresh_pg(connection)
    if head:
        print(f"[rxconfig] Fresh PG — stamped alembic head: {head}")
    return _original_alembic_upgrade(connection, to_rev)


rx.Model._alembic_upgrade = _alembic_upgrade_with_stamp


config = rx.Config(
    app_name="kakumi_app",
    # api_url="http://app.kakumitm.com:8000",
    # backend_path="/api",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
    db_url=os.getenv("DATABASE_URL", "sqlite:///kakumi.db"),
)
