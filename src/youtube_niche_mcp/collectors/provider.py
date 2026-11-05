"""Contract only: no undocumented third-party API or credential assumptions."""

from typing import Protocol

from youtube_niche_mcp.domain.foundation import Capability, Observation


class ObservationProvider(Protocol):
    name: str

    def capability(self) -> Capability: ...

    async def observe(self, kind: str, ids: list[str], capture_id: str) -> list[Observation]: ...


class CapabilityProvider(Protocol):
    """Optional acquisition operations are routed by capability, not forced on every provider."""

    name: str

    def capabilities(self) -> list[dict]: ...
