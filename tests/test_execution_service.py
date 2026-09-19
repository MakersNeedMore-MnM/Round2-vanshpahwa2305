import pandas as pd
import pytest

from core.execution_service import DatabaseExecutionError, ExecutionService
from security.query_limits import QueryLimits
from security.validator import ValidatedSQL, validate_sql


class FakeCursor:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.executed_sql: str | None = None
        self.closed = False

    def execute(self, sql: str) -> None:
        self.executed_sql = sql

    def fetchall(self) -> list[dict[str, object]]:
        return self.rows

    def close(self) -> None:
        self.closed = True


class FakeAdapter:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.cursor_instance = FakeCursor(rows)
        self.cursor_calls = 0

    def connect(self) -> None:
        pass

    def ping(self) -> bool:
        return True

    def cursor(self) -> FakeCursor:
        self.cursor_calls += 1
        return self.cursor_instance


def test_execution_requires_validated_sql_and_returns_dataframe() -> None:
    adapter = FakeAdapter([{"city": "Delhi", "sales": 100}])
    service = ExecutionService(adapter, QueryLimits(timeout_seconds=2, max_rows=10))
    validated = validate_sql("SELECT city, SUM(amount) AS sales FROM orders GROUP BY city")

    result = service.execute(validated)

    assert isinstance(result, pd.DataFrame)
    assert result.to_dict(orient="records") == [{"city": "Delhi", "sales": 100}]
    assert "MAX_EXECUTION_TIME(2000)" in adapter.cursor_instance.executed_sql
    assert adapter.cursor_calls == 1
    assert adapter.cursor_instance.closed is True


def test_raw_sql_is_rejected_before_adapter_access() -> None:
    adapter = FakeAdapter([])
    service = ExecutionService(adapter)

    with pytest.raises(TypeError, match="validated"):
        service.execute("SELECT 1")  # type: ignore[arg-type]

    assert adapter.cursor_calls == 0


def test_result_rows_are_bounded() -> None:
    adapter = FakeAdapter([{"id": 1}, {"id": 2}, {"id": 3}])
    service = ExecutionService(adapter, QueryLimits(max_rows=2))
    validated = validate_sql("SELECT id FROM orders", QueryLimits(max_rows=2))

    result = service.execute(validated)

    assert result.to_dict(orient="records") == [{"id": 1}, {"id": 2}]


def test_database_error_is_sanitized() -> None:
    class BrokenCursor(FakeCursor):
        def execute(self, sql: str) -> None:
            raise RuntimeError("password=super-secret host=private-db")

    adapter = FakeAdapter([])
    adapter.cursor_instance = BrokenCursor([])
    validated: ValidatedSQL = validate_sql("SELECT 1")

    with pytest.raises(DatabaseExecutionError, match="demo database query failed") as error:
        ExecutionService(adapter).execute(validated)

    assert "super-secret" not in str(error.value)
