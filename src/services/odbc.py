"""Shared SQL Server ODBC helpers (SQL Compare, Schema Backup, Queries)."""
from __future__ import annotations

from functools import lru_cache

_SERVER_KEYS = {"server", "data source", "address", "addr", "network address"}
_DATABASE_KEYS = {"database", "initial catalog"}
_AUTH_KEYS = {"uid", "user id", "trusted_connection", "integrated security", "authentication"}
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


def _parse(conn_str: str) -> list[tuple[str, str]]:
    """Split ``key=value;...`` into pairs; ``{...}`` values may contain ``;``."""
    pairs, i, n = [], 0, len(conn_str)
    while i < n:
        eq = conn_str.find("=", i)
        if eq == -1:
            break
        key = conn_str[i:eq].strip().strip(";").strip()
        j = eq + 1
        while j < n and conn_str[j] == " ":
            j += 1
        if j < n and conn_str[j] == "{":
            end = j + 1
            while end < n:  # "}}" is an escaped brace inside a braced value
                if conn_str[end] == "}":
                    if end + 1 < n and conn_str[end + 1] == "}":
                        end += 2
                        continue
                    break
                end += 1
            value = conn_str[j:end + 1]
            i = conn_str.find(";", end) + 1 or n
        else:
            semi = conn_str.find(";", j)
            semi = n if semi == -1 else semi
            value = conn_str[j:semi].strip()
            i = semi + 1
        if key:
            pairs.append((key, value))
    return pairs


def build_connection_string(server: str, extra: str, database: str, driver: str | None = None) -> str:
    """``extra`` (what the user typed) with the driver, server and database filled in.

    Anything the user typed wins, except the database, which is always the one
    asked for. With no login given, Windows authentication is used.
    """
    pairs = [(k, v) for k, v in _parse(extra) if k.lower() not in _DATABASE_KEYS]
    keys = {k.lower() for k, _ in pairs}
    if "driver" not in keys:
        pairs.insert(0, ("DRIVER", driver or best_driver()))
    if not keys & _SERVER_KEYS:
        pairs.insert(1, ("SERVER", server))
    pairs.append(("DATABASE", "{" + database.replace("}", "}}") + "}"))
    if not keys & _AUTH_KEYS:
        pairs.append(("Trusted_Connection", "yes"))
    return ";".join(f"{k}={v}" for k, v in pairs)
