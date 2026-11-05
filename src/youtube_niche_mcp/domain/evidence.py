from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from youtube_niche_mcp.domain.provenance import Provenance
from youtube_niche_mcp.domain.states import EvidenceState


class NumericEvidence(BaseModel):
    """Generic scalar contract, not an implemented research metric or score."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    state: EvidenceState
    value: StrictInt | Annotated[float, Field(strict=True, allow_inf_nan=False)] | None = None
    reason: str = Field(min_length=1)
    provenance: Provenance

    @model_validator(mode="after")
    def preserve_unknown(self) -> Self:
        numeric_states = {
            EvidenceState.AVAILABLE,
            EvidenceState.APPROXIMATE,
            EvidenceState.PARTIAL_COVERAGE,
        }
        if self.state not in numeric_states and self.value is not None:
            raise ValueError("Unknown or unresolved evidence must have value=null")
        if (
            self.state in {EvidenceState.AVAILABLE, EvidenceState.APPROXIMATE}
            and self.value is None
        ):
            raise ValueError("Available scalar evidence requires an observed value")
        return self
