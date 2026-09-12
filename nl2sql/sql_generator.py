"""LLM query planner with a text-to-SQL fallback.

Semantic search proposes the closest vetted queries; Gemini then decides:
  USE <query_id>  - a vetted query answers the question exactly (preferred: vetted SQL is reviewed),
  SQL: <query>    - none does, so it writes a new read-only SQLite query from the live schema,
  CANNOT_ANSWER   - the question is unrelated to the database or asks to change data.
Generated SQL gets no special trust: it passes validate_sql() and runs on the same read-only,
authorizer-protected, time-limited connection as every other query.
"""

import re
from dataclasses import dataclass
from functools import lru_cache

from .executor import connect_read_only
from .llm import ask_gemini
from .repository import QueryRecord

PLANNER_PROMPT = """You are the query planner for a read-only analytics chatbot over the Northwind SQLite database
(a food & beverage wholesaler: customers, orders, order lines, products, categories, suppliers, employees, shippers).

Reply in exactly ONE of these three formats and nothing else:

USE <query_id>
    when one of the vetted queries returns exactly what the question asks for (same filters, grouping,
    time period and level of detail). Prefer this whenever it genuinely fits.

SQL:
<a single SQLite query>
    when no vetted query answers the question exactly but the database can.

CANNOT_ANSWER
    when the question is unrelated to this database, or asks to create, change or delete anything.

Rules for SQL:
- Exactly one read-only statement starting with SELECT or WITH. Never INSERT, UPDATE, DELETE, DROP, ALTER,
  CREATE, REPLACE, ATTACH or PRAGMA statements.
- Use only tables and columns from the schema. Always write the table "Order Details" in double quotes.
- Revenue / sales / amount spent = SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) over "Order Details" od.
- Dates are TEXT 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'; filter and group them with strftime() / date().
- Relative periods ("last month", "this year", "recently") are relative to the latest order date in the data,
  (SELECT MAX(OrderDate) FROM Orders), never to today's date.
- Products.Discontinued is '1' for discontinued products, '0' otherwise.
- Round money and averages to 2 decimals and give every computed column a readable snake_case alias.
- Return at most 50 rows unless the user explicitly asks for everything.
- Questions about the database itself: use sqlite_master and pragma_table_info('<table name>').
- No comments and no markdown fences."""

RELATIONSHIPS = """Relationships:
Orders.CustomerID -> Customers.CustomerID; Orders.EmployeeID -> Employees.EmployeeID; Orders.ShipVia -> Shippers.ShipperID
"Order Details".OrderID -> Orders.OrderID; "Order Details".ProductID -> Products.ProductID
Products.CategoryID -> Categories.CategoryID; Products.SupplierID -> Suppliers.SupplierID
Employees.ReportsTo -> Employees.EmployeeID; EmployeeTerritories links Employees and Territories; Territories.RegionID -> Regions.RegionID"""


@dataclass(frozen=True)
class QueryPlan:
    kind: str  # "vetted" | "generated" | "cannot_answer"
    query_id: str | None = None
    sql: str | None = None


@lru_cache(maxsize=1)
def schema_description() -> str:
    """Every table with its row count and column types, read from the live database."""
    lines = []
    with connect_read_only() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        for (table,) in tables:
            columns = conn.execute("SELECT name, type FROM pragma_table_info(?)", (table,)).fetchall()
            rows = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            lines.append(f'"{table}" ({rows:,} rows): ' + ", ".join(f"{name} {ctype}".strip() for name, ctype in columns))
    return "\n".join(lines) + "\n\n" + RELATIONSHIPS


def parse_plan(reply: str, candidate_ids: set[str]) -> QueryPlan:
    text = re.sub(r"```(?:sql)?", "", reply, flags=re.IGNORECASE).strip()
    if text.upper().startswith("CANNOT_ANSWER"):
        return QueryPlan("cannot_answer")
    if match := re.match(r"USE\s+([\w-]+)", text, re.IGNORECASE):
        if match.group(1) in candidate_ids:
            return QueryPlan("vetted", query_id=match.group(1))
        raise ValueError(f"planner chose an unknown query: {match.group(1)}")
    sql = re.sub(r"^SQL:\s*", "", text, flags=re.IGNORECASE).strip()
    if re.match(r"(?:select|with)\b", sql, re.IGNORECASE):
        return QueryPlan("generated", sql=sql)
    raise ValueError(f"could not parse planner reply: {reply[:200]!r}")


def plan_query(
    question: str,
    candidates: list[QueryRecord],
    history: list[tuple[str, str]] | None = None,
    failed_sql: str | None = None,
    error: str | None = None,
) -> QueryPlan:
    parts = []
    if history:
        turns = "\n".join(f"{role}: {text[:300]}" for role, text in history[-4:])
        parts.append(f"Earlier conversation (only for resolving follow-up questions):\n{turns}")
    parts.append(f"Database schema:\n{schema_description()}")
    vetted = "\n".join(f"- {c.query_id}: {c.description}" for c in candidates) or "none"
    parts.append(f"Vetted queries:\n{vetted}")
    parts.append(f"User question: {question}")
    if failed_sql:
        parts.append(f"Your previous SQL failed.\nSQL:\n{failed_sql}\nError: {error}\nReply with corrected SQL in the SQL: format.")
    return parse_plan(ask_gemini(PLANNER_PROMPT, "\n\n".join(parts)), {c.query_id for c in candidates})
