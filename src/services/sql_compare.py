"""Compare a stored procedure's definition across every server and database.

Fixes Java bug #2. The Java controller never stored the first server's
definition, so differences *between* servers could never be reported. This
version gathers every (server, database) definition first and then groups
them, so the report says exactly which copies differ instead of stopping at
the first mismatch.

Also fixed along the way:
* queries are parameterised (the Java code concatenated the procedure name
  into the SQL string);
* a missing procedure or missing permission is reported per database instead
  of crashing on a null definition;
* one unreachable server no longer hides the results from the others.

Run ``compare()`` off the UI thread (e.g. in a QThreadPool worker); it blocks
on network I/O.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from ..model.items import ServerConfig, SQLCompareItem, SQLType
from .odbc import best_driver

# fetch(sql_type, server, database, procedure) -> definition text, or None if not found
Fetcher = Callable[[SQLType, ServerConfig, str, str], "str | None"]

_WHITESPACE = re.compile(r"\s+")


def normalize(definition: str) -> str:
    """Same rule as the Java version: ignore all whitespace and letter case."""
    return _WHITESPACE.sub("", definition).lower()


@dataclass(frozen=True)
class Location:
    server: str
    database: str

    def __str__(self) -> str:
        return f"{self.server} / {self.database}"


@dataclass
class CompareReport:
    procedure: str
    groups: list[list[Location]] = field(default_factory=list)  # one group per distinct definition
    missing: list[Location] = field(default_factory=list)
    errors: dict[Location, str] = field(default_factory=dict)

    @property
    def all_match(self) -> bool:
        return len(self.groups) == 1 and not self.missing and not self.errors

    def summary(self) -> str:
        if self.all_match:
            n = len(self.groups[0])
            return f"All definitions of '{self.procedure}' match ({n} databases checked)."
        lines = [f"Definitions of '{self.procedure}' do NOT all match."]
        if len(self.groups) > 1:
            lines.append("")
            for i, group in enumerate(self.groups, 1):
                lines.append(f"Version {i}:")
                lines.extend(f"    {loc}" for loc in group)
        if self.missing:
            lines += ["", "Procedure not found (or no permission to view it):"]
            lines.extend(f"    {loc}" for loc in self.missing)
        if self.errors:
            lines += ["", "Could not check:"]
            lines.extend(f"    {loc}: {msg}" for loc, msg in self.errors.items())
        return "\n".join(lines)


def compare(item: SQLCompareItem, fetch: Fetcher | None = None) -> CompareReport:
    fetch = fetch or fetch_definition
    report = CompareReport(procedure=item.procedure_name)
    by_definition: dict[str, list[Location]] = {}

    for server in item.servers:
        for database in server.databases:
            loc = Location(server.tab_name, database)
            try:
                definition = fetch(item.sql_type, server, database, item.procedure_name)
            except Exception as exc:  # driver errors vary by library
                report.errors[loc] = str(exc).strip() or type(exc).__name__
                continue
            if definition is None:
                report.missing.append(loc)
            else:
                by_definition.setdefault(normalize(definition), []).append(loc)

    # Largest group first, so "Version 1" is the majority copy.
    report.groups = sorted(by_definition.values(), key=len, reverse=True)
    return report


# ------------------------------------------------------------- real database access

def fetch_definition(sql_type: SQLType, server: ServerConfig, database: str,
                     procedure: str) -> str | None:
    if sql_type is SQLType.MYSQL:
        return _fetch_mysql(server, database, procedure)
    if sql_type is SQLType.TRANSACT_SQL:
        return _fetch_tsql(server, database, procedure)
    raise ValueError(f"Unsupported SQL type: {sql_type}")


def _fetch_mysql(server: ServerConfig, database: str, procedure: str) -> str | None:
    import pymysql

    conn = pymysql.connect(host=server.host, port=server.port if server.port > 0 else 3306,
                           user=server.username, password=server.password,
                           database=database, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT routine_definition FROM information_schema.routines "
                "WHERE specific_name = %s AND routine_schema = %s",
                (procedure, database),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    return row[0] if row and row[0] is not None else None


def _fetch_tsql(server: ServerConfig, database: str, procedure: str) -> str | None:
    import pyodbc

    host = f"{server.host},{server.port}" if server.port > 0 else server.host
    parts = [
        f"DRIVER={best_driver()}",
        f"SERVER={host}",
        f"DATABASE={database}",
        "Encrypt=yes",
    ]
    if server.integrated_security:
        parts.append("Trusted_Connection=yes")
    else:
        parts += [f"UID={server.username}", f"PWD={{{server.password.replace('}', '}}')}}}"]
    conn = pyodbc.connect(";".join(parts), timeout=10)
    try:
        cur = conn.cursor()
        cur.execute("SELECT OBJECT_DEFINITION(OBJECT_ID(?))", procedure)
        row = cur.fetchone()
    finally:
        conn.close()
    return row[0] if row and row[0] is not None else None
