"""Terminal version of the chatbot (the Streamlit app is app.py).

Usage:  uv run python main.py
"""

from nl2sql.answerer import compose_response
from nl2sql.pipeline import NL2SQLPipeline


def main() -> None:
    print("Loading embedding model and index...")
    pipeline = NL2SQLPipeline()
    history: list[tuple[str, str]] = []
    print("Ask a question about Northwind sales (type 'exit' to quit).\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        result = pipeline.ask(question, history)
        query = result.record.query_id if result.record else "no query"
        print(f"\n[{result.route} | {query} | answer: {result.answer.source}]")
        if result.route == "generated":
            print(result.record.sql)
        if result.answer.note:
            print(f"[{result.answer.note}]")
        print(f"\nBot: {compose_response(result.answer, result.data)}\n")
        if result.answer.unverified_numbers:
            print(f"[warning: numbers not found in the data: {', '.join(result.answer.unverified_numbers)}]\n")
        history += [("user", question), ("assistant", result.answer.text)]


if __name__ == "__main__":
    main()
