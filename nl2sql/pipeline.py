"""End-to-end flow: guardrail -> semantic retrieval -> (LLM planner) -> SQL execution -> grounded LLM answer."""

from dataclasses import dataclass, field

import pandas as pd

from .answerer import Answer, generate_answer
from .config import CONFIDENT_MATCH, MIN_SIMILARITY
from .executor import run_query
from .guardrails import REFUSAL_MESSAGE, UnsafeSQLError, check_question
from .llm import llm_available
from .repository import QueryRecord, load_repository
from .retriever import Match, Retriever
from .sql_generator import plan_query

GENERATED_ID = "generated_sql"


@dataclass
class ChatResult:
    question: str
    answer: Answer
    matches: list[Match] = field(default_factory=list)
    record: QueryRecord | None = None
    data: pd.DataFrame | None = None
    route: str = "declined"  # "vetted" | "generated" | "declined" | "blocked" | "error"

    @property
    def best(self) -> Match | None:
        return self.matches[0] if self.matches else None

    @property
    def chosen_match(self) -> Match | None:
        """Semantic-search match of the query that was actually run, if it was a vetted one."""
        if self.record is None:
            return None
        return next((m for m in self.matches if m.query_id == self.record.query_id), None)


def _refusal(reason: str) -> Answer:
    text = f"{REFUSAL_MESSAGE}\n\n_Blocked by guardrail: {reason}._\n\nTry a question instead, e.g. *Which customer spent the most?*"
    return Answer(text, "guardrail")


class NL2SQLPipeline:
    def __init__(self):
        self.repo = load_repository()
        self.retriever = Retriever(self.repo)

    def ask(self, question: str, history: list[tuple[str, str]] | None = None) -> ChatResult:
        verdict = check_question(question)
        if not verdict.allowed:
            return ChatResult(question, _refusal(verdict.reason), route="blocked")

        matches = self.retriever.search(question, top_k=3)
        best = matches[0]

        # Near-exact match, or no LLM available: semantic search alone decides.
        if best.score >= CONFIDENT_MATCH or not llm_available():
            if best.score < MIN_SIMILARITY:
                return self._decline(question, matches)
            return self._run_vetted(question, self.repo[best.query_id], matches, history)

        # Otherwise Gemini checks whether a vetted candidate really answers the question, or writes new SQL.
        candidates = [self.repo[m.query_id] for m in matches if m.score >= MIN_SIMILARITY]
        try:
            plan = plan_query(question, candidates, history)
        except Exception as exc:
            if best.score >= MIN_SIMILARITY:
                note = f"Query planner unavailable ({exc}), so the closest vetted query was used without checking that it fits."
                return self._run_vetted(question, self.repo[best.query_id], matches, history, note=note)
            return self._decline(question, matches, note=f"Query planner unavailable ({exc}).")

        if plan.kind == "vetted":
            return self._run_vetted(question, self.repo[plan.query_id], matches, history)
        if plan.kind == "generated":
            return self._run_generated(question, plan.sql, matches, history)
        return self._decline(question, matches)

    def _decline(self, question: str, matches: list[Match], note: str | None = None) -> ChatResult:
        suggestions = "\n".join(f"- {self.repo[m.query_id].sample_questions[0]}" for m in matches)
        text = f"I can't answer that from the Northwind database. Related questions I can answer:\n{suggestions}"
        if not llm_available():
            text += "\n\n_Add a GEMINI_API_KEY to let me write new SQL for questions outside the vetted query repository._"
        return ChatResult(question, Answer(text, "template", note=note), matches, route="declined")

    def _run_vetted(self, question, record: QueryRecord, matches, history, note: str | None = None) -> ChatResult:
        try:
            df = run_query(record.sql)
        except UnsafeSQLError as exc:
            return ChatResult(question, _refusal(str(exc)), matches, record, route="blocked")
        except Exception as exc:
            return ChatResult(question, Answer(f"Running the query failed: {exc}", "template"), matches, record, route="error")
        answer = generate_answer(question, record, df, history)
        if note:
            answer.note = f"{note} {answer.note or ''}".strip()
        return ChatResult(question, answer, matches, record, df, route="vetted")

    def _run_generated(self, question, sql: str, matches, history) -> ChatResult:
        error: Exception | None = None
        for attempt in range(2):  # one self-correction round if the generated SQL fails
            try:
                df = run_query(sql)
            except UnsafeSQLError as exc:
                return ChatResult(question, _refusal(f"generated SQL rejected - {exc}"), matches, route="blocked")
            except Exception as exc:
                error = exc
                if attempt == 1:
                    break
                try:
                    plan = plan_query(question, [], history, failed_sql=sql, error=str(exc))
                except Exception:
                    break
                if plan.kind != "generated":
                    break
                sql = plan.sql
                continue
            record = QueryRecord(GENERATED_ID, f"Result of an AI-generated SQL query answering: {question}", sql)
            return ChatResult(question, generate_answer(question, record, df, history), matches, record, df, route="generated")

        record = QueryRecord(GENERATED_ID, "AI-generated SQL that failed to run", sql)
        text = f"I wrote a SQL query for that, but it failed to run: {error}"
        return ChatResult(question, Answer(text, "template"), matches, record, route="error")
