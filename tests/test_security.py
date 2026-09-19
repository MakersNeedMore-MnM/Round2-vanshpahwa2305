import pytest

from security.query_limits import QueryLimits
from security.validator import SQLValidationError, validate_sql


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO customers (name) VALUES ('x')",
        "UPDATE customers SET name = 'x'",
        "DELETE FROM customers",
        "DROP TABLE customers",
        "ALTER TABLE customers ADD COLUMN x INT",
        "CREATE TABLE unsafe (id INT)",
        "TRUNCATE TABLE customers",
        "GRANT SELECT ON demo.* TO 'user'@'%'",
        "REVOKE SELECT ON demo.* FROM 'user'@'%'",
    ],
)
def test_destructive_statements_are_rejected(sql: str) -> None:
    with pytest.raises(SQLValidationError):
        validate_sql(sql)


def test_select_is_allowed_and_bounded() -> None:
    validated = validate_sql("SELECT city, SUM(amount) AS sales FROM orders GROUP BY city")

    assert validated.sql.upper().endswith("LIMIT 10000")
    assert validated.max_rows == 10_000


def test_existing_limit_is_preserved_when_safe() -> None:
    validated = validate_sql("SELECT * FROM orders LIMIT 25")

    assert "LIMIT 25" in validated.sql.upper()


def test_existing_limit_is_reduced_to_maximum() -> None:
    validated = validate_sql("SELECT * FROM orders LIMIT 500", QueryLimits(max_rows=100))

    assert validated.sql.upper().endswith("LIMIT 100")


def test_multiple_statements_are_rejected() -> None:
    with pytest.raises(SQLValidationError, match="one SQL statement"):
        validate_sql("SELECT 1; SELECT 2")


@pytest.mark.parametrize("sql", ["", "   ", "SELECT FROM", "not sql"])
def test_empty_or_malformed_sql_is_rejected(sql: str) -> None:
    with pytest.raises(SQLValidationError):
        validate_sql(sql)


def test_non_select_read_only_statement_is_rejected() -> None:
    with pytest.raises(SQLValidationError, match="Only SELECT"):
        validate_sql("SHOW TABLES")


def test_row_locking_select_is_rejected() -> None:
    with pytest.raises(SQLValidationError, match="prohibited"):
        validate_sql("SELECT * FROM customers FOR UPDATE")


def test_mysql_dialect_syntax_is_supported() -> None:
    validated = validate_sql("SELECT `city` FROM `orders` LIMIT 1")

    assert "city" in validated.sql
