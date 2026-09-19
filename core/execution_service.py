from typing import Any

import pandas as pd

from database.base import DatabaseAdapter
from database.mysql import MySQLConnectionError
from security.query_limits import QueryLimits
from security.validator import ValidatedSQL


class DatabaseExecutionError(RuntimeError):
    """A safe, user-facing database execution error."""


class ExecutionService:
    """Execute only SQL that has already passed the application validator."""

    def __init__(self, adapter: DatabaseAdapter, limits: QueryLimits | None = None) -> None:
        self.adapter = adapter
        self.limits = limits or QueryLimits()

    def health_check(self) -> bool:
        """Open the configured connection and report whether it is healthy."""

        try:
            self.adapter.connect()
            return self.adapter.ping()
        except MySQLConnectionError:
            raise
        except Exception:
            return False

    def execute(self, query: ValidatedSQL) -> pd.DataFrame:
        """Execute one validated query and return rows as a pandas DataFrame."""

        if not isinstance(query, ValidatedSQL):
            raise TypeError("ExecutionService requires SQL validated by validate_sql().")

        cursor: Any | None = None
        try:
            cursor = self.adapter.cursor()
            cursor.execute(self._with_timeout_hint(query.sql))
            rows = cursor.fetchall()
            if len(rows) > self.limits.max_rows:
                rows = rows[: self.limits.max_rows]
            return pd.DataFrame(rows)
        except MySQLConnectionError as error:
            raise DatabaseExecutionError(str(error)) from error
        except Exception as error:
            raise DatabaseExecutionError("The demo database query failed.") from error
        finally:
            if cursor is not None:
                cursor.close()

    def _with_timeout_hint(self, sql: str) -> str:
        timeout_ms = max(1, int(self.limits.timeout_seconds * 1000))
        return f"/*+ MAX_EXECUTION_TIME({timeout_ms}) */ {sql}"
