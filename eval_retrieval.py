"""Retrieval accuracy check: unseen paraphrases (not in descriptions.csv) must map to the expected query.

Usage:  uv run python eval_retrieval.py
"""

import sys

from nl2sql.config import MIN_SIMILARITY
from nl2sql.repository import load_repository
from nl2sql.retriever import Retriever

TEST_CASES = [
    ("How much money have we made in total?", "q01_total_revenue"),
    ("Give me the overall revenue figure", "q01_total_revenue"),
    ("What was the revenue for the past month?", "q02_sales_last_month"),
    ("Sales figures for last month please", "q02_sales_last_month"),
    ("Annual revenue trend", "q03_sales_by_year"),
    ("How did we do each year?", "q03_sales_by_year"),
    ("Who is our most valuable client?", "q04_top_customers"),
    ("Top 10 customers by purchases", "q04_top_customers"),
    ("Which items generate the most revenue?", "q05_top_products_by_revenue"),
    ("Most lucrative products", "q05_top_products_by_revenue"),
    ("Which product has the highest sales volume in units?", "q06_top_products_by_quantity"),
    ("What do customers order the most, by quantity?", "q06_top_products_by_quantity"),
    ("Revenue split across product categories", "q07_sales_by_category"),
    ("Which category is the most profitable?", "q07_sales_by_category"),
    ("Rank the employees by sales", "q08_employee_performance"),
    ("Who sold the most among our staff?", "q08_employee_performance"),
    ("Which countries do we sell to the most?", "q09_sales_by_country"),
    ("Revenue per country", "q09_sales_by_country"),
    ("Which delivery company should we use?", "q10_shipper_performance"),
    ("Average freight per shipping company", "q10_shipper_performance"),
    ("How often are orders shipped after the due date?", "q11_late_shipments"),
    ("On-time delivery rate", "q11_late_shipments"),
    ("Which items should we restock?", "q12_low_stock_products"),
    ("Products below reorder level", "q12_low_stock_products"),
    ("Which products are no longer available?", "q13_discontinued_products"),
    ("Show me the discontinued product list", "q13_discontinued_products"),
    ("What's the typical order size in dollars?", "q14_average_order_value"),
    ("Average basket value", "q14_average_order_value"),
    ("Monthly breakdown of last year's sales", "q15_monthly_sales_last_year"),
    ("How did revenue vary month to month last year?", "q15_monthly_sales_last_year"),
    ("Which orders are waiting to be shipped?", "q16_pending_orders"),
    ("List orders with no ship date", "q16_pending_orders"),
    ("What is our priciest product?", "q17_most_expensive_products"),
    ("Top 10 products by unit price", "q17_most_expensive_products"),
    ("Customer count per country", "q18_customers_by_country"),
    ("In which country are most of our clients based?", "q18_customers_by_country"),
    ("How much revenue did we lose to discounts?", "q19_discount_summary"),
    ("What proportion of sales were discounted?", "q19_discount_summary"),
    ("How many vendors are in each country?", "q20_suppliers_by_country"),
    ("Where are our suppliers based?", "q20_suppliers_by_country"),
    ("How big is each table in the database?", "q21_database_overview"),
    ("no of rows and column in the datbase", "q21_database_overview"),
]

OUT_OF_SCOPE = [
    "What's the weather like in Paris today?",
    "Write me a poem about cats",
]


def main() -> int:
    repo = load_repository()
    retriever = Retriever(repo)

    top1 = top3 = 0
    for question, expected in TEST_CASES:
        matches = retriever.search(question, top_k=3)
        ids = [m.query_id for m in matches]
        top1 += ids[0] == expected
        top3 += expected in ids
        if ids[0] != expected:
            print(f"MISS  {question!r}\n      expected {expected}, got {ids[0]} ({matches[0].score:.2f}); top3={ids}")

    n = len(TEST_CASES)
    print(f"\nTop-1 accuracy: {top1}/{n} = {top1 / n:.1%}")
    print(f"Top-3 accuracy: {top3}/{n} = {top3 / n:.1%}")

    print(f"\nOut-of-scope questions (should score below {MIN_SIMILARITY:.2f}):")
    for question in OUT_OF_SCOPE:
        best = retriever.search(question, top_k=1)[0]
        status = "ok" if best.score < MIN_SIMILARITY else "WOULD ANSWER"
        print(f"  {best.score:.2f} {status:12} {question!r}")

    return 0 if top1 / n >= 0.9 else 1


if __name__ == "__main__":
    sys.exit(main())
