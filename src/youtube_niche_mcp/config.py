"""Explicit process-environment configuration with secret-safe diagnostics."""

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError


class ConfigurationError(ValueError):
    """Invalid configuration; messages never include input values."""


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    db_path: Path = Field(default_factory=lambda: Path("data/research.sqlite3"))
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    db_timeout_seconds: float = Field(default=10, gt=0, le=120, allow_inf_nan=False)
    youtube_api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)
    nexlev_api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)
    nexlev_timeout_seconds: float = Field(default=20, gt=0, le=120, allow_inf_nan=False)
    nexlev_similarity_timeout_seconds: float = Field(default=300, gt=0, le=900, allow_inf_nan=False)
    api_timeout_seconds: float = Field(default=20, gt=0, le=120, allow_inf_nan=False)
    api_max_retries: int = Field(default=2, ge=0, le=5)
    api_retry_delay_seconds: float = Field(default=0.5, ge=0, le=10, allow_inf_nan=False)
    cache_ttl_seconds: int = Field(default=3600, ge=1, le=2592000)
    cache_stale_seconds: int = Field(default=300, ge=0, le=86400)
    batch_stats_enabled: bool = False
    api_batch_size: int = Field(default=50, ge=1, le=50)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Self:
        values = os.environ if env is None else env
        options = {}
        for variable, field in (
            ("YTNMCP_DB_PATH", "db_path"),
            ("YTNMCP_LOG_LEVEL", "log_level"),
            ("YTNMCP_DB_TIMEOUT_SECONDS", "db_timeout_seconds"),
            ("YOUTUBE_API_KEY", "youtube_api_key"),
            ("NEXLEV_API_KEY", "nexlev_api_key"),
            ("YTNMCP_NEXLEV_TIMEOUT_SECONDS", "nexlev_timeout_seconds"),
            ("YTNMCP_NEXLEV_SIMILARITY_TIMEOUT_SECONDS", "nexlev_similarity_timeout_seconds"),
            ("YTNMCP_API_TIMEOUT_SECONDS", "api_timeout_seconds"),
            ("YTNMCP_API_MAX_RETRIES", "api_max_retries"),
            ("YTNMCP_API_RETRY_DELAY_SECONDS", "api_retry_delay_seconds"),
            ("YTNMCP_CACHE_TTL_SECONDS", "cache_ttl_seconds"),
            ("YTNMCP_CACHE_STALE_SECONDS", "cache_stale_seconds"),
            ("YTNMCP_BATCH_STATS_ENABLED", "batch_stats_enabled"),
            ("YTNMCP_API_BATCH_SIZE", "api_batch_size"),
        ):
            if values.get(variable, "").strip():
                options[field] = values[variable].strip()
            elif variable in values and variable not in {"YOUTUBE_API_KEY", "NEXLEV_API_KEY"}:
                raise ConfigurationError(f"{variable} must not be blank")
        try:
            return cls.model_validate(options)
        except ValidationError as exc:
            fields = ", ".join(sorted({str(e["loc"][0]) for e in exc.errors()}))
            raise ConfigurationError(f"Invalid configuration fields: {fields}") from None

    def safe_summary(self) -> dict:
        return {
            "db_path": str(self.db_path.resolve()),
            "log_level": self.log_level,
            "db_timeout_seconds": self.db_timeout_seconds,
            "youtube_api_key_present": self.youtube_api_key is not None,
            "nexlev_api_key_present": self.nexlev_api_key is not None,
            "live_api_required": False,
            "api_timeout_seconds": self.api_timeout_seconds,
            "api_max_retries": self.api_max_retries,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "cache_stale_seconds": self.cache_stale_seconds,
            "batch_stats_enabled": self.batch_stats_enabled,
            "api_batch_size": self.api_batch_size,
        }
