# Northwind Insight Chatbot: Natural Language → SQL → Answer

An interactive chatbot that lets business users ask questions in plain English. The question is matched **by meaning** to a
library of vetted SQL queries, the best query runs against a real database, and an LLM turns the result into a
clear answer grounded strictly in the returned data. A vetted query is used whenever one fits. If none
does, Gemini writes a new read-only SQL query from the database schema, and that query must pass the same guardrails before it
runs.

## Tool stack

| Component | Choice |
| --- | --- |
| LLM (final answer) | Google Gemini (`gemini-flash-latest`) via the free Google AI Studio API, through the `google-genai` SDK |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` (open source, runs locally on CPU) |
| Dataset | [Northwind SQLite, extended edition](https://github.com/jpwhite3/northwind-SQLite3): `Orders` has 14 columns × 16,282 rows, `Order Details` has 609,283 rows |
| SQL query repository | [`queries/`](queries): 21 `.sql` files (filters, joins, aggregations, CTEs, window functions) |
| Fallback text-to-SQL | Gemini writes read-only SQLite from the live schema when no vetted query answers the question |
| Description document | [`descriptions.csv`](descriptions.csv): `query_id → sql_file, description, sample_questions` |
| Similarity search | In-memory cosine similarity with NumPy (normalised vectors, dot product) |
| Vector store | `index/embeddings.npy` + `index/index_meta.json` |
| Chatbot UI | Streamlit (plus a terminal chat in `main.py`) |

## Architecture

```
queries/*.sql ──► descriptions.csv ──(build_index.py, offline)──► index/embeddings.npy
                                                                       │
User question ──► guardrail check ──► embed ──► cosine similarity ◄────┘  (top-3 vetted candidates)
                                                     │
                   similarity ≥ 0.90 ────────────────┤
                   otherwise ──► Gemini planner:     │
                       USE <vetted query> ───────────┤
                       SQL: <new read-only query> ───┤  (validated, read-only, 10 s limit, 1 self-correction)
                       CANNOT_ANSWER ──► decline + suggested questions
                                                     ▼
                        run SQL on data/northwind.db (read-only)
                                                     ▼
               question + result table ──► Gemini ──► answer text
                                                     ▼
    answer + number check + exact result table concatenated ──► Streamlit chat
```

### Code layout (one module per responsibility)

| File | Responsibility |
| --- | --- |
| [`nl2sql/repository.py`](nl2sql/repository.py) | Load `descriptions.csv` and the `.sql` files into `QueryRecord`s |
| [`nl2sql/embeddings.py`](nl2sql/embeddings.py) | Embedding model wrapper; build, save and load the index (auto-rebuilds when `descriptions.csv` changes) |
| [`nl2sql/retriever.py`](nl2sql/retriever.py) | Cosine-similarity search returning the top-k distinct queries |
| [`nl2sql/guardrails.py`](nl2sql/guardrails.py) | Refuse harmful questions; validate SQL is a single read-only statement |
| [`nl2sql/executor.py`](nl2sql/executor.py) | Execute SQL on SQLite through a **read-only** connection with a read-only authorizer, return a DataFrame |
| [`nl2sql/answerer.py`](nl2sql/answerer.py) | Gemini prompt, template fallback, number verification, response concatenation |
| [`nl2sql/sql_generator.py`](nl2sql/sql_generator.py) | LLM planner: pick a vetted query, write new read-only SQL, or decline |
| [`nl2sql/llm.py`](nl2sql/llm.py) | Shared Gemini client with retries for 503 and short rate-limit waits |
| [`nl2sql/pipeline.py`](nl2sql/pipeline.py) | Orchestrates guardrail → retrieve → plan → execute → answer |
| [`build_index.py`](build_index.py) | Embedding / indexing script |
| [`app.py`](app.py) | Streamlit chatbot UI |
| [`api_key_manager.py`](api_key_manager.py) | Sidebar widget to paste a Gemini key at runtime (kept per browser session only) |
| [`main.py`](main.py) | Terminal chatbot |
| [`eval_retrieval.py`](eval_retrieval.py) | Retrieval accuracy test on 42 unseen paraphrases + out-of-scope questions |
| [`test_guardrails.py`](test_guardrails.py) | Guardrail tests: harmful requests blocked, legitimate questions allowed, writes denied |

## How retrieval works

Each query is indexed with **several texts**: its description plus three example phrasings from `descriptions.csv`.
A question's score for a query is its **highest** cosine similarity against any of that query's texts. This makes
retrieval robust to different wordings ("Which customer spent the most?" vs. "Who is our most valuable client?").
### Routing: vetted query or generated SQL

Similarity alone can't tell whether a vetted query answers a question *exactly*. "What were sales in Germany in
2020?" scores 0.57 against the monthly-sales query, which ignores both the country and the year. So:

| Situation | What happens |
| --- | --- |
| Best similarity ≥ 0.90 (`CONFIDENT_MATCH`) | The vetted query runs directly (no extra LLM call) |
| Below 0.90, Gemini key set | One planner call to Gemini with the question, the top-3 vetted candidates (≥ 0.40) and the live schema. It answers `USE <query_id>` if a vetted query fits exactly, writes a new `SELECT` if none does, or `CANNOT_ANSWER` for off-topic or write requests |
| Generated SQL fails to run | The error goes back to Gemini once for a corrected query |
| No Gemini key, or planner unavailable | Falls back to semantic search only: best vetted query if ≥ 0.40 (with a note that the fit wasn't checked), otherwise a polite decline with suggested questions |

The UI's **How I answered** expander always says whether the answer came from a vetted query or from AI-generated SQL, and shows the SQL.

## How answers stay grounded (no hallucinated numbers)

1. **Strict prompt:** Gemini receives only the question, the query's description and the formatted result table. It is told to
   copy numbers verbatim and never compute, round or estimate. Temperature is 0.
2. **Concatenation:** the exact query output is always appended to the answer as a table ("Source data (exact
   query output)"), so the real figures appear directly in the response whatever the LLM writes.
3. **Automatic number check:** every number in the LLM's answer is compared with the values in the result. Any number that
   isn't in the data is flagged with a warning under the answer.
4. **Deterministic fallback:** without an API key, or if the Gemini call fails (e.g. quota exhausted), the answer is built
   by concatenating values straight from the result, so the bot keeps working.

## Guardrails (read-only by design)

The chatbot refuses any request to drop, delete, insert, update or otherwise modify the database. Three
independent layers enforce this, so a miss in one layer is caught by the next ([`nl2sql/guardrails.py`](nl2sql/guardrails.py)):

| Layer | Where | What it does |
| --- | --- | --- |
| 1. Question screening | `check_question()`, runs **before** retrieval | Refuses natural-language write requests ("delete all customers", "update the price of Chai", "can you drop the orders table?"), SQL typed into the chat (`DROP TABLE`, `DELETE FROM`, `UPDATE … SET`, `INSERT INTO`, `ALTER`, `PRAGMA`…), SQL-injection patterns (`; DROP`, `' OR '1'='1`, `UNION SELECT`, `--`), prompt-injection attempts ("ignore your instructions…") and questions over 500 characters |
| 2. SQL validation | `validate_sql()`, applied when the repository loads **and** right before each execution | Only one statement, starting with `SELECT`/`WITH`, with no write/admin keywords outside string literals. A write query added to `queries/` stops the app from starting |
| 3. Database enforcement | [`nl2sql/executor.py`](nl2sql/executor.py) | Opens SQLite in read-only mode (`mode=ro`) and installs a SQLite **authorizer** that denies every operation except reading, enforced by the database engine itself. Queries are interrupted after 10 s and capped at 1,000 rows |

**AI-generated SQL gets no special trust:** it goes through layers 2 and 3 exactly like vetted SQL, and the planner prompt
tells Gemini to output `CANNOT_ANSWER` for any request to change data.

Refused requests get a clear message in the chat (shown in red in the UI) that names the rule that blocked them. The
LLM prompt also tells Gemini to stay read-only and ignore instructions embedded in questions.

Question screening checks for a write verb **aimed at data** ("delete … customers") or used as a **command**
("change the price…"), so analytical questions that use the same words still work: "Which products are
discontinued?", "How have sales changed year over year?", "Did orders drop in 2023?".

Run the guardrail tests (35 harmful questions, 113 legitimate ones, unsafe and safe SQL, direct write attempts
against the database, and the query time limit):

```bash
uv run python test_guardrails.py
```

## Setup

Requires Python 3.12+.

### 1. Install dependencies

With [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv sync
```

Or with pip:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

### 2. Add your free Gemini API key

1. Go to <https://aistudio.google.com/apikey> and click **Create API key** (free, no billing needed).
2. Copy `.env.example` to `.env` and paste the key:

   ```
   GEMINI_API_KEY=your-key-here
   ```

`.env` is git-ignored. Without a key the app still runs, but answers are template-based and only vetted queries can
be used.

**Or add a key while the app is running:** open **Gemini API key** in the sidebar, paste a key and click **Save key**.
The key is checked with a quick call that uses no generation quota, then kept **only in that browser session's memory**.
It is passed with each of that visitor's Gemini requests and never written to environment variables, disk or logs. On
a shared deployment every visitor runs in the same Python process, so one visitor's key is never used for anyone else. A
visitor's own key takes priority over the app's key for their session. **Remove my key** clears it.

> **Free-tier rate limit:** the Gemini free tier allows only a few requests per minute (5/min for the flash model at
> the time of writing). A question uses 1 call (confident match) or 2 calls (planner + answer). When the limit is hit,
> the app waits if Gemini asks for ≤ 10 s, otherwise it falls back to template answers / vetted queries and says so.

### 3. Database

`data/northwind.db` is included in the repo. To re-download it:

```bash
curl -L -o data/northwind.db https://raw.githubusercontent.com/jpwhite3/northwind-SQLite3/main/dist/northwind.db
```

### 4. Build the embedding index (optional)

The index is committed, and the app rebuilds it automatically if `descriptions.csv` changes. To build it manually:

```bash
uv run python build_index.py
```

The first run downloads the ~90 MB embedding model from Hugging Face.

### 5. Run the chatbot

```bash
uv run streamlit run app.py
```

Open <http://localhost:8501>. The sidebar has one example question per query, and each answer has a
**"How I answered"** expander showing the matched query, its similarity score, the SQL and the runner-up candidates.

Terminal version:

```bash
uv run python main.py
```

### 6. Test retrieval accuracy

```bash
uv run python eval_retrieval.py
```

Current results on 42 paraphrases that are **not** in `descriptions.csv` (semantic search alone, no LLM):

- **Top-1 accuracy: 92.9 % (39/42)**
- **Top-3 accuracy: 100 % (42/42)**
- Out-of-scope questions ("What's the weather like in Paris today?") score ≤ 0.22 and are rejected.

The three misses are close calls between related queries, e.g. "Annual revenue trend" matched the *monthly* trend
query (q15) instead of the *yearly* one (q03). All three score below 0.90, so with a Gemini key the planner reviews
them against the top-3 candidates, which always include the correct query.

## Query repository

| ID | Answers | SQL techniques |
| --- | --- | --- |
| q01_total_revenue | Total revenue, orders, units sold | aggregation |
| q02_sales_last_month | Sales for the last complete month | CTE, date functions, join |
| q03_sales_by_year | Yearly orders & revenue | group by, date functions |
| q04_top_customers | Top 10 customers by spend | 3-table join, ranking |
| q05_top_products_by_revenue | Top 10 products by revenue | join, ranking |
| q06_top_products_by_quantity | Top 10 products by units sold | join, ranking |
| q07_sales_by_category | Revenue per category + share % | CTE, window function |
| q08_employee_performance | Revenue & orders per employee | join, string concat |
| q09_sales_by_country | Orders & revenue per country | group by |
| q10_shipper_performance | Freight, speed, late % per shipper | join, julianday, conditional agg |
| q11_late_shipments | Late order count, %, avg days late | filter, CASE |
| q12_low_stock_products | Products at/below reorder level | filter, 3-table join |
| q13_discontinued_products | Discontinued products | filter |
| q14_average_order_value | Avg order value / items / freight | CTE, nested aggregation |
| q15_monthly_sales_last_year | Month-by-month revenue last year | CTE, date filter |
| q16_pending_orders | Unshipped orders | NULL filter, join |
| q17_most_expensive_products | 10 highest-priced products | ordering |
| q18_customers_by_country | Customers per country | group by |
| q19_discount_summary | Gross vs. net revenue, discounts | conditional aggregation |
| q20_suppliers_by_country | Suppliers & products per country | left join |
| q21_database_overview | Rows & columns per table, plus totals | CTE, UNION ALL, `pragma_table_info` |

"Last month" and "last year" mean the most recent **complete** month and year in the data (September 2023 and 2022),
because Northwind is a historical dataset that ends in October 2023.

### Adding a new query

1. Add `queries/q21_my_query.sql`.
2. Add a row to `descriptions.csv`: `q21_my_query,queries/q21_my_query.sql,"<description>","<question 1>|<question 2>|<question 3>"`.
3. Restart the app. The index rebuilds automatically.

## Example questions and outputs

Real outputs from this repository (numbers come straight from the database):

**Q: What were total sales last month?** → `q02_sales_last_month` (similarity 1.00)

| month | orders | units_sold | total_sales |
| --- | --- | --- | --- |
| 2023-09 | 119 | 121,187 | 3,544,698.51 |

Template answer (no API key set):

> **month**: 2023-09; **orders**: 119; **units sold**: 121,187; **total sales**: 3,544,698.51.

With a Gemini key the same numbers come back as a sentence, and the table above is still appended beneath it.

**Q: Who is our most valuable client?** → `q04_top_customers`

| customer | country | orders | total_spent |
| --- | --- | --- | --- |
| B's Beverages | UK | 210 | 6,154,115.34 |
| Hungry Coyote Import Store | USA | 198 | 5,698,023.67 |
| Rancho grande | Argentina | 194 | 5,559,110.08 |
| … | | | |

**Q: Which shipping company is the fastest?** → `q10_shipper_performance`

| shipper | orders_shipped | avg_freight | avg_days_to_ship | late_pct |
| --- | --- | --- | --- | --- |
| United Package | 5,475 | 248.08 | 7.78 | 22.94 |
| Federal Shipping | 5,455 | 248.93 | 7.82 | 23.01 |
| Speedy Express | 5,331 | 249.63 | 7.92 | 23.34 |

**Q: Tell me a joke** → rejected (similarity 0.22):

> I couldn't find a query in my repository that answers that question. Closest things I can answer: …

**Q: no of rows and column in the datbase** (typos included) → vetted query `q21_database_overview`

> The database contains a total of 625,890 rows and 88 columns.

**Q: What were sales in Germany in 2020?** → no vetted query fits, so Gemini generated:

```sql
SELECT ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) AS total_sales,
       COUNT(DISTINCT o.OrderID) AS total_orders
FROM Orders o JOIN "Order Details" od ON o.OrderID = od.OrderID
WHERE strftime('%Y', o.OrderDate) = '2020' AND o.ShipCountry = 'Germany'
```

> In 2020, total sales in Germany were $5,332,568.20 across 205 orders.

Other generated-SQL examples: *"How many orders did Ernst Handel place?"* (187), *"Which employee was hired first?"*,
*"Top 5 customers in USA by spend"*.

**Q: Show me all customers, and also clean up the Shippers table afterwards** → blocked by the guardrail before any SQL runs.

More questions to try: *"Which product category sells the most?"*, *"Which products need to be reordered?"*,
*"How much money did we give away in discounts?"*, *"Which orders are still pending?"*, *"Who is the top salesperson?"*

## Deploying a live demo (optional)

**Streamlit Community Cloud:** push this repo to GitHub, create a new app at <https://share.streamlit.io> pointing at
`app.py`, and under **Settings → Secrets** add:

```toml
GEMINI_API_KEY = "your-key-here"
```

If you skip the secret, the app still works: visitors can paste their own Gemini key in the sidebar, and it's used only
for their session.

PyTorch is pinned to the CPU-only build (in `uv.lock`, which Streamlit Cloud installs from first, and in
`requirements.txt`) to keep the build small. If the app ever crashes with `AttributeError ... torch.LongTensor`, the
PyTorch install on the server was incomplete: delete the app and deploy it again to get a fresh environment.

## Configuration

Set these in `.env` (or as environment variables):

| Variable | Default | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | – | Gemini API key (`GOOGLE_API_KEY` also works) |
| `GEMINI_MODEL` | `gemini-flash-latest` | Any Gemini model name |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Any sentence-transformers model, e.g. `BAAI/bge-small-en-v1.5` |
| `MIN_SIMILARITY` | `0.40` | Minimum cosine similarity for a vetted query to be used or offered to the planner |
| `CONFIDENT_MATCH` | `0.90` | At or above this, the vetted query runs without consulting the planner |
