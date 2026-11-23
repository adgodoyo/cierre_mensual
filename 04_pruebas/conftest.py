import sqlite3
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))


@pytest.fixture(scope="session")
def conn():
    c = sqlite3.connect(f"file:{RAIZ / '02_procesados' / 'cierre.db'}?mode=ro", uri=True)
    yield c
    c.close()
