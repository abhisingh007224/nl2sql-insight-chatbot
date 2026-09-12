"""Safety guardrails: three independent layers, so no single miss can lead to the database being modified.

1. check_question()  - screens the user's message before retrieval. Refuses requests to drop / delete /
                       modify data, raw SQL write statements, SQL-injection patterns and prompt-injection attempts.
2. validate_sql()    - only a single read-only SELECT / WITH statement may run. Applied to every repository
                       query at load time and again right before execution.
3. executor.py       - the SQLite connection is opened read-only and an authorizer denies every operation
                       except reading, enforced by SQLite itself.
"""

import re
from dataclasses import dataclass

MAX_QUESTION_LENGTH = 500

REFUSAL_MESSAGE = (
    "🚫 **I can't do that.** This assistant is **read-only**: it answers questions about the Northwind data, "
    "but it will never drop, delete, insert, update or otherwise modify the database."
)


class UnsafeSQLError(ValueError):
    """Raised when SQL is not a single read-only statement."""


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    category: str = ""
    reason: str = ""


# ---------------------------------------------------------------- layer 1: question screening

_FLAGS = re.IGNORECASE

# Where data lives, and the business entities stored in it.
_STORAGE = r"(?:databases?|db|tables?|schemas?|records?|rows?|columns?|fields?|data|dataset|entry|entries|everything|all)"
_STORAGE_STRICT = r"(?:databases?|db|tables?|schemas?|records?|rows?|columns?)"
_ENTITIES = (
    r"(?:customers?|orders?|products?|employees?|suppliers?|shippers?|categor(?:y|ies)|invoices?|prices?"
    r"|stock|inventory|sales|details|territor(?:y|ies)|regions?)"
)
_OBJECT = rf"(?:{_STORAGE}|{_ENTITIES})"
_WITHIN = r"(?:\W+\w+){0,5}?\W+"  # verb ... object, at most 5 words apart

# Verbs that only ever mean destroying data - blocked in any sentence form.
_DESTRUCTIVE = (
    r"(?:delet(?:e|es|ed|ing)|remov(?:e|es|ed|ing)|eras(?:e|es|ed|ing)|wip(?:e|es|ed|ing)"
    r"|destroy(?:s|ed|ing)?|truncat(?:e|es|ed|ing)|purg(?:e|es|ed|ing)|(?:get|gets|getting|got)\s+rid\s+of)"
)
# Verbs that also have innocent readings ("did orders drop?", "the price change") - blocked when used
# as a command, or when aimed at the storage itself.
_MODIFY = (
    r"(?:drop|update(?!\s+(?:me|us)\b)|modify|change|edit|alter|insert|add|create|rename|overwrite|replace|reset"
    r"|set|clear|clean(?:\s+up|\s+out)?|flush|mark|increase|decrease|raise|lower|reduce|cancel|move|merge|restore"
    r"|fix|correct|adjust)"
)
_COMMAND_PREFIX = (
    r"(?:^|[.!?;,]\s*|\b(?:please|pls|kindly|can you|could you|would you|will you|you should|go ahead and"
    r"|let'?s|help me|how (?:do|can|to|would|should) (?:i|we)?|i (?:want|need|would like|'d like)(?: you)? to"
    r"|we (?:want|need)(?: you)? to|now)\s+)"
)

_QUESTION_RULES: list[tuple[re.Pattern, str, str]] = [
    # Raw SQL write / admin statements typed into the chat
    (re.compile(r"\bdrop\s+(?:table|database|view|index|trigger|schema|column)\b", _FLAGS), "sql_write", "SQL DROP statement"),
    (re.compile(r"\bdelete\s+from\b", _FLAGS), "sql_write", "SQL DELETE statement"),
    (re.compile(r"\b(?:insert|replace)\s+(?:or\s+\w+\s+)?into\b", _FLAGS), "sql_write", "SQL INSERT statement"),
    (re.compile(r"\bupdate\s+\S+\s+set\b", _FLAGS), "sql_write", "SQL UPDATE statement"),
    (re.compile(r"\balter\s+(?:table|database)\b", _FLAGS), "sql_write", "SQL ALTER statement"),
    (re.compile(r"\bcreate\s+(?:table|view|index|trigger|database|schema)\b", _FLAGS), "sql_write", "SQL CREATE statement"),
    (re.compile(r"\btruncate\b", _FLAGS), "sql_write", "SQL TRUNCATE statement"),
    (re.compile(r"\b(?:attach|detach)\s+database\b|\bpragma\b|\bvacuum\b|\b(?:grant|revoke)\s+\w+", _FLAGS), "sql_write", "database administration command"),
    # SQL injection
    (re.compile(r";\s*(?:drop|delete|insert|update|alter|create|attach|pragma|select)\b", _FLAGS), "sql_injection", "stacked SQL statement"),
    (re.compile(r"--|/\*|\*/", _FLAGS), "sql_injection", "SQL comment sequence"),
    (re.compile(r"'\s*or\s+'?\w+'?\s*=\s*'?\w+|\bunion\s+(?:all\s+)?select\b", _FLAGS), "sql_injection", "SQL injection pattern"),
    # Natural-language requests to change data
    (re.compile(rf"\b{_DESTRUCTIVE}\b{_WITHIN}{_OBJECT}\b", _FLAGS), "data_modification", "request to delete data"),
    (re.compile(rf"{_COMMAND_PREFIX}(?:please\s+)?{_MODIFY}\b{_WITHIN}{_OBJECT}\b", _FLAGS), "data_modification", "request to modify data"),
    (re.compile(rf"\b{_MODIFY}\b{_WITHIN}{_STORAGE_STRICT}\b", _FLAGS), "data_modification", "request to modify the database structure"),
    # Prompt injection / jailbreak
    (re.compile(r"\b(?:ignore|disregard|forget|override|bypass)\b(?:\W+\w+){0,4}?\W+(?:instructions?|rules?|prompts?|guardrails?|restrictions?)\b", _FLAGS), "prompt_injection", "attempt to override instructions"),
    (re.compile(r"\b(?:system prompt|jailbreak|developer mode|you are now|act as (?:an? |the )?(?:admin|administrator|dba|root))\b", _FLAGS), "prompt_injection", "attempt to override instructions"),
]


def check_question(question: str) -> GuardrailResult:
    text = " ".join(question.split())
    if len(text) > MAX_QUESTION_LENGTH:
        return GuardrailResult(False, "too_long", f"question longer than {MAX_QUESTION_LENGTH} characters")
    for pattern, category, reason in _QUESTION_RULES:
        if pattern.search(text):
            return GuardrailResult(False, category, reason)
    return GuardrailResult(True)


# ---------------------------------------------------------------- layer 2: SQL validation

# String literals, quoted identifiers and comments, matched left-to-right so e.g. '--' inside a string is handled.
_LITERALS_AND_COMMENTS = re.compile(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"|--[^\n]*|/\*.*?\*/", re.DOTALL)
_FORBIDDEN_SQL = re.compile(
    r"\b(?:insert|update|delete|drop|alter|create|truncate|attach|detach|pragma|vacuum|reindex|analyze"
    r"|grant|revoke|begin|commit|rollback|savepoint|release)\b|\breplace\b(?!\s*\()",
    re.IGNORECASE,
)


def validate_sql(sql: str) -> None:
    """Raise UnsafeSQLError unless `sql` is exactly one read-only SELECT / WITH statement."""
    body = _LITERALS_AND_COMMENTS.sub(" ", sql).strip().rstrip(";").strip()
    if not body:
        raise UnsafeSQLError("empty SQL statement")
    if ";" in body:
        raise UnsafeSQLError("multiple SQL statements are not allowed")
    if not re.match(r"(?:select|with)\b", body, re.IGNORECASE):
        raise UnsafeSQLError("only SELECT / WITH queries are allowed")
    if match := _FORBIDDEN_SQL.search(body):
        raise UnsafeSQLError(f"forbidden SQL keyword: {match.group(0).upper()}")
