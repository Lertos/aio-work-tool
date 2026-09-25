"""Shared SQL Server ODBC helpers (SQL Compare and Schema Backup)."""
from __future__ import annotations

from functools import lru_cache

DRIVER_PREFERENCE = ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server")


@lru_cache(maxsize=1)
def best_driver() -> str:
    """Newest SQL Server ODBC driver installed ("SQL Server" ships with every Windows)."""
    try:
        import pyodbc
        installed = set(pyodbc.drivers())
    except ImportError:
        installed = set()
    name = next((d for d in DRIVER_PREFERENCE if d in installed), DRIVER_PREFERENCE[0])
    return "{" + name + "}"
