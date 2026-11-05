from datetime import UTC
from typing import Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from youtube_niche_mcp.domain.states import Precision, SourceKind


class Provenance(BaseModel):
    """An observation's clocks; publication is never substituted for observation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str = Field(min_length=1)
    source_kind: SourceKind
    source_version: str = Field(min_length=1)
    precision: Precision
    published_at: AwareDatetime | None = None
    observed_at: AwareDatetime
    available_at: AwareDatetime
    maturity_at: AwareDatetime | None = None

    @field_validator("published_at", "observed_at", "available_at", "maturity_at")
    @classmethod
    def normalize_utc(cls, value):
        return value.astimezone(UTC) if value else None

    @model_validator(mode="after")
    def validate_clocks(self) -> Self:
        if self.available_at < self.observed_at:
            raise ValueError("available_at cannot precede observed_at")
        if (
            self.maturity_at is not None
            and self.published_at is not None
            and self.maturity_at < self.published_at
        ):
            raise ValueError("maturity_at cannot precede published_at")
        return self
