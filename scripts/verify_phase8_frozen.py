"""Verify Phase 7 frozen methodology, migrations, history, tags and prior bundles."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT = "61305079c14f3196e1b28a517079f9bad7e29820"
EXCEPTIONS = {
    "tests/test_server.py",
    "tests/test_cache_capabilities.py",
    "tests/test_nexlev_client.py",
}


def original(name):
    return subprocess.run(
        ["git", "show", f"{CHECKPOINT}:{name}"], cwd=ROOT, capture_output=True, check=True
    ).stdout


def main():
    names = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", CHECKPOINT],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    prefixes = (
        "research_specs/",
        "src/youtube_niche_mcp/analysis/",
        "src/youtube_niche_mcp/decision/",
        "src/youtube_niche_mcp/qualitative/",
        "src/youtube_niche_mcp/eligibility/",
        "src/youtube_niche_mcp/history/",
        "src/youtube_niche_mcp/api/",
        "src/youtube_niche_mcp/collectors/",
        "src/youtube_niche_mcp/db/",
        "docs/phase-",
        "scripts/acceptance",
        "scripts/verify_phase",
        "tests/",
    )
    frozen = [n for n in names if n.startswith(prefixes) and n not in EXCEPTIONS]
    for name in frozen:
        before, after = original(name), (ROOT / name).read_bytes()
        if not name.startswith("research_specs/"):
            before, after = before.replace(b"\r\n", b"\n"), after.replace(b"\r\n", b"\n")
        assert before == after, name
    for name in EXCEPTIONS:
        before = original(name).replace(b"\r\n", b"\n")
        after = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
        expected = before.replace(b".phase == 7", b".phase == 8")
        assert expected == after, name
    assert (ROOT / "PROJECT_STATE.md").read_bytes().endswith(original("PROJECT_STATE.md"))
    receipt = json.loads((ROOT / "docs/phase-8-source-receipt.json").read_text())
    for tag, sha in receipt["prior_tags"].items():
        actual = subprocess.run(
            ["git", "rev-parse", tag], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        assert actual == sha, tag
    bundles = json.loads((ROOT / "docs/phase-8-prior-bundles.json").read_text())
    for row in bundles:
        path = ROOT.parent / Path(row["path"]).name
        assert path.stat().st_size == row["size_bytes"], path
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"], path
    print(
        json.dumps(
            {
                "ok": True,
                "checkpoint": CHECKPOINT,
                "frozen_files": len(frozen),
                "prior_bundles": len(bundles),
                "prior_tags": len(receipt["prior_tags"]),
            }
        )
    )


if __name__ == "__main__":
    main()
