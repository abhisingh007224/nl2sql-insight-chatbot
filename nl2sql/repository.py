"""Loads the SQL query repository (queries/*.sql) and its description document (descriptions.csv)."""

import csv
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from .config import DESCRIPTIONS_PATH, ROOT
from .guardrails import UnsafeSQLError, validate_sql


@dataclass(frozen=True)
class QueryRecord:
    query_id: str
    description: str
    sql: str
    sample_questions: list[str] = field(default_factory=list)

    def index_texts(self) -> list[str]:
        """Texts embedded for this query: its description plus example phrasings."""
        return [self.description, *self.sample_questions]


def load_repository(descriptions_path: Path = DESCRIPTIONS_PATH) -> dict[str, QueryRecord]:
    with open(descriptions_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    repo: dict[str, QueryRecord] = {}
    for row in rows:
        query_id = row["query_id"].strip()
        if query_id in repo:
            raise ValueError(f"Duplicate query_id in {descriptions_path.name}: {query_id}")
        sql_path = ROOT / row["sql_file"].strip()
        if not sql_path.exists():
            raise FileNotFoundError(f"SQL file for {query_id} not found: {sql_path}")
        sql = sql_path.read_text(encoding="utf-8").strip()
        try:
            validate_sql(sql)  # a write statement can never enter the repository
        except UnsafeSQLError as exc:
            raise ValueError(f"Unsafe SQL in {sql_path.name}: {exc}") from exc
        samples = [s.strip() for s in (row.get("sample_questions") or "").split("|") if s.strip()]
        repo[query_id] = QueryRecord(
            query_id=query_id,
            description=row["description"].strip(),
            sql=sql,
            sample_questions=samples,
        )
    return repo


def fingerprint(repo: dict[str, QueryRecord]) -> str:
    """Hash of every embedded text, used to detect a stale embedding index."""
    h = hashlib.sha256()
    for record in repo.values():
        h.update(record.query_id.encode())
        for text in record.index_texts():
            h.update(b"\x00" + text.encode())
    return h.hexdigest()
