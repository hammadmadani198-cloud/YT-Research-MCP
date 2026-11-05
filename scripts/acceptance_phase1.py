"""Capture exact offline acceptance outputs without changing Phase 0 reports."""

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    scratch = (root / ".pytest-tmp" / f"phase1-acceptance-{uuid4().hex}").resolve()
    if not scratch.is_relative_to(root) or scratch.exists():
        raise ValueError("Acceptance scratch must be a new directory inside the repository")
    scratch.mkdir(parents=True)
    python = sys.executable
    env = {
        key: value
        for key, value in os.environ.items()
        if key != "YOUTUBE_API_KEY" and not key.startswith("YTNMCP_")
    }
    env["YTNMCP_DB_PATH"] = str(root / "data" / "research.sqlite3")
    cli = [python, "-m", "youtube_niche_mcp"]
    clean, v1 = scratch / "clean.sqlite3", scratch / "v1.sqlite3"
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
            "    installed=migrate(connection,MIGRATIONS[:1])",
            "print('v1 fixture installed: '+str(installed))",
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
        [*cli, "tool", "list"],
        [*cli, "db", "status"],
        [*cli, "db", "integrity"],
        [*cli, "verify"],
        [*cli, "--db", str(clean), "migrate"],
        [*cli, "--db", str(clean), "migrate"],
        [*cli, "--db", str(clean), "db", "integrity"],
        [*cli, "--db", str(clean), "verify"],
        [python, "-c", seed_v1, str(v1)],
        [*cli, "--db", str(v1), "migrate"],
        [*cli, "--db", str(v1), "db", "integrity"],
        [*cli, "--db", str(v1), "verify"],
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
    results = []
    for command in commands:
        try:
            completed = subprocess.run(
                command, cwd=root, env=env, capture_output=True, text=True, timeout=60, check=False
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
        "phase": 1,
        "recorded_at": datetime.now(UTC).isoformat(),
        "live_api_used": False,
        "checks": results,
        "ok": all(result["exit_code"] == 0 for result in results),
    }
    (root / "docs" / "phase-1-results.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
