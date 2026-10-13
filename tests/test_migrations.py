"""The migration must build the schema from scratch, roll back cleanly, and match the models."""

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.models import Base

ROOT = Path(__file__).resolve().parent.parent
APP_TABLES = {"departments", "roles", "employees"}


@pytest.fixture
def db_url(tmp_path):
    return f"sqlite:///{tmp_path / 'migration_test.db'}"


@pytest.fixture
def alembic_cfg(db_url):
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def tables(url):
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()


def test_upgrade_builds_schema_on_a_clean_database(alembic_cfg, db_url):
    assert tables(db_url) == set()
    command.upgrade(alembic_cfg, "head")
    assert tables(db_url) == APP_TABLES


def test_downgrade_rolls_back_cleanly_and_can_reapply(alembic_cfg, db_url):
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    assert tables(db_url) == set()
    command.upgrade(alembic_cfg, "head")  # re-applying after a rollback must also work
    assert tables(db_url) == APP_TABLES


def test_migration_matches_the_models(alembic_cfg, db_url):
    """No drift: autogenerate would find nothing to add after the migration ran."""
    command.upgrade(alembic_cfg, "head")
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    finally:
        engine.dispose()
    assert diff == []
