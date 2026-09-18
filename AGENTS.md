# QueryPeek — Codex Project Instructions

## Mission
Build QueryPeek as a hackathon-ready, open-source natural-language-to-SQL analytics application.

The primary goal is a reliable working demo that can be deployed as ONE Python web application within 3 days.

## Non-negotiable architecture
- Python-first application.
- Streamlit is the UI and application entrypoint.
- Do NOT create a separate React frontend.
- Do NOT create a separate FastAPI service for the MVP.
- Keep business logic outside `app.py`.
- MySQL is the first supported database.
- Database adapters must be designed so MySQL/SQLite can be added later.
- LLM provider/model must be replaceable through a small interface.
- Use SQLGlot (or another AST-capable SQL parser) for SQL validation.
- Enforce read-only behavior at BOTH application validation and database-permission levels.
- Never execute arbitrary model-generated SQL without validation.
- Never store secrets in source control.
- Prefer small, testable modules over large files.

## MVP flow
User question -> schema retrieval -> SQL generation -> SQL AST/security validation -> read-only database execution -> result validation -> optional SQL repair (maximum 2 retries) -> table/chart response.

## Product requirements
1. Connect to MySQL.
2. Inspect and cache database schema.
3. Accept a natural-language question.
4. Generate dialect-aware SQL.
5. Show exact generated SQL.
6. Reject destructive/non-read-only SQL.
7. Execute validated SQL with limits/timeouts.
8. Display results as a table.
9. Generate a basic visualization when appropriate.
10. Display useful errors without exposing secrets.
11. Deploy as a single Streamlit application.
12. Include demo/example questions.

## Security requirements
- SELECT-only policy for MVP.
- Reject multiple statements.
- Reject DDL/DML and other write operations.
- Use a dedicated read-only MySQL role for demo/production database access.
- Apply query timeout and row limits.
- Never concatenate untrusted values into SQL.
- Never log passwords, connection strings, API keys, or full sensitive result sets.
- Do not send raw database rows to an LLM by default; prefer schema/metadata context.
- Treat LLM output as untrusted input.

## Coding standards
- Python 3.11+.
- Type hints for public functions.
- Small functions with clear names.
- No silent exception swallowing.
- UI code in `app.py` and `ui/` if added.
- Database code in `database/`.
- AI code in `ai/`.
- Security code in `security/`.
- Orchestration in `core/`.
- Add tests for security-critical behavior.
- Avoid premature abstractions.
- Do not add dependencies unless they solve a real requirement.

## Development workflow
Before implementing a feature, read `AGENTS.md`, `docs/PRD.md`, `docs/ARCHITECTURE.md`, and `TASKS.md`; inspect existing code; make the smallest change; run relevant tests; update docs when architecture/setup changes.

## 3-day priority rule
Prefer reliability over feature breadth. Defer multi-database support, authentication, RBAC, vector databases, distributed inference, and enterprise features until the core demo works. Never sacrifice SQL safety for speed.

## Definition of Done
A fresh clone can install dependencies, configure secrets, start Streamlit, connect to demo MySQL, ask a natural-language question, generate/validate/execute SQL safely, show SQL + result + chart, pass tests, and deploy as one Streamlit application.

## Git discipline
Make small logical commits. Never commit `.env`, credentials, secret database dumps, or generated caches.
