"""Executes SQL against the SQLite database: strictly read-only, time-limited and row-capped."""

import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from .config import DB_PATH, MAX_RESULT_ROWS, QUERY_TIMEOUT_SECONDS
from .guardrails import validate_sql

# SQLite authorizer: everything except reading tables and calling functions is denied by the engine itself.
_ALLOWED_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
# Read-only schema introspection, e.g. SELECT ... FROM pragma_table_info('Orders').
_ALLOWED_PRAGMAS = {"table_info", "table_xinfo", "foreign_key_list", "index_list", "index_info"}


def _read_only_authorizer(action: int, arg1: str | None, *_args) -> int:
    if action in _ALLOWED_ACTIONS:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_PRAGMA and (arg1 or "").lower() in _ALLOWED_PRAGMAS:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


@contextmanager
def connect_read_only(db_path: Path = DB_PATH, timeout: float = QUERY_TIMEOUT_SECONDS) -> Iterator[sqlite3.Connection]:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}. See README for setup.")
    # mode=ro: the connection cannot modify the database, whatever the SQL says.
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        conn.set_authorizer(_read_only_authorizer)
        deadline = time.monotonic() + timeout
        conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 10_000)  # non-zero aborts the query
        yield conn
    finally:
        conn.close()


def run_query(sql: str, db_path: Path = DB_PATH, max_rows: int = MAX_RESULT_ROWS) -> pd.DataFrame:
    validate_sql(sql)
    with connect_read_only(db_path) as conn:
        try:
            cursor = conn.execute(sql)
            rows = cursor.fetchmany(max_rows + 1)
        except sqlite3.OperationalError as exc:
            if "interrupted" in str(exc):
                raise TimeoutError(f"query stopped after exceeding the {QUERY_TIMEOUT_SECONDS}s time limit") from exc
            raise
        columns = [d[0] for d in cursor.description]
    df = pd.DataFrame(rows[:max_rows], columns=columns)
    df.attrs["truncated"] = len(rows) > max_rows
    return df
