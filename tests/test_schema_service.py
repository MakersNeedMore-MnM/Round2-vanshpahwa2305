from core.schema_service import SchemaService
from database.schema import ColumnInfo, DatabaseSchema, ForeignKeyInfo, TableInfo


class FakeAdapter:
    def __init__(self, schema: DatabaseSchema, key: str) -> None:
        self.schema = schema
        self.key = key
        self.inspect_calls = 0

    def inspect_schema(self) -> DatabaseSchema:
        self.inspect_calls += 1
        return self.schema


def demo_schema(database: str = "demo") -> DatabaseSchema:
    return DatabaseSchema(
        database=database,
        tables=[
            TableInfo(
                name="customers",
                columns=[
                    ColumnInfo("customer_id", "int", False, True),
                    ColumnInfo("region", "varchar", True),
                ],
            ),
            TableInfo(
                name="orders",
                columns=[
                    ColumnInfo("order_id", "int", False, True),
                    ColumnInfo("customer_id", "int", False),
                    ColumnInfo("amount", "decimal", False),
                ],
                foreign_keys=[
                    ForeignKeyInfo("customer_id", "customers", "customer_id", "orders_fk")
                ],
            ),
            TableInfo(
                name="products",
                columns=[ColumnInfo("product_name", "varchar", False)],
            ),
        ],
    )


def setup_function() -> None:
    SchemaService.clear_cache()


def test_schema_retrieval_and_cache_hit() -> None:
    adapter = FakeAdapter(demo_schema(), "demo")
    service = SchemaService(adapter, cache_key=adapter.key)

    assert service.load_schema() == demo_schema()
    assert service.load_schema() == demo_schema()
    assert adapter.inspect_calls == 1


def test_invalidation_forces_refresh() -> None:
    adapter = FakeAdapter(demo_schema(), "demo")
    service = SchemaService(adapter, cache_key=adapter.key)

    service.load_schema()
    service.invalidate()
    service.load_schema()

    assert adapter.inspect_calls == 2


def test_different_database_keys_do_not_share_schemas() -> None:
    first = FakeAdapter(demo_schema("first"), "first")
    second = FakeAdapter(demo_schema("second"), "second")

    assert SchemaService(first, cache_key=first.key).load_schema().database == "first"
    assert SchemaService(second, cache_key=second.key).load_schema().database == "second"
    assert first.inspect_calls == 1
    assert second.inspect_calls == 1


def test_relevant_schema_matches_columns_and_includes_fk_related_tables() -> None:
    adapter = FakeAdapter(demo_schema(), "demo")
    service = SchemaService(adapter, cache_key=adapter.key)

    result = service.relevant_schema("What was total sales by region?")

    assert [table.name for table in result.tables] == ["customers", "orders"]


def test_low_confidence_query_falls_back_to_full_schema() -> None:
    adapter = FakeAdapter(demo_schema(), "demo")
    service = SchemaService(adapter, cache_key=adapter.key)

    result = service.relevant_schema("tell me something unrelated")

    assert result == demo_schema()


def test_empty_schema_is_supported() -> None:
    empty = DatabaseSchema(database="empty")
    adapter = FakeAdapter(empty, "empty")
    service = SchemaService(adapter, cache_key=adapter.key)

    assert service.relevant_schema("anything") == empty
