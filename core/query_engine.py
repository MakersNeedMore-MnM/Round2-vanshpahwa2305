from dataclasses import dataclass

import pandas as pd

from ai.sql_generator import GeneratedSQL, SQLGenerator
from core.execution_service import ExecutionService
from core.schema_service import SchemaService
from security.query_limits import QueryLimits
from security.validator import ValidatedSQL, validate_sql


@dataclass(frozen=True)
class QueryResult:
    """Transparent result of one safe QueryPeek request."""

    question: str
    generated: GeneratedSQL
    validated: ValidatedSQL
    rows: pd.DataFrame


class QueryEngine:
    """Minimal orchestration seam for schema retrieval and SQL generation."""

    def __init__(
        self,
        schema_service: SchemaService,
        sql_generator: SQLGenerator,
        execution_service: ExecutionService | None = None,
        limits: QueryLimits | None = None,
    ) -> None:
        self.schema_service = schema_service
        self.sql_generator = sql_generator
        self.execution_service = execution_service
        self.limits = limits or QueryLimits()

    def generate_sql(self, question: str) -> GeneratedSQL:
        """Retrieve relevant schema and generate SQL; do not execute the result."""

        schema = self.schema_service.relevant_schema(question)
        return self.sql_generator.generate(question, schema)

    def run(self, question: str) -> QueryResult:
        """Run the complete safe MVP flow for one natural-language question."""

        if self.execution_service is None:
            raise RuntimeError("QueryEngine requires an execution service to run queries.")

        generated = self.generate_sql(question)
        validated = validate_sql(generated.sql, self.limits)
        rows = self.execution_service.execute(validated)
        return QueryResult(
            question=question,
            generated=generated,
            validated=validated,
            rows=rows,
        )
