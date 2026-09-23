# nl2sql-insight-chatbot

![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## Overview

The **nl2sql-insight-chatbot** is an intelligent assistant designed to transform natural language queries into SQL commands that can be executed against a database. This Python-based chatbot utilizes advanced machine learning models and data manipulation capabilities to provide comprehensive data retrieval from a SQLite database.

## Features

- Converts natural language questions to SQL queries.
- Executes SQL queries against a SQLite database.
- Supports embedding generation and data retrieval through modular components.
- Leverages Google GENAI for advanced natural language understanding.
- Easy integration and setup via environment variables.

## Technology Stack

- **Programming Language**: Python 3.8+
- **Libraries**:
  - NumPy
  - Pandas
  - Google GENAI
  - Python-dotenv for environment management
- **Database**: SQLite (northwind.db)

## Repository Structure

```
nl2sql-insight-chatbot/
├── .env.example
├── .gitignore
├── .python-version
├── README.md
├── api_key_manager.py
├── app.py
├── build_index.py
├── data/
│   └── northwind.db
├── descriptions.csv
├── eval_retrieval.py
├── index/
│   ├── embeddings.npy
│   └── index_meta.json
├── main.py
├── nl2sql/
│   ├── __init__.py
│   ├── answerer.py
│   ├── config.py
│   ├── embeddings.py
│   ├── executor.py
│   ├── guardrails.py
│   ├── llm.py
│   ├── pipeline.py
│   ├── repository.py
│   ├── retriever.py
│   └── sql_generator.py
├── pyproject.toml
├── queries/
│   ├── q01_total_revenue.sql
│   ├── q02_sales_last_month.sql
│   └── ...
├── requirements.txt
├── test_guardrails.py
└── uv.lock
```

## System Architecture & Application Workflow

```mermaid
graph TD;
    A[User Input] --> B[NLP Module];
    B --> C[Query Generation];
    C --> D[SQL Execution];
    D --> E[Database (northwind.db)];
    E --> F[Return Results];
    F --> A;
```

## Installation & Setup Instructions

Follow the steps below to set up and run the project:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/nl2sql-insight-chatbot.git
   cd nl2sql-insight-chatbot
   ```

2. **Set up a Python virtual environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate # On Windows use `venv\Scripts\activate`
   ```

3. **Install the dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a `.env` file**:
   Copy `.env.example` to `.env` and fill in the required environment variables:
   ```dotenv
   GEMINI_API_KEY=your_api_key_here
   ```

5. **Run the application**:
   ```bash
   python app.py
   ```

## Environment/Configuration Requirements

- **GEMINI_API_KEY**: Required for integration with the Google GENAI service.
- Optional environment configurations for model versions can also be specified.

## API Documentation

### Endpoints
#### POST /query
- **Description**: Accepts a natural language query and returns the SQL query and result.

- **Request**:
  ```json
  {
    "question": "What is the total revenue?"
  }
  ```

- **Response**:
  ```json
  {
    "sql": "SELECT SUM(revenue) FROM sales;",
    "result": [...]
  }
  ```

## Database Information

The application uses an SQLite database named `northwind.db`. This database contains various tables relevant to sales, customers, and products.

### Schema
Basic tables include:
- **Sales**: Contains sales transactions.
- **Customers**: Stores customer information.
- Additional tables available for queries in the `queries/` directory.

## Important Classes, Functions, and Modules

- `answerer.py`: Generates answers from queries.
- `sql_generator.py`: Constructs SQL queries from natural language.
- `retriever.py`: Retrieves data based on SQL queries.

## Code Execution Flow

1. The user inputs a question.
2. The NLP module processes the input and generates a SQL query.
3. The execution module runs the SQL command against the SQLite database.
4. Results are returned to the user in a readable format.

## Testing Instructions

To run the tests, execute:
```bash
pytest test_guardrails.py
```
You can also include additional data evaluation tests as needed.

## Deployment Instructions

Deployment is manual. Ensure all dependencies are installed, and the production environment is set up correctly using the instructions above. Code can be deployed using various methods, such as through a simple Python server or cloud services.

## Troubleshooting & Common Issues

- **Missing API Key**: Ensure `GEMINI_API_KEY` is correctly set in the `.env` file.
- **Database Connection Failed**: Verify that `northwind.db` is present in the `data/` folder.

## Usage Examples

### Example Code Snippet
```python
import requests

json_data = {
    "question": "What is the total revenue?"
}
response = requests.post("http://localhost:5000/query", json=json_data)
print(response.json())
```

## Contributing

Please refer to the `CONTRIBUTING.md` for guidelines on how to contribute to this project.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
