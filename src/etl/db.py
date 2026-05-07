"""
db.py — Singleton de conexión al DWH.

Uso:
    from etl.db import get_engine
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(...)
"""

import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine

    load_dotenv()
    required = ["DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        sys.exit(f"[ERROR] Variables de entorno faltantes: {', '.join(missing)}")

    url = (
        f"postgresql+psycopg2://"
        f"{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{os.environ.get('DB_HOST', 'localhost')}:{os.environ.get('DB_PORT', '5432')}"
        f"/{os.environ['DB_NAME']}"
    )
    _engine = create_engine(url, pool_pre_ping=True)
    return _engine
