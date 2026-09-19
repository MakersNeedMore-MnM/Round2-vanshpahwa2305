import pytest

from ai.prompt_builder import build_sql_prompt
from ai.provider import LLMProviderError
from ai.sql_generator import SQLGenerationError, SQLGenerator
from database.schema import ColumnInfo, DatabaseSchema, ForeignKeyInfo, TableInfo


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self, response: str = "SELECT COUNT(*) FROM customers") -> None:
        self.response = response
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


class ErrorProvider(FakeProvider):
    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        raise LLMProviderError("provider unavailable")


class NoDatabaseAdapter:
    def inspect_schema(self) -> None:
        raise AssertionError("SQL generation must not inspect or execute a database")


def demo_schema() -> DatabaseSchema:
    return DatabaseSchema(
        database="demo",
        tables=[
            TableInfo(
                name="orders",
                columns=[ColumnInfo("customer_id", "int", False, True)],
                foreign_keys=[
                    ForeignKeyInfo("customer_id", "customers", "customer_id", "orders_fk")
                ],
            ),
            TableInfo(
                name="customers",
                columns=[ColumnInfo("region", "varchar", True)],
            ),
        ],
    )


def test_prompt_contains_question_mysql_and_relevant_schema() -> None:
    prompt = build_sql_prompt("Which region has the most orders?", demo_schema())

    assert "Which region has the most orders?" in prompt
    assert "SQL dialect: MySQL" in prompt
    assert "TABLE orders" in prompt
    assert "customer_id" in prompt
    assert "TABLE products" not in prompt
    assert "Return SQL only" in prompt


def test_generator_returns_structured_sql_without_database_execution() -> None:
    provider = FakeProvider("SELECT COUNT(*) FROM orders")
    result = SQLGenerator(provider).generate("How many orders?", demo_schema())

    assert result.sql == "SELECT COUNT(*) FROM orders"
    assert result.provider == "fake"
    assert result.model == "fake-model"
    assert len(provider.prompts) == 1


def test_generator_strips_practical_markdown_fence() -> None:
    provider = FakeProvider("```sql\nSELECT 1\n```")

    result = SQLGenerator(provider).generate("Give me a query", demo_schema())

    assert result.sql == "SELECT 1"


def test_provider_error_is_wrapped_cleanly() -> None:
    with pytest.raises(SQLGenerationError, match="provider unavailable"):
        SQLGenerator(ErrorProvider()).generate("How many orders?", demo_schema())


@pytest.mark.parametrize("response", ["", "   ", "```sql\n```"])
def test_empty_model_output_is_rejected(response: str) -> None:
    with pytest.raises(SQLGenerationError, match="empty SQL"):
        SQLGenerator(FakeProvider(response)).generate("How many orders?", demo_schema())
