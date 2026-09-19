import re
from collections import deque
from dataclasses import replace
from typing import ClassVar

from database.base import DatabaseAdapter
from database.schema import DatabaseSchema, TableInfo

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_COMMON_IDENTIFIERS = {
    "buyer": "customer",
    "buyers": "customer",
    "client": "customer",
    "clients": "customer",
    "revenue": "amount",
    "sales": "amount",
    "spend": "amount",
    "spending": "amount",
    "product": "product",
    "products": "product",
}


class SchemaService:
    """Load, cache, and deterministically narrow database schema metadata."""

    _cache: ClassVar[dict[str, DatabaseSchema]] = {}

    def __init__(self, adapter: DatabaseAdapter, cache_key: str | None = None) -> None:
        self.adapter = adapter
        self._cache_key = cache_key or self._build_cache_key(adapter)

    def load_schema(self, force_refresh: bool = False) -> DatabaseSchema:
        """Return the complete schema, introspecting the adapter only when needed."""

        if force_refresh or self._cache_key not in self._cache:
            self._cache[self._cache_key] = self.adapter.inspect_schema()
        return self._cache[self._cache_key]

    def refresh(self) -> DatabaseSchema:
        """Explicitly re-introspect and cache the schema."""

        return self.load_schema(force_refresh=True)

    def invalidate(self) -> None:
        """Remove this adapter's schema from the in-memory cache."""

        self._cache.pop(self._cache_key, None)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all in-memory schema entries, primarily for tests or reset flows."""

        cls._cache.clear()

    def relevant_schema(self, question: str) -> DatabaseSchema:
        """Return matched tables plus FK-related tables for a natural-language question.

        Matching is intentionally lexical and deterministic. If no table or column
        receives a useful match, the complete cached schema is returned so the SQL
        generator never receives an empty context solely because of weak wording.
        """

        schema = self.load_schema()
        if not schema.tables:
            return DatabaseSchema(database=schema.database)

        question_tokens = self._question_tokens(question)
        scores = {table.name: self._table_score(table, question_tokens) for table in schema.tables}
        matched = {name for name, score in scores.items() if score > 0}
        if not matched:
            return schema

        return self._with_related_tables(schema, matched)

    @staticmethod
    def _build_cache_key(adapter: DatabaseAdapter) -> str:
        """Build a non-secret cache key from a configured adapter identity."""

        config = getattr(adapter, "config", None)
        if config is not None:
            values = (
                getattr(config, "host", ""),
                getattr(config, "port", 3306),
                getattr(config, "database", ""),
                getattr(config, "user", ""),
            )
            return "mysql:" + "|".join(str(value) for value in values)
        return f"{type(adapter).__module__}.{type(adapter).__qualname__}:{id(adapter)}"

    @staticmethod
    def _question_tokens(question: str) -> set[str]:
        tokens = set(_TOKEN_PATTERN.findall(question.lower()))
        aliases = {_COMMON_IDENTIFIERS[token] for token in tokens if token in _COMMON_IDENTIFIERS}
        tokens.update(aliases)
        return tokens

    @staticmethod
    def _table_score(table: TableInfo, question_tokens: set[str]) -> int:
        identifiers = {table.name.lower()}
        identifiers.update(column.name.lower() for column in table.columns)
        score = 0
        for token in question_tokens:
            if token in identifiers:
                score += 2
            elif any(
                len(token) >= 4
                and (identifier.startswith(token) or token.startswith(identifier.rstrip("s")))
                for identifier in identifiers
            ):
                score += 1
        return score

    @classmethod
    def _with_related_tables(
        cls, schema: DatabaseSchema, matched: set[str]
    ) -> DatabaseSchema:
        by_name = {table.name: table for table in schema.tables}
        relationships: dict[str, set[str]] = {name: set() for name in by_name}
        for table in schema.tables:
            for foreign_key in table.foreign_keys:
                if foreign_key.referenced_table in by_name:
                    relationships[table.name].add(foreign_key.referenced_table)
                    relationships[foreign_key.referenced_table].add(table.name)

        included = set(matched)
        queue = deque(matched)
        while queue:
            table_name = queue.popleft()
            for related_name in relationships[table_name]:
                if related_name not in included:
                    included.add(related_name)
                    queue.append(related_name)

        return DatabaseSchema(
            database=schema.database,
            tables=[replace(table) for table in schema.tables if table.name in included],
        )
