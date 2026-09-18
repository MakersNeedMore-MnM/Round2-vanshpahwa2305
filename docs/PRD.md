# Product Requirements Document

## Product
QueryPeek

## Problem
Users often need engineering/data teams to answer ad-hoc database questions. QueryPeek lets users ask questions in natural language and inspect the SQL and results instead of requiring them to write SQL manually.

## Core experience
1. Configure a database.
2. Read database metadata.
3. Ask a natural-language question.
4. Retrieve relevant schema context.
5. Generate SQL.
6. Parse and validate SQL.
7. Execute using read-only credentials.
8. Show SQL and results.
9. Show a chart when appropriate.

## MVP success criteria
- MySQL end-to-end.
- Single Streamlit deployment.
- Exact SQL visible.
- Destructive SQL blocked.
- Database account is read-only.
- Common analytical questions work reliably.
- Errors are understandable.
- Demo requires no manual intervention.

## Non-goals
- Database administration.
- Write queries.
- Schema modification.
- Enterprise identity/RBAC.
- Perfect natural-language understanding.

## Principles
Transparency, safety, simplicity, extensibility, and data minimization.
