from types import SimpleNamespace

import pytest

from ai.provider import (
    GeminiProvider,
    LLMConfig,
    LLMProviderError,
    LLMRateLimitError,
)


class FakeModels:
    def __init__(self, text: str = "SELECT 1", error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.calls: list[dict[str, str]] = []

    def generate_content(self, **kwargs: str) -> SimpleNamespace:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(text=self.text)


class FakeProviderError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class FakeClient:
    def __init__(self, models: FakeModels) -> None:
        self.models = models


def gemini_config() -> LLMConfig:
    return LLMConfig(
        provider="gemini",
        api_key="test-key",
        model="gemini-3.6-flash",
    )


def test_gemini_environment_configuration_uses_gemini_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "configured-test-key")
    monkeypatch.setenv("LLM_MODEL", "gemini-3.6-flash")

    config = LLMConfig.from_environment()

    assert config.provider == "gemini"
    assert config.api_key == "configured-test-key"
    assert config.model == "gemini-3.6-flash"


def test_gemini_provider_sends_prompt_and_returns_text() -> None:
    models = FakeModels("SELECT COUNT(*) FROM customers")
    provider = GeminiProvider(gemini_config(), FakeClient(models))

    result = provider.generate("schema-grounded prompt")

    assert result == "SELECT COUNT(*) FROM customers"
    assert models.calls == [
        {"model": "gemini-3.6-flash", "contents": "schema-grounded prompt"}
    ]


def test_gemini_provider_handles_rate_limits_without_raw_error_details() -> None:
    provider = GeminiProvider(
        gemini_config(),
        FakeClient(FakeModels(error=FakeProviderError("rate limited", 429))),
    )

    with pytest.raises(LLMRateLimitError, match="temporarily rate-limited"):
        provider.generate("prompt")


def test_gemini_provider_handles_provider_errors_safely() -> None:
    provider = GeminiProvider(
        gemini_config(),
        FakeClient(FakeModels(error=FakeProviderError("secret response body"))),
    )

    with pytest.raises(LLMProviderError, match="Gemini provider request failed") as error:
        provider.generate("prompt")

    assert "secret response body" not in str(error.value)


def test_gemini_provider_rejects_empty_response() -> None:
    provider = GeminiProvider(gemini_config(), FakeClient(FakeModels("  ")))

    with pytest.raises(LLMProviderError, match="empty content"):
        provider.generate("prompt")
