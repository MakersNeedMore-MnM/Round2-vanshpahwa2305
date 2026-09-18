from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ColumnInfo:
    """Metadata for one database column."""

    name: str
    data_type: str
    nullable: bool
    is_primary_key: bool = False


@dataclass(frozen=True)
class ForeignKeyInfo:
    """A relationship from one table column to another table column."""

    column_name: str
    referenced_table: str
    referenced_column: str
    constraint_name: str


@dataclass
class TableInfo:
    """Metadata for one table."""

    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    foreign_keys: list[ForeignKeyInfo] = field(default_factory=list)


@dataclass
class DatabaseSchema:
    """Database metadata in a provider-neutral representation."""

    database: str
    tables: list[TableInfo] = field(default_factory=list)


def _value(row: Any, key: str, index: int) -> Any:
    """Read a value from either a dictionary or a tuple-like database row."""

    if isinstance(row, dict):
        return row[key]
    return row[index]


def introspect_mysql_schema(cursor: Any, database: str) -> DatabaseSchema:
    """Build schema metadata from MySQL's information_schema views.

    The database name is passed as a bound parameter in every query. No
    identifiers or user-controlled values are interpolated into SQL.
    """

    cursor.execute(
        """
        SELECT TABLE_NAME
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
        """,
        (database,),
    )
    table_names = [str(_value(row, "TABLE_NAME", 0)) for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
        ORDER BY TABLE_NAME, ORDINAL_POSITION
        """,
        (database,),
    )
    columns_by_table: dict[str, list[ColumnInfo]] = {name: [] for name in table_names}
    for row in cursor.fetchall():
        table_name = str(_value(row, "TABLE_NAME", 0))
        if table_name in columns_by_table:
            columns_by_table[table_name].append(
                ColumnInfo(
                    name=str(_value(row, "COLUMN_NAME", 1)),
                    data_type=str(_value(row, "DATA_TYPE", 2)),
                    nullable=str(_value(row, "IS_NULLABLE", 3)).upper() == "YES",
                    is_primary_key=str(_value(row, "COLUMN_KEY", 4)).upper() == "PRI",
                )
            )

    cursor.execute(
        """
        SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME,
               REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = %s
          AND REFERENCED_TABLE_NAME IS NOT NULL
        ORDER BY TABLE_NAME, CONSTRAINT_NAME, ORDINAL_POSITION
        """,
        (database,),
    )
    foreign_keys_by_table: dict[str, list[ForeignKeyInfo]] = {
        name: [] for name in table_names
    }
    for row in cursor.fetchall():
        table_name = str(_value(row, "TABLE_NAME", 0))
        if table_name in foreign_keys_by_table:
            foreign_keys_by_table[table_name].append(
                ForeignKeyInfo(
                    column_name=str(_value(row, "COLUMN_NAME", 1)),
                    constraint_name=str(_value(row, "CONSTRAINT_NAME", 2)),
                    referenced_table=str(_value(row, "REFERENCED_TABLE_NAME", 3)),
                    referenced_column=str(_value(row, "REFERENCED_COLUMN_NAME", 4)),
                )
            )

    return DatabaseSchema(
        database=database,
        tables=[
            TableInfo(
                name=name,
                columns=columns_by_table[name],
                foreign_keys=foreign_keys_by_table[name],
            )
            for name in table_names
        ],
    )
