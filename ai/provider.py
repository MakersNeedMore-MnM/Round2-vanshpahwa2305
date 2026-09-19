import json
import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMProviderError(RuntimeError):
    """A safe, user-facing error from an LLM provider."""


class LLMProvider(Protocol):
    """Provider-neutral interface for text generation."""

    name: str
    model: str

    def generate(self, prompt: str) -> str:
        """Generate text from a prompt without executing any generated content."""


@dataclass(frozen=True)
class LLMConfig:
    """Configuration shared by provider factories and provider implementations."""

    provider: str
    api_key: str = ""
    model: str = ""
    endpoint: str = "https://openrouter.ai/api/v1/chat/completions"
    timeout_seconds: float = 30.0

    @classmethod
    def from_environment(cls) -> "LLMConfig":
        """Load provider settings without logging or otherwise exposing secrets."""

        return cls(
            provider=os.getenv("LLM_PROVIDER", "").strip(),
            api_key=os.getenv("LLM_API_KEY", ""),
            model=os.getenv("LLM_MODEL", "").strip(),
        )


class OpenRouterProvider:
    """OpenRouter chat-completions provider using Python's standard HTTP client."""

    name = "openrouter"

    def __init__(self, config: LLMConfig) -> None:
        if not config.api_key:
            raise LLMProviderError("LLM_API_KEY is required for the configured provider.")
        if not config.model:
            raise LLMProviderError("LLM_MODEL is required for the configured provider.")
        self._api_key = config.api_key
        self.model = config.model
        self._endpoint = config.endpoint
        self._timeout_seconds = config.timeout_seconds

    def generate(self, prompt: str) -> str:
        """Request one completion and return only its text content."""

        payload = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            }
        ).encode("utf-8")
        request = Request(
            self._endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                body: Any = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise LLMProviderError(f"LLM provider returned HTTP {error.code}.") from error
        except URLError as error:
            raise LLMProviderError("Could not reach the configured LLM provider.") from error
        except (TimeoutError, OSError) as error:
            raise LLMProviderError("The LLM provider request failed.") from error
        except json.JSONDecodeError as error:
            raise LLMProviderError("The LLM provider returned invalid JSON.") from error

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise LLMProviderError("The LLM provider returned an unexpected response.") from error
        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("The LLM provider returned empty content.")
        return content.strip()


def create_llm_provider(config: LLMConfig | None = None) -> LLMProvider:
    """Create the configured provider while keeping provider selection replaceable."""

    resolved = config or LLMConfig.from_environment()
    provider_name = resolved.provider.lower()
    if provider_name == "openrouter":
        return OpenRouterProvider(resolved)
    if not provider_name:
        raise LLMProviderError("LLM_PROVIDER must be configured.")
    raise LLMProviderError(f"Unsupported LLM provider: {resolved.provider}.")
