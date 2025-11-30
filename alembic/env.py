# alembic/env.py
from __future__ import annotations
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context
from dotenv import load_dotenv

# load .env from project root
load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# If alembic.ini has a placeholder for sqlalchemy.url, override it from env
# (you can also set sqlalchemy.url in alembic.ini to something sensible)
raw_url = os.environ.get("DATABASE_URL")
if not raw_url:
    # fallback to DATABASE_SYNC_URL if you provided one
    raw_url = os.environ.get("DATABASE_SYNC_URL")
if not raw_url:
    raise RuntimeError("DATABASE_URL (or DATABASE_SYNC_URL) must be set in the environment or .env")

# Convert asyncpg URL to psycopg2 URL for Alembic (sync)
# e.g. postgresql+asyncpg://user:pass@host/db -> postgresql+psycopg2://user:pass@host/db
if raw_url.startswith("postgresql+asyncpg://"):
    sync_url = raw_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
else:
    sync_url = raw_url

# set the sqlalchemy.url used by alembic
config.set_main_option("sqlalchemy.url", sync_url)

# Interpret the config file for Python logging.
if config.config_file_name:
    fileConfig(config.config_file_name)

# Import your model's MetaData object here
# Make sure app.database.Base is importable (project root is current working directory)
try:
    from app.database import Base  # noqa: E402
except Exception as exc:
    raise RuntimeError("Could not import Base from app.database. Ensure your project root is current working directory and app.database is importable.") from exc

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
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
    """Run migrations in 'online' mode using a sync engine."""
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # helpful for detecting type changes
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
