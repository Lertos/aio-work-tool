"""Save the current definition of procedures, functions, triggers and views to .sql files.

One run writes into a new timestamped folder so earlier backups are never overwritten::

    <save folder>/<environment> 2026-09-25 143012/<database>/<entity>.sql

Each database gets one connection, reused for all of its entities. A missing
entity or an unreachable database is reported and the rest of the run carries on.

Run ``backup()`` off the UI thread (e.g. in a QThreadPool worker); it blocks
on network I/O.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from ..model.items import SchemaEnvironment
from .odbc import best_driver

# fetch(connection_string, entities) -> {entity: definition, or None if not found}
Fetcher = Callable[[str, list[str]], "dict[str, str | None]"]

_SERVER_KEYS = {"server", "data source", "address", "addr", "network address"}
_DATABASE_KEYS = {"database", "initial catalog"}
_AUTH_KEYS = {"uid", "user id", "trusted_connection", "integrated security", "authentication"}
_BAD_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


# ------------------------------------------------------------------ connection strings

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


def connection_string(env: SchemaEnvironment, database: str, driver: str | None = None) -> str:
    """The environment's connection string with the driver, server and database filled in.

    Anything the user typed wins, except the database, which is always the one
    being backed up. With no login given, Windows authentication is used.
    """
    pairs = [(k, v) for k, v in _parse(env.connection_string)
             if k.lower() not in _DATABASE_KEYS]
    keys = {k.lower() for k, _ in pairs}
    if "driver" not in keys:
        pairs.insert(0, ("DRIVER", driver or best_driver()))
    if not keys & _SERVER_KEYS:
        pairs.insert(1, ("SERVER", env.server))
    pairs.append(("DATABASE", "{" + database.replace("}", "}}") + "}"))
    if not keys & _AUTH_KEYS:
        pairs.append(("Trusted_Connection", "yes"))
    return ";".join(f"{k}={v}" for k, v in pairs)


# ------------------------------------------------------------------------- backup

@dataclass
class BackupResult:
    folder: Path
    saved: list[Path] = field(default_factory=list)
    missing: dict[str, list[str]] = field(default_factory=dict)  # database -> entities
    errors: dict[str, str] = field(default_factory=dict)          # database -> message

    def summary(self) -> str:
        lines = [f"{len(self.saved)} definition(s) saved."]
        if self.saved:
            lines.append(f"\n{self.folder}")
        if self.missing:
            lines.append("\nNot found (or no permission to view):")
            for database, entities in self.missing.items():
                lines.append(f"    {database}: {', '.join(entities)}")
        if self.errors:
            lines.append("\nCould not connect:")
            lines.extend(f"    {database}: {message}" for database, message in self.errors.items())
        return "\n".join(lines)


def split_names(text: str) -> list[str]:
    """Names from a text box: one per line and/or comma-separated, duplicates removed."""
    seen, names = set(), []
    for name in re.split(r"[\n,]", text):
        name = name.strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            names.append(name)
    return names


def safe_filename(name: str) -> str:
    return _BAD_FILENAME_CHARS.sub("_", name).strip(" .") or "_"


def backup(env: SchemaEnvironment, databases: list[str], entities: list[str], save_to: Path,
           fetch: Fetcher | None = None, now: datetime | None = None) -> BackupResult:
    fetch = fetch or fetch_definitions
    stamp = (now or datetime.now()).strftime("%Y-%m-%d %H%M%S")
    result = BackupResult(Path(save_to) / safe_filename(f"{env.description} {stamp}"))

    for database in databases:
        try:
            definitions = fetch(connection_string(env, database), entities)
        except Exception as exc:  # driver errors vary; report and move on
            result.errors[database] = str(exc).strip() or type(exc).__name__
            continue
        folder = result.folder / safe_filename(database)
        for entity in entities:
            definition = definitions.get(entity)
            if definition is None:
                result.missing.setdefault(database, []).append(entity)
                continue
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"{safe_filename(entity)}.sql"
            # newline="" keeps the server's line endings exactly as stored.
            path.write_text(definition, encoding="utf-8", newline="")
            result.saved.append(path)
    return result


# ------------------------------------------------------------- real database access

def fetch_definitions(conn_str: str, entities: list[str]) -> dict[str, str | None]:
    import pyodbc

    conn = pyodbc.connect(conn_str, timeout=10)
    try:
        cur = conn.cursor()
        found = {}
        for entity in entities:
            cur.execute("SELECT OBJECT_DEFINITION(OBJECT_ID(?))", entity)
            row = cur.fetchone()
            found[entity] = row[0] if row and row[0] is not None else None
        return found
    finally:
        conn.close()
