"""Verify preserved research, formula modules, migrations and prior reports against Phase 4."""

import json
import subprocess
from pathlib import Path

from youtube_niche_mcp.db.schema import MIGRATIONS

ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT = "b53e5bfacf33ce581f3f7ba7e5eaeaee990f5486"


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
        or name
        in {
            "src/youtube_niche_mcp/db/phase2.py",
            "src/youtube_niche_mcp/db/phase2_5.py",
            "src/youtube_niche_mcp/db/phase3.py",
        }
        or (name.startswith("docs/phase-") and not name.startswith("docs/phase-5"))
        or name.startswith("scripts/acceptance_phase")
    ]
    for name in names:
        original = subprocess.run(
            ["git", "show", f"{CHECKPOINT}:{name}"], cwd=ROOT, capture_output=True, check=True
        ).stdout
        current = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
        if current != original.replace(b"\r\n", b"\n"):
            raise ValueError(f"Frozen Phase-4 artifact changed: {name}")
    expected = [
        "df4ead10f9d64ecd7950b0c37717976e475bd2dd6e0a6ca1d047554509f12177",
        "c44e9bcca6a67d4007c209e306958ed31d02ef60f25aeeac01bb0bfae34a89c9",
        "7296eb9bec26ba21ea8caa0f6be50895e7944fd987d06106b08e873ee588ae7d",
        "384125aba24302812cedd74d6dd9aeb088a2e40ba37b4540a82ad003beac391d",
        "cf8f065640223bf1192b54f44ecef9acde06f738f3624cfec21ba55afec61383",
    ]
    assert [m.checksum for m in MIGRATIONS[:5]] == expected
    print(
        json.dumps(
            {
                "ok": True,
                "checkpoint": CHECKPOINT,
                "frozen_files": names,
                "migration_checksums_v1_v5": expected,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
