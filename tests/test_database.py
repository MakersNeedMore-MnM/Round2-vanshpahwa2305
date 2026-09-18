from database.mysql import MySQLConfig
from database.schema import introspect_mysql_schema


class FakeCursor:
    def __init__(self) -> None:
        self.queries: list[tuple[str, tuple[str, ...]]] = []
        self._result_sets = [
            [{"TABLE_NAME": "customers"}, {"TABLE_NAME": "orders"}],
            [
                {
                    "TABLE_NAME": "orders",
                    "COLUMN_NAME": "order_id",
                    "DATA_TYPE": "int",
                    "IS_NULLABLE": "NO",
                    "COLUMN_KEY": "PRI",
                },
                {
                    "TABLE_NAME": "orders",
                    "COLUMN_NAME": "customer_id",
                    "DATA_TYPE": "int",
                    "IS_NULLABLE": "NO",
                    "COLUMN_KEY": "MUL",
                },
            ],
            [
                {
                    "TABLE_NAME": "orders",
                    "COLUMN_NAME": "customer_id",
                    "CONSTRAINT_NAME": "orders_customer_fk",
                    "REFERENCED_TABLE_NAME": "customers",
                    "REFERENCED_COLUMN_NAME": "customer_id",
                }
            ],
        ]

    def execute(self, query: str, params: tuple[str, ...]) -> None:
        self.queries.append((query, params))

    def fetchall(self) -> list[dict[str, str]]:
        return self._result_sets.pop(0)


def test_mysql_config_defaults_to_mysql_port() -> None:
    config = MySQLConfig(
        host="db.example.com", database="demo", user="readonly", password="secret"
    )
    assert config.port == 3306
    assert config.connect_timeout == 10


def test_mysql_schema_introspection_collects_metadata() -> None:
    cursor = FakeCursor()

    schema = introspect_mysql_schema(cursor, "querypeek_demo")

    assert [table.name for table in schema.tables] == ["customers", "orders"]
    orders = schema.tables[1]
    assert orders.columns[0].is_primary_key is True
    assert orders.columns[1].nullable is False
    assert orders.foreign_keys[0].referenced_table == "customers"
    assert all(params == ("querypeek_demo",) for _, params in cursor.queries)
