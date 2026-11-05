import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from youtube_niche_mcp.domain.provenance import Provenance
from youtube_niche_mcp.domain.states import Precision, SourceKind


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def provenance():
    observed = datetime(2026, 10, 2, 6, tzinfo=UTC)
    return Provenance(
        source="fixture",
        source_kind=SourceKind.PUBLIC_API,
        source_version="fixture-v1",
        precision=Precision.EXACT,
        published_at=observed - timedelta(days=40),
        observed_at=observed,
        available_at=observed,
        maturity_at=observed - timedelta(days=10),
    )


@pytest.fixture(autouse=True)
def isolate_configuration(monkeypatch, tmp_path):
    """Never let tests inherit the user's real key or configured research DB."""
    for variable in (
        "YOUTUBE_API_KEY",
        "NEXLEV_API_KEY",
        "YTNMCP_LOG_LEVEL",
        "YTNMCP_DB_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("YTNMCP_DB_PATH", str(tmp_path / "test.sqlite3"))


@pytest.fixture(autouse=True)
def prohibit_live_api(monkeypatch):
    import os

    import httpx

    for key in list(os.environ):
        if key.startswith("YTNMCP_") and key != "YTNMCP_DB_PATH":
            monkeypatch.delenv(key, raising=False)

    async def forbidden(*args, **kwargs):
        raise AssertionError("Standard tests must never contact external HTTP services")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


@pytest.fixture
def api_fixture():
    return json.loads((Path(__file__).parent / "fixtures" / "public_api.json").read_text())


@pytest.fixture
def now():
    return datetime(2026, 10, 2, 6, tzinfo=UTC)


@pytest.fixture
def repository(tmp_path, now):
    from youtube_niche_mcp.db.connection import connect
    from youtube_niche_mcp.db.migrations import migrate
    from youtube_niche_mcp.history.repository import HistoryRepository

    with connect(tmp_path / "history.sqlite3") as connection:
        migrate(connection)
        yield HistoryRepository(connection, clock=lambda: now, secrets=("fixture-secret",))


@pytest.fixture
def observation_factory(now):
    from youtube_niche_mcp.domain.evidence import NumericEvidence
    from youtube_niche_mcp.domain.foundation import Metadata, Observation

    def create(
        value=100,
        *,
        at=None,
        available=None,
        kind="video",
        entity_id=None,
        source="youtube:videos.list",
        capture_id=None,
        title="Earlier title",
        publication=None,
    ):
        at = at or now
        p = Provenance(
            source=source,
            source_kind=SourceKind.PROVIDER
            if source.startswith("provider")
            else SourceKind.PUBLIC_API,
            source_version="fixture-v1",
            precision=Precision.EXACT,
            observed_at=at,
            available_at=available or at,
        )
        return Observation(
            capture_id=capture_id or at.isoformat(),
            entity_kind=kind,
            entity_id=entity_id or ("UC" + "a" * 22 if kind == "channel" else "a" * 11),
            request_at=at,
            provenance=p,
            metadata=Metadata(title=title, publication_at=publication),
            metrics={
                "subscriber_count" if kind == "channel" else "view_count": NumericEvidence(
                    state="available", value=value, reason="fixture", provenance=p
                )
            },
            metric_definition="fixture-public-count-v1",
        )

    return create
