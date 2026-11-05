from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from youtube_niche_mcp.api.contracts import QuotaContract
from youtube_niche_mcp.domain.foundation import timestamp


@dataclass(frozen=True)
class QuotaEntry:
    endpoint: str
    request_count: int
    assumed_cost: int
    bucket: str
    requested_at: str
    contract_version: str


class QuotaLedger:
    def __init__(self, contract: QuotaContract | None = None, sink: Callable | None = None):
        self.contract = contract or QuotaContract()
        self.entries: list[QuotaEntry] = []
        self.sink = sink

    def record(self, endpoint: str, at: datetime) -> None:
        method = self.contract.endpoints[endpoint]
        entry = QuotaEntry(
            endpoint, 1, method.cost, method.bucket, timestamp(at), self.contract.version
        )
        if self.sink:
            self.sink(entry)
        self.entries.append(entry)

    def totals(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for entry in self.entries:
            totals[entry.bucket] = totals.get(entry.bucket, 0) + entry.assumed_cost
        return totals
