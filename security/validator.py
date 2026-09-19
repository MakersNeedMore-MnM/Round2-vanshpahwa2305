from dataclasses import dataclass
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from security.query_limits import QueryLimits


class SQLValidationError(ValueError):
    """Raised when generated SQL is not a safe, valid MVP query."""


@dataclass(frozen=True)
class ValidatedSQL:
    """SQL that passed AST validation and has a bounded result limit."""

    sql: str
    expression: exp.Expression
    max_rows: int


_BLOCKED_NODE_NAMES = {
    "alter",
    "attach",
    "command",
    "commit",
    "create",
    "delete",
    "drop",
    "grant",
    "insert",
    "lock",
    "merge",
    "revoke",
    "rollback",
    "set",
    "truncate",
    "update",
    "use",
}


def validate_sql(sql: str, limits: QueryLimits | None = None) -> ValidatedSQL:
    """Parse and validate one MySQL SELECT, applying a maximum row limit."""

    if not isinstance(sql, str) or not sql.strip():
        raise SQLValidationError("SQL must be a non-empty string.")

    active_limits = limits or QueryLimits()
    try:
        statements = sqlglot.parse(sql, read="mysql")
    except ParseError as error:
        raise SQLValidationError("SQL could not be parsed as MySQL.") from error

    if len(statements) != 1:
        raise SQLValidationError("Only one SQL statement is allowed.")

    expression = statements[0]
    if not isinstance(expression, exp.Select):
        raise SQLValidationError("Only SELECT statements are allowed.")

    for node in expression.walk():
        if type(node).__name__.lower() in _BLOCKED_NODE_NAMES:
            raise SQLValidationError("The SQL contains a prohibited operation.")

    expression = _apply_row_limit(expression, active_limits.max_rows)
    return ValidatedSQL(
        sql=expression.sql(dialect="mysql"),
        expression=expression,
        max_rows=active_limits.max_rows,
    )


def _apply_row_limit(expression: exp.Select, max_rows: int) -> exp.Select:
    limit = expression.args.get("limit")
    if limit is None:
        return expression.limit(max_rows)

    limit_expression: Any = limit.args.get("expression")
    if isinstance(limit_expression, exp.Literal) and limit_expression.is_number:
        try:
            requested_rows = int(limit_expression.this)
        except (TypeError, ValueError):
            return expression
        if requested_rows > max_rows:
            return expression.limit(max_rows)
    return expression
