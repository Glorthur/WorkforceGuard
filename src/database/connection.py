"""
Database connection manager for WorkforceGuard.
Automatically connects to local MySQL 8.0 server using user credentials,
with an automatic local SQLite fallback so queries and analytics run smoothly.
"""
import os
from pathlib import Path
from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine

DB_DIR = Path(__file__).resolve().parents[2] / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
SQLITE_PATH = DB_DIR / "workforce_ai.db"

_ENGINE: Engine = None
_DB_TYPE: str = "sqlite"

def reset_engine():
    """Resets the cached engine instance (primarily for testing)."""
    global _ENGINE, _DB_TYPE
    if _ENGINE is not None:
        _ENGINE.dispose()
        _ENGINE = None
        _DB_TYPE = "sqlite"

def get_engine() -> Engine:
    """
    Returns an active SQLAlchemy engine. Automatically connects to MySQL 8.0
    if available, otherwise falls back to local SQLite.
    """
    global _ENGINE, _DB_TYPE
    if _ENGINE is not None:
        return _ENGINE

    # 1. Check WORKFORCEGUARD_DB_URL or explicit environment variable
    custom_url = os.getenv("WORKFORCEGUARD_DB_URL")
    if custom_url:
        try:
            engine = create_engine(custom_url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            _ENGINE = engine
            _DB_TYPE = "mysql" if "mysql" in custom_url else "sqlite"
            return _ENGINE
        except Exception as e:
            print(f"Notice: Could not connect to WORKFORCEGUARD_DB_URL ({e}). Falling back to local SQLite.")

    # 2. MySQL, only if configured (never hardcode credentials), e.g.
    #    MYSQL_DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/workforce_ai_governance
    mysql_url = os.getenv("MYSQL_DATABASE_URL")
    if mysql_url:
        try:
            engine = create_engine(mysql_url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            _ENGINE = engine
            _DB_TYPE = "mysql"
            return _ENGINE
        except Exception as e:
            print(f"Notice: Could not connect to MYSQL_DATABASE_URL ({type(e).__name__}). Falling back to local SQLite.")

    # 3. Fallback to SQLite with active foreign keys
    engine = create_engine(f"sqlite:///{SQLITE_PATH}", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    _ENGINE = engine
    _DB_TYPE = "sqlite"
    if not SQLITE_PATH.exists() or SQLITE_PATH.stat().st_size == 0:
        from src.database.ingest_data import ingest_all_data
        ingest_all_data(engine)
    return _ENGINE

def get_db_type() -> str:
    global _DB_TYPE
    if _ENGINE is None:
        get_engine()
    return _DB_TYPE

def execute_query(sql: str, params: dict = None):
    """Executes a SQL query and returns a pandas DataFrame."""
    import pandas as pd
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)
