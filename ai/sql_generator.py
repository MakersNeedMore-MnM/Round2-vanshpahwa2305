from dataclasses import dataclass

from ai.prompt_builder import build_sql_prompt
from ai.provider import LLMProvider, LLMProviderError
from database.schema import DatabaseSchema


class SQLGenerationError(RuntimeError):
    """A safe error raised when SQL generation cannot produce usable output."""


@dataclass(frozen=True)
class GeneratedSQL:
    """Provider-neutral SQL generation result."""

    sql: str
    provider: str
    model: str


class SQLGenerator:
    """Generate SQL from a question and retrieved schema without executing it."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def generate(self, question: str, schema: DatabaseSchema) -> GeneratedSQL:
        """Generate SQL from relevant schema context through the configured provider."""

        if not question.strip():
            raise SQLGenerationError("A natural-language question is required.")

        prompt = build_sql_prompt(question, schema)
        try:
            raw_sql = self.provider.generate(prompt)
        except LLMProviderError as error:
            raise SQLGenerationError(str(error)) from error
        except Exception as error:
            raise SQLGenerationError("The configured LLM provider failed.") from error

        sql = _clean_sql_output(raw_sql)
        if not sql:
            raise SQLGenerationError("The LLM provider returned empty SQL.")
        return GeneratedSQL(
            sql=sql,
            provider=self.provider.name,
            model=self.provider.model,
        )


def _clean_sql_output(output: str) -> str:
    """Remove a practical Markdown fence without attempting SQL validation."""

    if not isinstance(output, str):
        return ""
    cleaned = output.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]).strip()
        if cleaned.lower().startswith("sql\n"):
            cleaned = cleaned[4:].strip()
    return cleaned
