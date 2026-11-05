"""Verify preserved research, formula modules, migrations and prior reports against Phase 5."""

import json
import subprocess
from pathlib import Path

from youtube_niche_mcp.db.schema import MIGRATIONS

ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT = "99c90d6dec642b74ce4942130d1e4fe18ec35009"


def main():
    listing = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", CHECKPOINT],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    names = [
        name
        for name in listing
        if name.startswith("research_specs/")
        or (
            name.startswith("src/youtube_niche_mcp/analysis/")
            and name
            not in {
                "src/youtube_niche_mcp/analysis/models.py",
                "src/youtube_niche_mcp/analysis/repository.py",
            }
        )
        or name.startswith("src/youtube_niche_mcp/qualitative/")
        or name
        in {
            "src/youtube_niche_mcp/db/phase2.py",
            "src/youtube_niche_mcp/db/phase2_5.py",
            "src/youtube_niche_mcp/db/phase3.py",
            "src/youtube_niche_mcp/db/phase5.py",
            "src/youtube_niche_mcp/db/schema.py",
        }
        or (name.startswith("docs/phase-") and not name.startswith("docs/phase-6"))
        or name.startswith("scripts/acceptance_phase")
    ]
    for name in names:
        original = subprocess.run(
            ["git", "show", f"{CHECKPOINT}:{name}"], cwd=ROOT, capture_output=True, check=True
        ).stdout
        current = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
        if name.startswith("research_specs/") and (ROOT / name).read_bytes() != original:
            raise ValueError(f"Research specification bytes changed: {name}")
        if current != original.replace(b"\r\n", b"\n"):
            raise ValueError(f"Frozen Phase-5 artifact changed: {name}")
    expected = [
        "df4ead10f9d64ecd7950b0c37717976e475bd2dd6e0a6ca1d047554509f12177",
        "c44e9bcca6a67d4007c209e306958ed31d02ef60f25aeeac01bb0bfae34a89c9",
        "7296eb9bec26ba21ea8caa0f6be50895e7944fd987d06106b08e873ee588ae7d",
        "384125aba24302812cedd74d6dd9aeb088a2e40ba37b4540a82ad003beac391d",
        "cf8f065640223bf1192b54f44ecef9acde06f738f3624cfec21ba55afec61383",
    ]
    expected.append("80c2b3747e424560ade285b19375634144e1510b1a2e8295c28f86aee2ed7d50")
    assert [m.checksum for m in MIGRATIONS] == expected
    print(
        json.dumps(
            {
                "ok": True,
                "checkpoint": CHECKPOINT,
                "frozen_files": names,
                "migration_checksums_v1_v6": expected,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
