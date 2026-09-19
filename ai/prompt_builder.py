from database.schema import DatabaseSchema


def build_sql_prompt(question: str, schema: DatabaseSchema) -> str:
    """Build a schema-grounded prompt for MySQL SQL generation."""

    schema_lines: list[str] = []
    for table in schema.tables:
        schema_lines.append(f"TABLE {table.name}")
        for column in table.columns:
            attributes = [column.data_type]
            if column.is_primary_key:
                attributes.append("PRIMARY KEY")
            if not column.nullable:
                attributes.append("NOT NULL")
            schema_lines.append(f"  - {column.name}: {', '.join(attributes)}")
        for foreign_key in table.foreign_keys:
            schema_lines.append(
                "  - FOREIGN KEY "
                f"{foreign_key.column_name} REFERENCES "
                f"{foreign_key.referenced_table}({foreign_key.referenced_column})"
            )

    schema_context = "\n".join(schema_lines) or "(No tables were retrieved.)"
    return f"""You generate SQL for QueryPeek.

SQL dialect: MySQL.
The SQL output will be parsed and validated for read-only safety before it is
eligible for execution. Treat the schema below as the only available database
context. Use only the listed tables and columns.

Rules:
- Generate exactly one read-only SELECT statement.
- Do not generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE,
  GRANT, REVOKE, transaction control, stored procedures, or multiple statements.
- Do not invent tables or columns.
- Return SQL only, without explanations or Markdown fences.

Relevant schema:
{schema_context}

User question:
{question}
""".strip()
