"""Assert the Phase 6 methodology, sources, reports and migrations are unchanged."""

import json
import subprocess
from pathlib import Path

from youtube_niche_mcp.db.schema import MIGRATIONS

ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT = "8ce01aa05b1c56be93305fc57672d8fb792e35be"
INTEGRATION = {
    "tests/" + n
    for n in (
        "test_server.py",
        "test_history.py",
        "test_analysis_integrity.py",
        "test_cli.py",
        "test_cache_capabilities.py",
        "test_nexlev_client.py",
        "test_db.py",
        "test_decision_integrity.py",
        "test_qualitative_integrity.py",
    )
}


def original(name):
    return subprocess.run(
        ["git", "show", f"{CHECKPOINT}:{name}"], cwd=ROOT, capture_output=True, check=True
    ).stdout


def main():
    files = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", CHECKPOINT],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    frozen = [
        n
        for n in files
        if n.startswith(
            (
                "research_specs/",
                "src/youtube_niche_mcp/analysis/",
                "src/youtube_niche_mcp/decision/",
                "src/youtube_niche_mcp/qualitative/",
                "src/youtube_niche_mcp/eligibility/",
                "src/youtube_niche_mcp/history/",
                "src/youtube_niche_mcp/api/",
                "src/youtube_niche_mcp/collectors/",
                "docs/phase-",
                "scripts/acceptance",
                "scripts/verify_phase",
                "tests/",
            )
        )
        and n not in INTEGRATION
    ]
    for name in frozen:
        before, after = original(name), (ROOT / name).read_bytes()
        if name.startswith("research_specs/"):
            assert before == after, name
        else:
            assert before.replace(b"\r\n", b"\n") == after.replace(b"\r\n", b"\n"), name
    expected = [
        "df4ead10f9d64ecd7950b0c37717976e475bd2dd6e0a6ca1d047554509f12177",
        "c44e9bcca6a67d4007c209e306958ed31d02ef60f25aeeac01bb0bfae34a89c9",
        "7296eb9bec26ba21ea8caa0f6be50895e7944fd987d06106b08e873ee588ae7d",
        "384125aba24302812cedd74d6dd9aeb088a2e40ba37b4540a82ad003beac391d",
        "cf8f065640223bf1192b54f44ecef9acde06f738f3624cfec21ba55afec61383",
        "80c2b3747e424560ade285b19375634144e1510b1a2e8295c28f86aee2ed7d50",
    ]
    assert [m.checksum for m in MIGRATIONS[:6]] == expected
    state = (ROOT / "PROJECT_STATE.md").read_bytes()
    assert state.endswith(original("PROJECT_STATE.md")), "Phase 0-6 state archive changed"
    print(
        json.dumps(
            {
                "ok": True,
                "checkpoint": CHECKPOINT,
                "frozen_file_count": len(frozen),
                "files": frozen,
                "migration_checksums_v1_v6": expected,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
