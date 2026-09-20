# QueryPeek

**Ask your MySQL database questions in plain English. Get validated SQL, results, and charts.**

QueryPeek is an open-source, AI-powered data exploration app. It reads your database schema, generates SQL from a natural-language question, validates it, executes it through read-only credentials, and presents the SQL, the results, and a visualization.

> **Status: Working prototype.** This Streamlit app demonstrates the core pipeline end to end. The full MVP and production frontend are the next phase (see [Roadmap](#roadmap)).

<!-- Add a screenshot or GIF of the AI Copilot here -->
<!-- ![QueryPeek demo](docs/demo.gif) -->

**Live demo:** _add link here_

---

## Table of Contents

- [Why QueryPeek](#why-querypeek)
- [How It Works](#how-it-works)
- [Features](#features)
- [Security Model](#security-model)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Example Questions](#example-questions)
- [Project Structure](#project-structure)
- [Development](#development)
- [Roadmap](#roadmap)
- [Contributing](#contributing)

---

## Why QueryPeek

Databases hold the answers, but getting them requires SQL, schema knowledge, joins, and aggregations. That locks out non-technical users, business teams, students, analysts, and developers working in unfamiliar schemas.

Ask *"Which city generated the highest sales?"* and QueryPeek understands the question, finds the relevant tables, writes the SQL, validates it, runs it safely, and shows you the answer.

---

## How It Works

```
Natural-language question
          ↓
  Schema retrieval (MySQL introspection)
          ↓
  SQL generation (Google Gemini)
          ↓
  SQL validation (SQLGlot)
          ↓
  Read-only, bounded execution
          ↓
  Result processing (Pandas)
          ↓
  Visualization (Plotly)
```

**Core design principle:** AI-generated SQL is untrusted input. It must never become an uncontrolled database operation.

---

## Features

**Database integration (MySQL)**
- Connection handling and health checks
- Schema introspection: tables, columns, primary keys, foreign keys
- Row counts and database metadata
- Read-only access

**AI SQL generation**
- Google Gemini generates MySQL-compatible SQL from your question
- Relevant schema is supplied as context
- Generation is fully separated from execution
- Automatic query repair on failure (configurable retries)

**Safe execution**
- Query timeouts and result-row limits
- Pandas-based result processing
- Error handling and safe table previews

**Visualization**
- Bar, line, scatter, and donut charts (Plotly)

**Dashboard**
- Connection status and database overview
- Table explorer, schema viewer, and ER relationship information
- AI Copilot showing generated SQL, validated SQL, results, charts, and security feedback

---

## Security Model

QueryPeek uses defense in depth so generated SQL cannot modify your data.

| Layer | Protection |
|---|---|
| **1. SQL validator** | SQLGlot parses the query and rejects anything that is not a permitted read-only statement. Blocks `DELETE`, `UPDATE`, `INSERT`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `REVOKE`. |
| **2. Read-only DB user** | The app connects with a dedicated MySQL account that has only `SELECT` permission. |
| **3. Execution limits** | Query timeout (`QUERY_TIMEOUT_SECONDS`) and row cap (`MAX_ROWS`). |

Tested example:

> **Prompt:** "Delete all customers."
> **Result:** Rejected by the validator before it reaches the database.

Always connect with a dedicated read-only database user in any deployment.

---

## Architecture

```
┌───────────────────┐
│       User        │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│   Web Frontend    │   Streamlit today → Node.js web app planned
└─────────┬─────────┘
          ▼
┌───────────────────┐
│    AI Copilot     │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Schema Retrieval  │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│   SQL Generator   │   Gemini (pluggable LLM provider)
└─────────┬─────────┘
          ▼
┌───────────────────┐
│  SQL Security     │
│    Validator      │   SELECT only
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Database Adapter  │   MySQL today, more engines planned
└─────────┬─────────┘
          ▼
┌───────────────────┐
│     Database      │
└───────────────────┘
```

The LLM layer is provider-configurable (`LLM_PROVIDER`), and the database layer is built around an adapter approach so additional engines can be added without changing the rest of the pipeline.

---

## Tech Stack

| Component | Prototype | Planned |
|---|---|---|
| Frontend | Streamlit | Node.js web application |
| Language | Python | Python + expanded agent layer |
| AI | Google Gemini (`google-genai`) | Expanded AI / agent capabilities |
| Database | MySQL | + PostgreSQL, SQLite, SQL Server |
| SQL parsing / validation | SQLGlot | Sandboxing + permission controls |
| Data processing | Pandas | Advanced analytics |
| Visualization | Plotly | Interactive dashboards |
| DB driver | MySQL Connector/Python | Per-engine adapters |
| Config / models | python-dotenv, Pydantic | Same |
| Testing / linting | Pytest, Ruff | Same |

---

## Quick Start

### No MySQL needed for demo users

The deployed app uses a hosted synthetic MySQL demo database, so visitors do not need MySQL installed.

> **Note:** a cloud-deployed app cannot connect to `localhost` on an end user's machine. For deployment, use a hosted MySQL instance.

### Prerequisites

- Python 3.10+
- A MySQL database (local or hosted) with a **SELECT-only** user
- A Google Gemini API key

### Run locally

```bash
git clone https://github.com/MakersNeedMore-MnM/Round2-vanshpahwa2305.git
cd Round2-vanshpahwa2305

python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1

pip install -r requirements.txt

cp .env.example .env               # Windows: copy .env.example .env
# edit .env with your database and Gemini credentials

streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

### Set up the demo database

Create the synthetic demo schema and data with [`demo_database/setup.sql`](demo_database/setup.sql). It creates tables such as `customers`, `employees`, `orders`, and `products`.

```bash
mysql -u root -p < demo_database/setup.sql
```

Then create a read-only user:

```sql
CREATE USER 'readonly_user'@'%' IDENTIFIED BY 'strong_password';
GRANT SELECT ON querypeek_demo.* TO 'readonly_user'@'%';
FLUSH PRIVILEGES;
```

### Deploying on Streamlit Cloud

Add the same values from `.env.example` as Streamlit secrets, pointing `DEMO_DATABASE_HOST` at a hosted MySQL instance.

---

## Configuration

Set these in `.env` locally, or as Streamlit Cloud secrets when deployed.

| Variable | Description | Default in `.env.example` |
|---|---|---|
| `DEMO_DATABASE_HOST` | MySQL host | `localhost` |
| `DEMO_DATABASE_PORT` | MySQL port | `3306` |
| `DEMO_DATABASE_NAME` | Database name | `querypeek_demo` |
| `DEMO_DATABASE_USER` | MySQL user (must be **SELECT-only**) | `readonly_user` |
| `DEMO_DATABASE_PASSWORD` | MySQL password | *(empty)* |
| `LLM_PROVIDER` | LLM provider | `gemini` |
| `GEMINI_API_KEY` | Google Gemini API key | *(empty)* |
| `LLM_MODEL` | Model name | see `.env.example` |
| `QUERY_TIMEOUT_SECONDS` | Max query execution time | `10` |
| `MAX_ROWS` | Max rows returned | `10000` |
| `MAX_REPAIR_RETRIES` | Auto-repair attempts for failed SQL | `2` |

Never commit `.env` or credentials to version control.

---

## Example Questions

- Which city generated the highest sales?
- What are the top 3 products by revenue?
- How many orders did each customer place?
- What is the average order value by region?
- Which product category generated the most revenue?
- How much revenue did each employee manage?
- Show monthly sales for the latest year.
- Which customers placed orders over 500?

Try a destructive request too:

> **Delete all customers.** → Rejected by the security validator; nothing is executed.

---

## Project Structure

```
.
├── app.py               # Streamlit entry point
├── ai/                  # LLM integration and SQL generation
├── core/                # Core application logic
├── database/            # MySQL connection, health checks, schema introspection
├── security/            # SQL validation
├── visualization/       # Plotly chart generation
├── demo_database/       # Synthetic demo schema and data (setup.sql)
├── tests/               # Pytest suite
├── docs/                # Documentation
├── .streamlit/          # Streamlit configuration
├── .env.example         # Environment variable template
├── requirements.txt
├── pyproject.toml       # Tooling configuration
├── AGENTS.md            # Guidelines for contributors and coding agents
└── TASKS.md             # Task tracking
```

---

## Development

```bash
# Run tests
pytest

# Lint
ruff check .

# Format
ruff format .
```

Read [`AGENTS.md`](AGENTS.md) before modifying the project.

---

## Roadmap

### Phase 1: Prototype (current)

- [x] MySQL integration and schema introspection
- [x] Gemini SQL generation
- [x] SQL security validation
- [x] Read-only, bounded execution
- [x] Query results and basic visualization
- [x] Database dashboard
- [x] Streamlit deployment

### Phase 2: MVP (next)

- [ ] Dedicated Node.js web frontend
- [ ] Conversational Copilot with follow-ups (e.g. *"What were the top 3 products in that city?"*)
- [ ] Query history and saved queries
- [ ] Smarter visualization selection
- [ ] Authentication and workspaces
- [ ] Improved error recovery
- [ ] Query explanations
- [ ] Production-grade, responsive UX

### Phase 3: Advanced platform

- [ ] Multiple database engines (PostgreSQL, SQLite, SQL Server)
- [ ] Query intelligence: performance analysis, index recommendations, expensive-query detection
- [ ] AI-generated insights from results
- [ ] Dashboard builder and sharing
- [ ] CSV / Excel / PDF export
- [ ] Enterprise security: sandboxing, per-user permissions, audit logs, secure credential management

---

## Vision

QueryPeek is not meant to be only an AI SQL generator. The goal is an AI-powered database interaction and analytics platform where people talk to their data naturally.

```
Ask a question → Understand the database → Generate & validate SQL
      → Execute safely → Understand the result → Discover insights
```

---

## Contributing

1. Fork the repository
2. Create a branch: `git checkout -b feature/your-feature`
3. Make your changes and add tests
4. Run `pytest` and `ruff check .`
5. Open a pull request

Please open an issue first for large changes.

---

## License

Add your license here (e.g. MIT).
