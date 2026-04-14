from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

import reflex as rx  # noqa: E402
from alembic import context

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
from kakumi_app.models.tournament_model import (
    Tournament,
    TournamentCategory,
    Match,
    MatchScore,
    Penalty,
    Tatami,
)  # noqa: E402, F401
from kakumi_app.models.athlete_model import Athlete  # noqa: E402, F401
from kakumi_app.models.referee_model import Referee  # noqa: E402, F401
from kakumi_app.models.user_model import User  # noqa: E402, F401
from kakumi_app.models.login_attempt import LoginAttempt  # noqa: E402, F401
from kakumi_app.models.token_blacklist import TokenBlacklist  # noqa: E402, F401
from kakumi_app.models.audit_log import AuditLog  # noqa: E402, F401
from kakumi_app.models.team_model import Team, TeamMember  # noqa: E402, F401
from kakumi_app.models.kata_model import (  # noqa: E402, F401
    KataJudgeScore,
    KataRoundStanding,
)

target_metadata = rx.Model.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


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


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
