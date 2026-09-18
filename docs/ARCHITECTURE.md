# QueryPeek Architecture

```text
User
  |
  v
Streamlit UI
  |
  v
QueryEngine
  |
  +--> SchemaService --> MySQLAdapter --> MySQL metadata
  +--> SQLGenerator --> LLM Provider
  +--> SQLValidator --> SQLGlot AST
  +--> ExecutionService --> Read-only MySQL
  +--> ResultValidator
  +--> ChartBuilder
  |
  v
SQL + Results + Visualization
```

MySQL is the first supported database. The deployed MVP uses a hosted synthetic MySQL database so users do not need MySQL installed.

A deployed cloud application cannot connect to `localhost` on an end user's computer.

Keep the database adapter replaceable so PostgreSQL/SQLite can be added after the MVP.

LLM output is untrusted and must pass AST validation before execution. The database account must also be read-only.
