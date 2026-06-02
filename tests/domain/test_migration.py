"""Alembic migration sanity tests."""

import importlib.util
import inspect
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "alembic" / "versions"


def _load_migration(filename: str):
    path = MIGRATIONS_DIR / filename
    spec = importlib.util.spec_from_file_location(filename.removesuffix(".py"), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_module_imports() -> None:
    module = _load_migration("002_phase2_domain_models.py")
    assert module.revision == "002_phase2_domain_models"
    assert module.down_revision == "001_phase1_initial"
    assert callable(module.upgrade)
    assert callable(module.downgrade)


def test_migration_creates_all_domain_tables() -> None:
    module = _load_migration("002_phase2_domain_models.py")
    source = inspect.getsource(module.upgrade)
    for table in ("cameras", "zones", "visitor_sessions", "transactions", "events"):
        assert table in source


def test_migration_revision_chain() -> None:
    phase1 = _load_migration("001_phase1_initial.py")
    phase2 = _load_migration("002_phase2_domain_models.py")
    assert phase1.down_revision is None
    assert phase2.down_revision == phase1.revision
