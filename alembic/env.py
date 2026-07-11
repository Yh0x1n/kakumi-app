import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, inspect
from sqlalchemy import pool

import reflex as rx  # noqa: E402
from alembic import context
from kakumi_app import models as _models  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

target_metadata = rx.Model.metadata

# Override sqlalchemy.url with DATABASE_URL env var if set.
_env_url = os.getenv("DATABASE_URL", "").strip()
if _env_url:
    config.set_main_option("sqlalchemy.url", _env_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def _stamp_head_if_fresh_pg(connection) -> str | None:
    """
    Detect a fresh PostgreSQL database (no alembic_version table)
    and stamp the current head to avoid replaying legacy migrations.

    Returns the head revision if stamped, None otherwise.
    """
    dialect = connection.dialect.name
    if dialect != "postgresql":
        return None

    insp = inspect(connection)
    if "alembic_version" in insp.get_table_names():
        return None

    # Fresh PG: stamp head instead of replaying 26 legacy CREATE TABLEs.
    from alembic.script import ScriptDirectory
    from alembic.runtime.migration import MigrationContext

    script = ScriptDirectory.from_config(config)
    head = "heads"
    context_ctx = MigrationContext.configure(connection)
    context_ctx.stamp(script, head)
    return str(script.get_current_head())


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    section = config.get_section(config.config_ini_section, {})
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        stamped = _stamp_head_if_fresh_pg(connection)
        if stamped:
            print(
                f"[env.py] Fresh PostgreSQL detected — stamped alembic head: {stamped}"
            )

        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
