"""Run a saved query against one database and collect every result set (Queries tab).

* ``GO`` on a line of its own splits the script into batches, like SSMS.
* Each batch may return several result sets; all are kept, in order.
* Statements that return no rows (UPDATE, INSERT...) are reported as "N rows affected".
* Runs with autocommit on, so changes are committed as each statement completes.
* At most MAX_ROWS rows are kept per result set, so a huge SELECT can't freeze the app.

Run ``run_query()`` off the UI thread (e.g. in a QThreadPool worker); it blocks
on network I/O.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from ..model.items import SavedQuery
from .odbc import build_connection_string

MAX_ROWS = 10_000
_GO = re.compile(r"^\s*GO\s*;?\s*$", re.IGNORECASE | re.MULTILINE)


@dataclass
class ResultSet:
    columns: list[str]
    rows: list[tuple]
    truncated: bool = False  # True if the server returned more than MAX_ROWS rows


@dataclass
class QueryResult:
    result_sets: list[ResultSet] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)  # "12 rows affected" etc.


# execute(connection_string, batches) -> QueryResult
Executor = Callable[[str, list[str]], QueryResult]


def split_batches(sql: str) -> list[str]:
    return [batch.strip() for batch in _GO.split(sql) if batch.strip()]


def remember_database(item: SavedQuery, database: str, keep: int = 10) -> list[str]:
    """``recent_databases`` with ``database`` moved to the front."""
    rest = [d for d in item.recent_databases if d.lower() != database.lower()]
    return [database] + rest[:keep - 1]


def run_query(item: SavedQuery, database: str, execute: Executor | None = None) -> QueryResult:
    execute = execute or execute_batches
    conn_str = build_connection_string(item.server, item.connection_string, database)
    return execute(conn_str, split_batches(item.query))


# ------------------------------------------------------------- real database access

def execute_batches(conn_str: str, batches: list[str]) -> QueryResult:
    import pyodbc

    result = QueryResult()
    conn = pyodbc.connect(conn_str, timeout=10, autocommit=True)
    try:
        cur = conn.cursor()
        for batch in batches:
            cur.execute(batch)
            while True:
                if cur.description:
                    columns = [col[0] or f"(column {i + 1})" for i, col in enumerate(cur.description)]
                    rows = [tuple(row) for row in cur.fetchmany(MAX_ROWS + 1)]
                    truncated = len(rows) > MAX_ROWS
                    result.result_sets.append(ResultSet(columns, rows[:MAX_ROWS], truncated))
                elif cur.rowcount >= 0:
                    result.messages.append(f"{cur.rowcount} row(s) affected")
                if not cur.nextset():
                    break
    finally:
        conn.close()
    return result
