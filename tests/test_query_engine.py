import pandas as pd
import pytest

from ai.sql_generator import GeneratedSQL
from core.query_engine import QueryEngine
from security.validator import SQLValidationError


class FakeSchemaService:
    def __init__(self) -> None:
        self.questions: list[str] = []

    def relevant_schema(self, question: str) -> object:
        self.questions.append(question)
        return object()


class FakeGenerator:
    def __init__(self, sql: str) -> None:
        self.sql = sql

    def generate(self, question: str, schema: object) -> GeneratedSQL:
        return GeneratedSQL(self.sql, "fake", "fake-model")


class FakeExecutionService:
    def __init__(self) -> None:
        self.queries: list[object] = []

    def execute(self, query: object) -> pd.DataFrame:
        self.queries.append(query)
        return pd.DataFrame([{"city": "Delhi", "sales": 100}])


def test_query_engine_runs_schema_generation_validation_and_execution() -> None:
    schema = FakeSchemaService()
    execution = FakeExecutionService()
    engine = QueryEngine(schema, FakeGenerator("SELECT 1"), execution)

    result = engine.run("Which city generated the highest sales?")

    assert schema.questions == ["Which city generated the highest sales?"]
    assert result.generated.sql == "SELECT 1"
    assert result.validated.sql.upper().endswith("LIMIT 10000")
    assert len(execution.queries) == 1


def test_invalid_generated_sql_never_reaches_execution() -> None:
    execution = FakeExecutionService()
    engine = QueryEngine(FakeSchemaService(), FakeGenerator("DROP TABLE customers"), execution)

    with pytest.raises(SQLValidationError):
        engine.run("Delete customers")

    assert execution.queries == []
