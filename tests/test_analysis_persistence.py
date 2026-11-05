import json
import sqlite3
from datetime import timedelta

import pytest
from phase3_helpers import metrics, seed

from youtube_niche_mcp.analysis.repository import AnalysisUnavailable
from youtube_niche_mcp.analysis.service import AnalysisService
from youtube_niche_mcp.cli import main
from youtube_niche_mcp.db.connection import connect
from youtube_niche_mcp.db.migrations import migrate
from youtube_niche_mcp.db.schema import MIGRATIONS, Migration
from youtube_niche_mcp.db.status import integrity


def test_permission_revocation_blocks_derivative_read(repository, observation_factory, now):
    vd, _, _, opt = seed(repository, observation_factory, now, [[10000]])
    service = AnalysisService(repository)
    bundle = service.analyze(vd, opt)
    repository.connection.execute("DELETE FROM retention_permissions")
    with pytest.raises(AnalysisUnavailable, match="dependency"):
        service.inspect(bundle.run.run_id)
    current = service.analyze(vd, opt)
    assert current.run.run_id != bundle.run.run_id and metrics(current)["F3"].value is None


def test_baseline_freeze_future_observation_and_current_subscribers(
    repository, observation_factory, now
):
    vd, _, ids, opt = seed(repository, observation_factory, now, [[100] * 5 + [300], [100] * 2])
    service = AnalysisService(repository)
    opt = opt.model_copy(update={"candidate_id": ids[5], "baseline_cutoff": now})
    first = service.analyze(vd, opt)
    repository.append(observation_factory(999999, kind="channel", at=now))
    assert service.analyze(vd, opt) == first
    old = opt.model_copy(update={"baseline_cutoff": now - timedelta(days=3), "coverage": ()})
    f = metrics(service.analyze(vd, old))["F1"]
    assert f.value is None and "not frozen" in f.details["reason"]


def test_conflicted_topics_are_not_other(repository, observation_factory, now):
    from youtube_niche_mcp.eligibility.models import Claim, NicheMembership, Subject
    from youtube_niche_mcp.eligibility.repository import EligibilityRepository

    vd, _, ids, opt = seed(repository, observation_factory, now, [[12000]], topics=["a"])
    e = EligibilityRepository(repository)
    at = now - timedelta(days=2)
    subject = Subject(entity_kind="video", entity_id=ids[0])
    c = Claim(
        subject=subject,
        field="niche_membership",
        value={"node_id": "a", "state": "excluded"},
        basis="human_review",
        source="independent conflicting source",
        source_version="v1",
        observed_at=at,
        available_at=at,
        reason="Synthetic disagreement",
        data_origin="independent_annotation",
        permission_state="permitted",
    )
    eid = e.append_claim(c)
    e.assign_niche(
        NicheMembership(
            subject=subject,
            node_id="a",
            taxonomy_version="topics-v1",
            state="excluded",
            confidence="high",
            evidence_ids=(eid,),
            rule_version="topic-v1",
            source=c.source,
            decided_at=at,
            available_at=at,
            reason=c.reason,
        )
    )
    f = metrics(AnalysisService(repository).analyze(vd, opt))["F8"]
    assert f.value is None and f.details["conflicted"] == 1 and not f.details["families"]


def test_frozen_eligibility_later_provider_cannot_revise(repository, observation_factory, now):
    from youtube_niche_mcp.eligibility.models import Claim, Subject
    from youtube_niche_mcp.eligibility.repository import EligibilityRepository

    vd, _, ids, opt = seed(repository, observation_factory, now, [[10000]])
    service = AnalysisService(repository)
    first = service.analyze(vd, opt)
    EligibilityRepository(repository).append_claim(
        Claim(
            subject=Subject(entity_kind="video", entity_id=ids[0]),
            field="faceless",
            value=False,
            basis="provider_label",
            source="nexlev.faceless_classifier",
            source_version="v1",
            observed_at=now,
            available_at=now,
            reason="Later provider label",
            data_origin="provider_data",
        )
    )
    assert service.analyze(vd, opt) == first


@pytest.mark.parametrize("version", [0, 1, 2, 3, 4])
def test_frozen_migrations_upgrade_v5(tmp_path, version):
    expected = [
        "df4ead10f9d64ecd7950b0c37717976e475bd2dd6e0a6ca1d047554509f12177",
        "c44e9bcca6a67d4007c209e306958ed31d02ef60f25aeeac01bb0bfae34a89c9",
        "7296eb9bec26ba21ea8caa0f6be50895e7944fd987d06106b08e873ee588ae7d",
        "384125aba24302812cedd74d6dd9aeb088a2e40ba37b4540a82ad003beac391d",
    ]
    assert [m.checksum for m in MIGRATIONS[:4]] == expected
    with connect(tmp_path / "upgrade.sqlite3") as c:
        if version:
            migrate(c, MIGRATIONS[:version])
        assert migrate(c, MIGRATIONS[:5]) == list(range(version + 1, 6)) and integrity(c)["ok"]
        assert (
            c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0] == 34
        )


def test_v5_failure_atomic_preserves_v4(tmp_path):
    with connect(tmp_path / "rollback.sqlite3") as c:
        migrate(c, MIGRATIONS[:4])
        broken = Migration(5, "broken", (*MIGRATIONS[4].statements, "INVALID SQL"))
        with pytest.raises(sqlite3.OperationalError):
            migrate(c, (*MIGRATIONS[:4], broken))
        assert not c.execute("SELECT 1 FROM sqlite_master WHERE name='analysis_runs'").fetchone()
        assert migrate(c, MIGRATIONS[:5]) == [5] and integrity(c)["ok"]


def test_formulas_cli_offline_no_db(tmp_path, capsys):
    path = tmp_path / "absent.sqlite3"
    assert main(["--db", str(path), "analysis", "formulas"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["public_tools"] == 0 and "F19" in payload["formulas"] and not path.exists()


def test_cli_run_inspect_stored_only(repository, observation_factory, now, tmp_path, capsys):
    vd, _, _, opt = seed(repository, observation_factory, now, [[10000]])
    repository.connection.commit()
    path = repository.connection.execute("PRAGMA database_list").fetchone()[2]
    profile = tmp_path / "options.json"
    profile.write_text(opt.model_dump_json(), encoding="utf-8")
    assert main(["--db", path, "analysis", "run", "--cohort", vd, "--options", str(profile)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] and len(payload["metrics"]) == 12
    assert main(["--db", path, "analysis", "inspect", payload["run"]["run_id"]]) == 0
    assert json.loads(capsys.readouterr().out) == payload


def test_viral_feed_is_not_entrant_frame(repository, observation_factory, now):
    vd, _, _, opt = seed(repository, observation_factory, now, [[1000000]])
    f = metrics(AnalysisService(repository).analyze(vd, opt))["F19"]
    assert f.value is None and "entrant frame" in f.details["reason"]


def test_unpositioned_exposure_cannot_claim_complete_upload_fraction(
    repository, observation_factory, now
):
    from youtube_niche_mcp.analysis.exposure import exposure
    from youtube_niche_mcp.analysis.outcomes import resolve

    vd, cd, _, opt = seed(repository, observation_factory, now, [[100]])
    frame = AnalysisService(repository).repository.load(cd, vd, opt)
    unresolved = frame.videos[0].model_copy(update={"publication_at": None})
    frame = frame.model_copy(update={"videos": (unresolved,)})
    result = exposure(frame, (resolve(unresolved, opt, now),), opt, grouped=True)
    assert result["unpositioned_records"] and result["upload_fraction"] is None
    assert result["upload_bounds"]["state"] == "finite_frame_not_established"
    assert result["unknown_entrants"] == 1
