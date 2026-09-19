import os
from dataclasses import dataclass


@dataclass(frozen=True)
class QueryLimits:
    """Execution limits applied to every generated query."""

    timeout_seconds: float = 10.0
    max_rows: int = 10_000

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_rows <= 0:
            raise ValueError("max_rows must be positive")

    @classmethod
    def from_environment(cls) -> "QueryLimits":
        """Load limits from environment variables with safe defaults."""

        return cls(
            timeout_seconds=float(os.getenv("QUERY_TIMEOUT_SECONDS", "10")),
            max_rows=int(os.getenv("MAX_ROWS", "10000")),
        )
