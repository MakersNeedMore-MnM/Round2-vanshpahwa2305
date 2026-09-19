# QueryPeek

**QueryPeek — Ask your MySQL database questions in plain English.**

QueryPeek is an open-source natural-language-to-SQL analytics application. It retrieves relevant MySQL schema information, generates SQL, validates it, executes it through read-only credentials, and presents SQL, results, and visualization.

## Hackathon MVP

- Python + Streamlit
- MySQL
- SQLGlot
- Pluggable LLM provider
- Plotly

## No MySQL required for demo users

The deployed version should use a hosted synthetic MySQL demo database. A visitor does not need MySQL installed.

For local development, MySQL can run on `localhost:3306`.

**Important:** a deployed cloud application cannot connect to `localhost` on an end user's PC.

## Run locally

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

Configure local `.env` values or Streamlit Cloud secrets for OpenRouter and a
hosted MySQL database. The database account used by QueryPeek must have only
`SELECT` permission. Use [`demo_database/setup.sql`](demo_database/setup.sql)
to create the synthetic demo schema and data.

Example questions:

- Which city generated the highest sales?
- What are the top 3 products by revenue?
- How many orders did each customer place?
- What is the average order value by region?
- Which product category generated the most revenue?
- How much revenue did each employee manage?
- Show monthly sales for the latest year.
- Which customers placed orders over 500?

Read `AGENTS.md` before modifying the project.
