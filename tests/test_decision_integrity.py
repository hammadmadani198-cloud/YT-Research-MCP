"""Retention, permissions, known-at-time, immutable replay and zero-network integration."""

import ast
import json
import sqlite3
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from phase6_helpers import options_json, result, setup

from youtube_niche_mcp.analysis.repository import AnalysisUnavailable
from youtube_niche_mcp.cli import main
from youtube_niche_mcp.decision.models import DecisionOptions, PolicyClock
from youtube_niche_mcp.decision.service import DecisionService


def test_deterministic_replay_preserves_source_runs(repository, observation_factory, now):
    base, q, opt, _, _ = setup(repository, observation_factory, now)
    s = DecisionService(repository)
    before = [
        tuple(r)
        for r in repository.connection.execute("SELECT * FROM analysis_runs ORDER BY run_id")
    ]
    first = s.analyze(opt)
    count = repository.connection.execute("SELECT COUNT(*) FROM analysis_runs").fetchone()[0]
    assert first == s.analyze(opt) == s.inspect(first.run.run_id)
    assert (
        repository.connection.execute("SELECT COUNT(*) FROM analysis_runs").fetchone()[0] == count
    )
    assert s.repository.read(base.run.run_id) == base and s.repository.read(q.run.run_id) == q
    after = {r[0]: tuple(r) for r in repository.connection.execute("SELECT * FROM analysis_runs")}
    assert all(after[r[0]] == r for r in before)


def test_read_after_clock_advance_uses_immutable_results(repository, observation_factory, now):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    s = DecisionService(repository)
    first = s.analyze(opt)
    repository.clock = lambda: now + timedelta(hours=1)
    assert s.inspect(first.run.run_id) == first
    assert s.analyze(opt) == first


@pytest.mark.parametrize(
    "table",
    [
        "analysis_runs",
        "cohort_definitions",
        "qualitative_annotations",
        "classification_claims",
        "creator_group_memberships",
        "source_records",
        "retention_permissions",
        "discovery_runs",
    ],
)
def test_removed_ancestry_blocks_cached_decision(repository, observation_factory, now, table):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    s = DecisionService(repository)
    b = s.analyze(opt)
    repository.connection.execute(f"DELETE FROM {table}")
    if table == "source_records":
        repository.connection.execute("DELETE FROM statistical_history")
    with pytest.raises(AnalysisUnavailable):
        s.inspect(b.run.run_id)


def test_discovery_protocol_mutation_invalidates_decision_and_sensitivity(
    repository, observation_factory, now
):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    s = DecisionService(repository)
    b = s.analyze(opt)
    rid = next(r["run_id"] for r in result(b, "decision").details["sensitivity"] if r["run_id"])
    repository.connection.execute(
        "UPDATE discovery_runs SET query='tampered' WHERE run_id='official'"
    )
    with pytest.raises(AnalysisUnavailable, match="changed"):
        s.inspect(b.run.run_id)
    with pytest.raises(AnalysisUnavailable, match="changed"):
        s.inspect(rid)


def test_expired_policy_and_review_do_not_survive_cache(repository, observation_factory, now):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    s = DecisionService(repository)
    b = s.analyze(opt)
    repository.clock = lambda: now + timedelta(days=11)
    with pytest.raises(AnalysisUnavailable, match="expired"):
        s.inspect(b.run.run_id)
    later = s.analyze(opt)
    assert result(later, "decision").state == "high_rights_or_policy_dependency"
    assert result(later, "decision").details["unavailable_source_runs"]
    assert not result(later, "decision").details["evidence"]["coverage"]["qualitative"]


def test_input_permission_revocation_invalidates_sensitivity(repository, observation_factory, now):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    s = DecisionService(repository)
    b = s.analyze(opt)
    rid = next(
        r["run_id"]
        for r in result(b, "decision").details["sensitivity"]
        if r["family"] == "missingness"
    )
    repository.connection.execute("DELETE FROM retention_permissions")
    with pytest.raises(AnalysisUnavailable):
        s.inspect(rid)


def test_decision_and_sensitivity_tables_are_append_only(repository, observation_factory, now):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    b = DecisionService(repository).analyze(opt)
    with pytest.raises(sqlite3.IntegrityError):
        repository.connection.execute(
            "UPDATE analysis_runs SET input_hash='changed' WHERE run_id=?", (b.run.run_id,)
        )


def test_decision_internal_cli_and_public_tool_catalog(
    repository, observation_factory, now, tmp_path, capsys, monkeypatch
):
    # The CLI uses the real current clock. This synthetic evidence frame is fixed
    # to October 2026; keep both CLI and fixture clocks aligned in the test.
    from youtube_niche_mcp.history import repository as history_module

    original_class = history_module.HistoryRepository

    class FixtureClockRepository(original_class):
        def __init__(self, connection, *args, **kwargs):
            kwargs.setdefault("clock", lambda: now)
            super().__init__(connection, *args, **kwargs)

    monkeypatch.setattr(history_module, "HistoryRepository", FixtureClockRepository)
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    database = repository.connection.execute("PRAGMA database_list").fetchone()[2]
    repository.connection.commit()
    p = tmp_path / "options.json"
    p.write_text(options_json(opt), encoding="utf-8")
    assert main(["--db", database, "decision", "run", "--options", str(p)]) == 0
    body = json.loads(capsys.readouterr().out)
    assert body["ok"] and body["run"]["formula_version"] == "phase6-v1"
    assert main(["--db", database, "decision", "inspect", body["run"]["run_id"]]) == 0
    assert json.loads(capsys.readouterr().out)["run"]["run_id"] == body["run"]["run_id"]
    assert main(["decision", "f17-config"]) == 0
    assert json.loads(capsys.readouterr().out)["sorting_only"]
    assert main(["tool", "list"]) == 0
    tools = json.loads(capsys.readouterr().out)
    assert len(tools["registered_tools"]) == 15


def test_zero_http_and_quota(repository, observation_factory, now, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No HTTP from decision layer")

    monkeypatch.setattr(httpx.Client, "request", forbidden)
    monkeypatch.setattr(httpx.AsyncClient, "request", forbidden)
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    DecisionService(repository).analyze(opt)
    assert repository.connection.execute("SELECT COUNT(*) FROM quota_requests").fetchone()[0] == 0
    for p in (Path(__file__).parents[1] / "src/youtube_niche_mcp/decision").glob("*.py"):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        assert not any(
            isinstance(n, (ast.Import, ast.ImportFrom)) and "httpx" in ast.unparse(n)
            for n in ast.walk(tree)
        )


@pytest.mark.parametrize("field,value", [("goal", 1), ("age_days", 7), ("tolerance_seconds", 100)])
def test_incompatible_base_measurements_rejected(
    repository, observation_factory, now, field, value
):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    with pytest.raises(ValueError, match="match canonical"):
        DecisionService(repository).analyze(opt.model_copy(update={field: value}))


def test_future_cutoff_rejected(repository, observation_factory, now):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    with pytest.raises(ValueError, match="Future"):
        DecisionService(repository).analyze(
            opt.model_copy(update={"cutoff": now + timedelta(days=1)})
        )


def test_future_policy_receipt_rejected(now):
    with pytest.raises(ValueError):
        PolicyClock(
            snapshot_id="x",
            retrieved_at=now,
            refresh_by=now,
            available_at=now,
            expires_at=now + timedelta(days=1),
            provenance_reference="synthetic",
        )


def test_decision_manifest_round_trip_strict(repository, observation_factory, now):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    assert DecisionOptions.model_validate_json(options_json(opt)) == opt
    body = opt.model_dump(mode="json")
    body["confidence_percentage"] = 93.7
    with pytest.raises(ValueError):
        DecisionOptions.model_validate(body)


def test_sensitive_derivatives_remain_separate_from_base(repository, observation_factory, now):
    base, _, opt, _, _ = setup(repository, observation_factory, now)
    opt = opt.model_copy(
        update={"sensitivity": opt.sensitivity.model_copy(update={"goals": (25000,)})}
    )
    b = DecisionService(repository).analyze(opt)
    variant = next(
        r for r in result(b, "decision").details["sensitivity"] if r["label"] == "goal:25000"
    )
    saved = DecisionService(repository).inspect(variant["run_id"])
    assert saved.run.options.parent_run_id == base.run.run_id
    assert saved.run.options.changed_option == {"goal": 25000}
    assert saved.run.input_hash == saved.run.options.input_identity
    assert saved.run.run_id in b.run.input_ids


def test_policy_context_changes_sensitivity_identity(repository, observation_factory, now):
    _, _, opt, _, _ = setup(repository, observation_factory, now)
    service = DecisionService(repository)
    first = service.analyze(opt)
    receipt = PolicyClock(
        snapshot_id="stale-receipt",
        retrieved_at=now - timedelta(days=40),
        refresh_by=now - timedelta(days=10),
        available_at=now - timedelta(days=40),
        expires_at=now + timedelta(days=5),
        provenance_reference="Retained clock only",
    )
    second = service.analyze(opt.model_copy(update={"policy_clocks": (receipt,)}))
    a = result(first, "decision").details["sensitivity"]
    b = result(second, "decision").details["sensitivity"]
    assert a[0]["run_id"] != b[0]["run_id"]
    assert service.inspect(a[0]["run_id"]).metrics[0].details == a[0]
    assert service.inspect(b[0]["run_id"]).metrics[0].details == b[0]
