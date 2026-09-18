from typing import Protocol

from database.schema import DatabaseSchema


class DatabaseAdapter(Protocol):
    """Common lifecycle and metadata operations for supported databases."""

    def connect(self) -> None:
        """Open the database connection."""

    def close(self) -> None:
        """Close the database connection and release resources."""

    def ping(self) -> bool:
        """Return whether the database connection is currently healthy."""

    def inspect_schema(self) -> DatabaseSchema:
        """Return database metadata required by QueryPeek."""

    def cursor(self) -> object:
        """Provide a database cursor for later query execution services."""
