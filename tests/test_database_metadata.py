import pandas as pd

from core.database_metadata import (
    DatabaseMetadataService,
    build_preview_query,
)
from database.schema import ColumnInfo, DatabaseSchema, TableInfo


class FakeCursor:
    def __init__(self, adapter: "FakeAdapter") -> None:
        self.adapter = adapter
        self.rows: list[dict[str, object]] = []

    def execute(self, query: str, params: tuple[object, ...] = ()) -> None:
        self.adapter.queries.append((query, params))
        if "information_schema.TABLES" in query:
            self.rows = [
                {"TABLE_NAME": "customers", "SIZE_BYTES": 1000},
                {"TABLE_NAME": "orders", "SIZE_BYTES": 2000},
            ]
        elif "COUNT(*)" in query and "customers" in query:
            self.rows = [{"ROW_COUNT": 6}]
        elif "COUNT(*)" in query and "orders" in query:
            self.rows = [{"ROW_COUNT": 12}]
        else:
            raise AssertionError(f"Unexpected query: {query}")

    def fetchall(self) -> list[dict[str, object]]:
        return self.rows

    def close(self) -> None:
        pass


class FakeAdapter:
    def __init__(self) -> None:
        self.queries: list[tuple[str, tuple[object, ...]]] = []

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)


def demo_schema() -> DatabaseSchema:
    return DatabaseSchema(
        database="querypeek_demo",
        tables=[
            TableInfo(name="customers", columns=[ColumnInfo("customer_id", "int", False, True)]),
            TableInfo(name="orders", columns=[ColumnInfo("order_id", "int", False, True)]),
        ],
    )


def setup_function() -> None:
    DatabaseMetadataService.clear_cache()


def test_metadata_service_loads_realistic_counts_and_sizes_once() -> None:
    adapter = FakeAdapter()
    service = DatabaseMetadataService(adapter, cache_key="demo")

    first = service.load(demo_schema())
    second = service.load(demo_schema())

    assert first is second
    assert first.total_rows == 18
    assert first.total_size_label == "3.0 KB"
    assert first.largest_table is not None
    assert first.largest_table.name == "orders"
    assert len(adapter.queries) == 3
    assert isinstance(first.rows_frame(), pd.DataFrame)


def test_preview_query_is_validated_and_bounded() -> None:
    query = build_preview_query("customers")

    assert query.sql.upper().startswith("SELECT * FROM `CUSTOMERS`")
    assert query.sql.upper().endswith("LIMIT 10000")
