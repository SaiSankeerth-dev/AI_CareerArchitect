import os
import sys
from pathlib import Path

# Run tests against a throwaway SQLite DB and no external LLM.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_career.db")
os.environ.setdefault("LLM_MODEL", "ollama/test-model-not-running")
os.environ.setdefault("LLM_API_BASE", "http://127.0.0.1:1")  # guaranteed unreachable
os.environ.setdefault("JWT_SECRET", "test-secret")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Remove any stale DB from a previous run before the engine touches it.
Path("test_career.db").unlink(missing_ok=True)

import pytest


@pytest.fixture(autouse=True, scope="session")
def _cleanup_test_db():
    yield
    for name in ("test_career.db",):
        try:
            Path(name).unlink(missing_ok=True)
        except PermissionError:
            pass
