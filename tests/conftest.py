import os
import tempfile
from pathlib import Path

_TEST_DIR = Path(tempfile.mkdtemp(prefix="agent_workbench_test_"))
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ["DATABASE_URL"] = f"sqlite:///{(_TEST_DIR / 'agent.db').as_posix()}"

import pytest  # noqa: E402

import backend.tools.database as database_tool  # noqa: E402
import backend.tools.file_tools as file_tools  # noqa: E402
from backend.db import Base, engine, init_db  # noqa: E402

database_tool.DEMO_DB_PATH = _TEST_DIR / "demo.db"
file_tools.WORKSPACE_DIR = _TEST_DIR / "workspace"

init_db()


@pytest.fixture(autouse=True)
def _clean_database():
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
