import json
from datetime import timedelta

import pytest
from pydantic import SecretStr

from youtube_niche_mcp.api.client import APIError
from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.domain.foundation import Outcome
from youtube_niche_mcp.domain.states import EvidenceState
from youtube_niche_mcp.server import server_status
from youtube_niche_mcp.services.cache import DerivedIdentity, LiveCache
from youtube_niche_mcp.services.capabilities import capabilities, operational_status


def test_cache_fresh_expired_refresh_source_keys_history_unchanged(
    repository, observation_factory, now
):
    time = [now]
    repository.append(observation_factory())
    before = [tuple(r) for r in repository.connection.execute("SELECT * FROM video_observations")]
    cache = LiveCache(
        repository.connection, ttl_seconds=60, stale_seconds=30, clock=lambda: time[0]
    )
    args = ("youtube", "videos.list", {"id": "aaaaaaaaaaa", "part": "snippet"})
    first = cache.put(*args, {"title": "A"})
    assert cache.get(*args) == first
    assert cache.key("youtube", "route", {"a": 1, "b": 2}) == cache.key(
        "youtube", "route", {"b": 2, "a": 1}
    )
    assert cache.key("provider", "route", {"a": 1}) != cache.key("youtube", "route", {"a": 1})
    time[0] += timedelta(seconds=60)
    assert cache.get(*args) is None
    stale = cache.get(*args, allow_stale=True)
    assert stale.stale and stale.payload == {"title": "A"}
    time[0] += timedelta(seconds=30)
    assert cache.get(*args, allow_stale=True) is None
    cache.put(*args, {"title": "B"})
    assert cache.get(*args).payload == {"title": "B"}
    assert [
        tuple(r) for r in repository.connection.execute("SELECT * FROM video_observations")
    ] == before
    for purpose in ("snapshot", "known_at_time", "analysis"):
        with pytest.raises(ValueError, match="historical"):
            cache.get(*args, allow_stale=True, purpose=purpose)


@pytest.mark.anyio
async def test_cache_stale_only_explicit_transient_fallback(repository, now):
    time = [now]
    cache = LiveCache(repository.connection, ttl_seconds=1, stale_seconds=10, clock=lambda: time[0])
    args = ("youtube", "videos.list", {"id": "aaaaaaaaaaa"})
    cache.put(*args, {"title": "cached"})
    time[0] += timedelta(seconds=2)

    async def fail():
        raise APIError("videos.list", Outcome.TRANSIENT_ERROR, "transport_error")

    assert (await cache.load(*args, fail, allow_stale=True)).stale
    with pytest.raises(APIError):
        await cache.load(*args, fail)

    async def quota():
        raise APIError("videos.list", Outcome.QUOTA_LIMITED, "quotaExceeded")

    with pytest.raises(APIError):
        await cache.load(*args, quota, allow_stale=True)

    async def succeed():
        return {"title": "refreshed"}

    assert not (await cache.load(*args, succeed)).stale


@pytest.mark.parametrize(
    "payload",
    [
        {"key": "arbitrary"},
        {"Authorization": "arbitrary"},
        {"X-Goog-Api-Key": "arbitrary"},
        {"Cookie": "arbitrary"},
        {"nested": {"access_token": "arbitrary"}},
        {"title": "fixture-secret"},
    ],
)
def test_cache_and_history_secret_safety(repository, observation_factory, now, payload):
    cache = LiveCache(repository.connection, clock=lambda: now, secrets=("fixture-secret",))
    with pytest.raises(ValueError, match="Credential"):
        cache.put("youtube", "videos.list", {}, payload)
    with pytest.raises(ValueError, match="Credential"):
        repository.append(observation_factory(title="fixture-secret"))
    assert repository.connection.execute("SELECT COUNT(*) FROM source_records").fetchone()[0] == 0
    assert repository.connection.execute("SELECT COUNT(*) FROM live_cache").fetchone()[0] == 0
    with pytest.raises(ValueError, match="Credential"):
        cache.key("youtube", "videos.list", {"key": "arbitrary"})


def test_cache_retention_bound_and_derived_identity(repository, now):
    time = [now]
    cache = LiveCache(
        repository.connection, ttl_seconds=30 * 86400, stale_seconds=300, clock=lambda: time[0]
    )
    cache.put("youtube", "route", {}, {"title": "fixture"})
    time[0] += timedelta(days=30)
    assert cache.get("youtube", "route", {}, allow_stale=True) is None
    a = DerivedIdentity("inputs-1", "analysis-v1")
    assert a.key != DerivedIdentity("inputs-2", "analysis-v1").key
    assert a.key != DerivedIdentity("inputs-1", "analysis-v2").key
    assert a.permission_state == "policy_permission_required"
    assert repository.connection.execute("SELECT COUNT(*) FROM derived_cache").fetchone()[0] == 0


def test_capabilities_unconfigured_configured_policy_history():
    unconfigured = {v.name: v for v in capabilities(Settings())}
    assert not unconfigured["youtube_public_api"].enabled
    assert unconfigured["snapshot_history"].state == EvidenceState.INSUFFICIENT_HISTORY
    assert unconfigured["derived_analytics"].state == EvidenceState.POLICY_PERMISSION_REQUIRED
    assert (
        unconfigured["captions_and_owner_analytics"].state
        == EvidenceState.OWNER_AUTHORIZATION_REQUIRED
    )
    assert not unconfigured["auxiliary_provider"].enabled
    configured = capabilities(
        Settings(youtube_api_key=SecretStr("fixture-secret")), history_count=2
    )
    assert configured[0].enabled and configured[1].enabled
    assert "fixture-secret" not in json.dumps([v.model_dump(mode="json") for v in configured])


def test_status_without_db_no_creation_and_secret_safe(tmp_path):
    settings = Settings(
        db_path=tmp_path / "absent" / "history.sqlite3", youtube_api_key=SecretStr("fixture-secret")
    )
    payload = server_status(settings)
    assert payload.phase == 8
    assert payload.schema_version == 7
    assert payload.actual_schema_version is None
    assert payload.youtube_api_key_present
    assert payload.history_state == "insufficient_history"
    assert len(payload.implemented_tools) == 15
    assert "fixture-secret" not in payload.model_dump_json()
    assert operational_status(settings)["state"] == "not_initialized"
    assert not settings.db_path.parent.exists()
