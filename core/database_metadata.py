"""Cached, read-only database metadata used by the dashboard UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

import pandas as pd

from database.base import DatabaseAdapter
from database.schema import DatabaseSchema
from security.query_limits import QueryLimits
from security.validator import ValidatedSQL, validate_sql


class DatabaseMetadataError(RuntimeError):
    """A safe error while loading dashboard metadata."""


@dataclass(frozen=True)
class TableMetrics:
    """Safe statistics for one accessible table."""

    name: str
    row_count: int
    size_bytes: int | None

    @property
    def size_label(self) -> str:
        return format_bytes(self.size_bytes)


@dataclass(frozen=True)
class DatabaseOverview:
    """Dashboard metadata for one database."""

    database: str
    tables: tuple[TableMetrics, ...]

    @property
    def total_rows(self) -> int:
        return sum(table.row_count for table in self.tables)

    @property
    def total_size_bytes(self) -> int | None:
        sizes = [table.size_bytes for table in self.tables]
        if not sizes or any(size is None for size in sizes):
            return None
        return sum(size for size in sizes if size is not None)

    @property
    def total_size_label(self) -> str:
        return format_bytes(self.total_size_bytes)

    @property
    def largest_table(self) -> TableMetrics | None:
        return max(self.tables, key=lambda table: table.row_count, default=None)

    def as_frame(self) -> pd.DataFrame:
        """Return display data without exposing internal mutable state."""

        return pd.DataFrame(
            [
                {
                    "TABLE": table.name,
                    "ROWS": table.row_count,
                    "SIZE": table.size_label,
                    "ACTION": "Explore →",
                }
                for table in self.tables
            ]
        )

    def rows_frame(self) -> pd.DataFrame:
        """Return numeric table-row data suitable for Plotly."""

        return pd.DataFrame(
            [{"table": table.name, "rows": table.row_count} for table in self.tables]
        )

    def sizes_frame(self) -> pd.DataFrame:
        """Return size data for tables where MySQL exposes size metadata."""

        return pd.DataFrame(
            [
                {"table": table.name, "size_mb": table.size_bytes / 1_000_000}
                for table in self.tables
                if table.size_bytes is not None
            ]
        )


def format_bytes(size_bytes: int | None) -> str:
    """Format a byte count, or return N/A when the server has no size value."""

    if size_bytes is None:
        return "N/A"
    if size_bytes < 1_000_000:
        return f"{size_bytes / 1_000:.1f} KB"
    if size_bytes < 1_000_000_000:
        return f"{size_bytes / 1_000_000:.1f} MB"
    return f"{size_bytes / 1_000_000_000:.1f} GB"


def quote_table_identifier(table_name: str) -> str:
    """Quote a metadata-derived MySQL table identifier safely."""

    if not isinstance(table_name, str) or not table_name:
        raise ValueError("Table name must be a non-empty string.")
    return f"`{table_name.replace('`', '``')}`"


def build_preview_query(table_name: str, limits: QueryLimits | None = None) -> ValidatedSQL:
    """Build a bounded SELECT preview through the normal SQL validator."""

    return validate_sql(
        f"SELECT * FROM {quote_table_identifier(table_name)}",
        limits,
    )


class DatabaseMetadataService:
    """Load real table counts and sizes once per configured database."""

    _cache: ClassVar[dict[str, DatabaseOverview]] = {}

    def __init__(self, adapter: DatabaseAdapter, cache_key: str | None = None) -> None:
        self.adapter = adapter
        self._cache_key = cache_key or self._build_cache_key(adapter)

    def load(self, schema: DatabaseSchema, force_refresh: bool = False) -> DatabaseOverview:
        """Return cached overview metadata, refreshing only when requested."""

        if force_refresh or self._cache_key not in self._cache:
            self._cache[self._cache_key] = self._introspect(schema)
        return self._cache[self._cache_key]

    def invalidate(self) -> None:
        """Remove this database's overview from the in-memory cache."""

        self._cache.pop(self._cache_key, None)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all overview entries, primarily for tests."""

        cls._cache.clear()

    def _introspect(self, schema: DatabaseSchema) -> DatabaseOverview:
        try:
            size_rows = self._fetch_all(
                """
                SELECT TABLE_NAME,
                       DATA_LENGTH + INDEX_LENGTH AS SIZE_BYTES
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
                """,
                (schema.database,),
            )
            sizes = {
                str(row["TABLE_NAME"]): self._optional_int(row.get("SIZE_BYTES"))
                for row in size_rows
            }
            metrics = tuple(
                TableMetrics(
                    name=table.name,
                    row_count=self._count_rows(table.name),
                    size_bytes=sizes.get(table.name),
                )
                for table in schema.tables
            )
        except Exception as error:
            raise DatabaseMetadataError("Could not load database metadata.") from error
        return DatabaseOverview(database=schema.database, tables=metrics)

    def _count_rows(self, table_name: str) -> int:
        rows = self._fetch_all(
            f"SELECT COUNT(*) AS ROW_COUNT FROM {quote_table_identifier(table_name)}"
        )
        if not rows:
            return 0
        return int(rows[0]["ROW_COUNT"])

    def _fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        cursor: Any | None = None
        try:
            cursor = self.adapter.cursor()
            cursor.execute(query, params)
            return list(cursor.fetchall())
        finally:
            if cursor is not None:
                cursor.close()

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        return None if value is None else int(value)

    @staticmethod
    def _build_cache_key(adapter: DatabaseAdapter) -> str:
        config = getattr(adapter, "config", None)
        if config is not None:
            values = (
                getattr(config, "host", ""),
                getattr(config, "port", 3306),
                getattr(config, "database", ""),
                getattr(config, "user", ""),
            )
            return "metadata:mysql:" + "|".join(str(value) for value in values)
        return f"metadata:{type(adapter).__module__}.{type(adapter).__qualname__}:{id(adapter)}"


__all__ = [
    "DatabaseMetadataError",
    "DatabaseMetadataService",
    "DatabaseOverview",
    "TableMetrics",
    "build_preview_query",
    "format_bytes",
    "quote_table_identifier",
]
