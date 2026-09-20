import json
import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMProviderError(RuntimeError):
    """A safe, user-facing error from an LLM provider."""


class LLMRateLimitError(LLMProviderError):
    """The configured provider temporarily rate-limited the request."""


class LLMProvider(Protocol):
    """Provider-neutral interface for text generation."""

    name: str
    model: str

    def generate(self, prompt: str) -> str:
        """Generate text from a prompt without executing any generated content."""


DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"
DEPRECATED_GEMINI_MODELS = {"gemini-2.5-flash", "gemini-2.5-flash-lite"}


def normalize_model_name(provider: str, model: str) -> str:
    """Map deprecated provider model names to the currently supported versions."""

    normalized = (model or "").strip()
    provider_name = (provider or "").strip().lower()
    if provider_name == "gemini":
        if not normalized:
            return DEFAULT_GEMINI_MODEL
        if normalized in DEPRECATED_GEMINI_MODELS:
            return DEFAULT_GEMINI_MODEL
        return normalized
    return normalized


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

        provider = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
        if provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY", "")
            model = normalize_model_name(
                provider,
                os.getenv("LLM_MODEL") or os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL,
            )
        else:
            api_key = os.getenv("LLM_API_KEY", "")
            model = normalize_model_name(provider, os.getenv("LLM_MODEL") or "")
        return cls(
            provider=provider,
            api_key=api_key,
            model=model,
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
            if error.code == 429:
                raise LLMRateLimitError(
                    "The configured LLM model is temporarily rate-limited."
                ) from error
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


class GeminiProvider:
    """Google Gemini provider using the official ``google-genai`` SDK."""

    name = "gemini"

    def __init__(self, config: LLMConfig, client: Any | None = None) -> None:
        if not config.api_key:
            raise LLMProviderError("GEMINI_API_KEY is required for the configured provider.")
        if not config.model:
            raise LLMProviderError("LLM_MODEL is required for the configured provider.")
        self._api_key = config.api_key
        self.model = config.model
        self._client = client or self._create_client()

    def _create_client(self) -> Any:
        try:
            from google import genai
        except ImportError as error:
            raise LLMProviderError(
                "The google-genai package is required for the Gemini provider."
            ) from error
        return genai.Client(api_key=self._api_key)

    def generate(self, prompt: str) -> str:
        """Generate text and return only Gemini's response text."""

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            content = response.text
        except Exception as error:
            if _provider_status_code(error) == 429:
                raise LLMRateLimitError(
                    "The configured Gemini model is temporarily rate-limited."
                ) from error
            raise LLMProviderError("The Gemini provider request failed.") from error

        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("The Gemini provider returned empty content.")
        return content.strip()


def _provider_status_code(error: Exception) -> int | None:
    """Read a numeric provider status without exposing the raw exception."""

    for attribute in ("status_code", "code"):
        value = getattr(error, attribute, None)
        if isinstance(value, int):
            return value
    return None


def create_llm_provider(config: LLMConfig | None = None) -> LLMProvider:
    """Create the configured provider while keeping provider selection replaceable."""

    resolved = config or LLMConfig.from_environment()
    provider_name = resolved.provider.lower()
    if provider_name == "gemini":
        return GeminiProvider(resolved)
    if provider_name == "openrouter":
        return OpenRouterProvider(resolved)
    if not provider_name:
        raise LLMProviderError("LLM_PROVIDER must be configured.")
    raise LLMProviderError(f"Unsupported LLM provider: {resolved.provider}.")
