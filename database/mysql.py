import ssl
from dataclasses import dataclass
from types import TracebackType
from typing import Any

from database.schema import DatabaseSchema, introspect_mysql_schema


class MySQLConnectionError(RuntimeError):
    """Safe connection failure with no credentials or server details."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


def _connection_error_category(error: Exception) -> str:
    errno = getattr(error, "errno", None)
    if errno in {1044, 1045, 1698}:
        return "MySQL authentication failure."
    if errno == 1049:
        return "MySQL database not found."
    if errno in {2003, 2005, 2006, 2013}:
        return "MySQL connection failure."
    return "MySQL connection failure."


@dataclass(frozen=True)
class MySQLConfig:
    """Connection settings for a MySQL database.

    Passwords are intentionally kept in this object only for the connector;
    callers must not log or serialize this configuration.
    """

    host: str
    database: str
    user: str
    password: str
    port: int = 3306
    connect_timeout: int = 10
    ssl_disabled: bool = False
    ssl_verify_cert: bool = False
    ssl_verify_identity: bool = False
    ssl_ca: str | None = None


class MySQLAdapter:
    """Small MySQL adapter used by schema and execution services."""

    def __init__(self, config: MySQLConfig) -> None:
        self.config = config
        self._connection: Any | None = None

    def connect(self) -> None:
        """Open a MySQL connection if one is not already open."""

        if self._connection is not None and self.ping():
            return
        if self._connection is not None:
            self.close()

        try:
            import mysql.connector
        except ImportError as error:
            raise RuntimeError(
                "mysql-connector-python is required to connect to MySQL."
            ) from error

        connection_kwargs: dict[str, Any] = {
            "host": self.config.host,
            "port": self.config.port,
            "database": self.config.database,
            "user": self.config.user,
            "password": self.config.password,
            "connection_timeout": self.config.connect_timeout,
        }

        if not self.config.ssl_disabled:
            connection_kwargs["ssl_disabled"] = False
            connection_kwargs["ssl_verify_cert"] = self.config.ssl_verify_cert
            connection_kwargs["ssl_verify_identity"] = self.config.ssl_verify_identity
            ssl_ca = self.config.ssl_ca
            if ssl_ca is None:
                try:
                    import certifi

                    ssl_ca = certifi.where()
                except Exception:
                    default_paths = ssl.get_default_verify_paths()
                    ssl_ca = default_paths.openssl_cafile or default_paths.cafile
            if ssl_ca:
                connection_kwargs["ssl_ca"] = ssl_ca

        try:
            self._connection = mysql.connector.connect(**connection_kwargs)
        except mysql.connector.Error as error:
            raise MySQLConnectionError(_connection_error_category(error)) from error

    def close(self) -> None:
        """Close the connection, if open."""

        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def ping(self) -> bool:
        """Check connection health without attempting reconnection."""

        if self._connection is None:
            return False
        try:
            return bool(self._connection.is_connected())
        except Exception:
            return False

    def inspect_schema(self) -> DatabaseSchema:
        """Inspect tables, columns, primary keys, and foreign keys."""

        self.connect()
        cursor = self._connection.cursor(dictionary=True)
        try:
            return introspect_mysql_schema(cursor, self.config.database)
        finally:
            cursor.close()

    def cursor(self) -> Any:
        """Return a cursor from an active connection for query execution."""

        self.connect()
        return self._connection.cursor(dictionary=True)

    def __enter__(self) -> "MySQLAdapter":
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
