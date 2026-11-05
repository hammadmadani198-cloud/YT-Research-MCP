"""Capture exact offline acceptance outputs without changing Phase 0/1/2/2.5 reports."""

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    scratch = (root / ".pytest-tmp" / f"phase4-acceptance-{uuid4().hex}").resolve()
    if not scratch.is_relative_to(root) or scratch.exists():
        raise ValueError("Acceptance scratch must be a new directory inside the repository")
    scratch.mkdir(parents=True)
    python = sys.executable
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"YOUTUBE_API_KEY", "NEXLEV_API_KEY"} and not key.startswith("YTNMCP_")
    }
    env["PYTHONUTF8"] = "1"
    env["YTNMCP_DB_PATH"] = str(root / "data" / "research.sqlite3")
    cli = [python, "-m", "youtube_niche_mcp"]
    clean, v1, v2, v3 = (
        scratch / name for name in ("clean.sqlite3", "v1.sqlite3", "v2.sqlite3", "v3.sqlite3")
    )
    imports = "\n".join(
        [
            "import importlib, pkgutil, youtube_niche_mcp",
            "modules=list(pkgutil.walk_packages(youtube_niche_mcp.__path__,",
            "    youtube_niche_mcp.__name__+'.'))",
            "for module in modules:",
            "    if not module.name.endswith('__main__'):",
            "        importlib.import_module(module.name)",
            "print('Package import sweep passed: '+str(len(modules))+' modules')",
        ]
    )
    seed_v1 = "\n".join(
        [
            "import sys",
            "from pathlib import Path",
            "from youtube_niche_mcp.db.connection import connect",
            "from youtube_niche_mcp.db.migrations import migrate",
            "from youtube_niche_mcp.db.schema import MIGRATIONS",
            "with connect(Path(sys.argv[1])) as connection:",
            "    installed=migrate(connection,MIGRATIONS[:int(sys.argv[2])])",
            "print('Versioned fixture installed: '+str(installed))",
        ]
    )
    commands = [
        [python, "-m", "pip", "check"],
        [python, "-m", "pytest", "-q", "--tb=short", f"--basetemp={scratch / 'tests'}"],
        [python, "-m", "ruff", "check", "."],
        [python, "-m", "ruff", "format", "--check", "."],
        [python, "-c", imports],
        [*cli, "--version"],
        [*cli, "config", "check"],
        [*cli, "api", "capability"],
        [*cli, "history", "status"],
        [*cli, "snapshot", "status"],
        [*cli, "eligibility", "rules"],
        [*cli, "taxonomy", "status"],
        [*cli, "cohort", "status"],
        [*cli, "tool", "list"],
        [*cli, "db", "status"],
        [*cli, "db", "integrity"],
        [*cli, "verify"],
        [*cli, "--db", str(clean), "migrate"],
        [*cli, "--db", str(clean), "migrate"],
        [*cli, "--db", str(clean), "db", "integrity"],
        [*cli, "--db", str(clean), "verify"],
        [python, "-c", seed_v1, str(v1), "1"],
        [*cli, "--db", str(v1), "migrate"],
        [*cli, "--db", str(v1), "db", "integrity"],
        [*cli, "--db", str(v1), "verify"],
        [python, "-c", seed_v1, str(v2), "2"],
        [*cli, "--db", str(v2), "migrate"],
        [*cli, "--db", str(v2), "db", "integrity"],
        [*cli, "--db", str(v2), "verify"],
        [
            python,
            "-m",
            "pytest",
            "-q",
            "-m",
            "stdio",
            "--tb=short",
            f"--basetemp={scratch / 'stdio'}",
        ],
    ]
    commands.extend(
        [
            [*cli, "provider", operation]
            for operation in ("status", "capabilities", "quota", "contract", "cache-status")
        ]
    )
    commands.extend(
        [
            [python, "-c", seed_v1, str(v3), "3"],
            [*cli, "--db", str(v3), "migrate"],
            [*cli, "--db", str(v3), "db", "integrity"],
            [*cli, "--db", str(v3), "verify"],
            [
                python,
                "-m",
                "pytest",
                "-q",
                "tests/test_nexlev_client.py",
                "tests/test_nexlev_evidence.py",
                "tests/test_nexlev_acquisition.py",
                "--tb=short",
                f"--basetemp={scratch / 'nexlev'}",
            ],
        ]
    )
    v4 = scratch / "v4.sqlite3"
    commands.extend(
        [
            [python, "-c", seed_v1, str(v4), "4"],
            [*cli, "--db", str(v4), "migrate"],
            [*cli, "--db", str(v4), "db", "integrity"],
            [*cli, "--db", str(v4), "verify"],
            [*cli, "analysis", "formulas"],
            [
                python,
                "-m",
                "pytest",
                "-q",
                "tests/test_analysis_formulas.py",
                "tests/test_analysis_integrity.py",
                "tests/test_analysis_persistence.py",
                "--tb=short",
                f"--basetemp={scratch / 'analytics'}",
            ],
        ]
    )
    v5 = scratch / "v5.sqlite3"
    commands.extend(
        [
            [python, "-c", seed_v1, str(v5), "5"],
            [*cli, "--db", str(v5), "migrate"],
            [*cli, "--db", str(v5), "db", "integrity"],
            [*cli, "--db", str(v5), "verify"],
            [
                python,
                "-m",
                "pytest",
                "-q",
                *[str(p) for p in sorted((root / "tests").glob("test_historical_*.py"))],
                "--tb=short",
                f"--basetemp={scratch / 'historical'}",
            ],
            [
                python,
                "-m",
                "pytest",
                "-q",
                "tests/test_phase2_retention.py",
                "tests/test_history.py",
                "tests/test_analysis_persistence.py",
                "--tb=short",
                f"--basetemp={scratch / 'retention'}",
            ],
        ]
    )
    results = []
    for command in commands:
        try:
            completed = subprocess.run(
                command,
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=180,
                check=False,
            )
            result = {
                "command": command,
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        except subprocess.TimeoutExpired:
            result = {"command": command, "exit_code": 124, "stdout": "", "stderr": "Timed out"}
        results.append(result)
        print(
            f"{'PASS' if result['exit_code'] == 0 else 'FAIL'}: {subprocess.list2cmdline(command)}",
            flush=True,
        )
    report = {
        "phase": 4,
        "recorded_at": datetime.now(UTC).isoformat(),
        "live_api_used": False,
        "checks": results,
        "ok": all(result["exit_code"] == 0 for result in results),
    }
    (root / "docs" / "phase-4-results.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
