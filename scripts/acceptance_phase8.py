"""Capture exact offline acceptance outputs without changing Phase 0-7 reports."""

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    scratch = (root / ".pytest-tmp" / f"phase8-acceptance-{uuid4().hex}").resolve()
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
    clean = scratch / "clean.sqlite3"
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
        [*cli, "tool", "list"],
        [*cli, "db", "status"],
        [*cli, "db", "integrity"],
        [*cli, "verify"],
        [*cli, "provider", "capabilities"],
        [*cli, "api", "capability"],
        [*cli, "analysis", "formulas"],
        [*cli, "history", "status"],
        [python, "scripts/verify_phase7_frozen.py"],
        [python, "scripts/verify_phase8_frozen.py"],
        [python, "scripts/verify_phase8_docs.py"],
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
        [
            python,
            "-m",
            "pytest",
            "-q",
            "-s",
            "tests/test_release_phase8.py",
            "--tb=short",
            f"--basetemp={scratch / 'release'}",
        ],
        [*cli, "--db", str(clean), "migrate"],
        [*cli, "--db", str(clean), "migrate"],
        [*cli, "--db", str(clean), "db", "integrity"],
        [*cli, "--db", str(clean), "verify"],
    ]
    for version in range(1, 7):
        fixture = scratch / f"v{version}.sqlite3"
        commands.extend(
            [
                [python, "-c", seed_v1, str(fixture), str(version)],
                [*cli, "--db", str(fixture), "migrate"],
                [*cli, "--db", str(fixture), "migrate"],
                [*cli, "--db", str(fixture), "verify"],
            ]
        )
    results = []
    positions = None
    report_path = root / "docs/phase-8-results.json"
    if args.retry_failed:
        previous = json.loads(report_path.read_text(encoding="utf-8"))
        if not previous.get("complete"):
            raise ValueError("The original acceptance run must finish before retrying")
        results = previous["checks"]
        positions = [
            i
            for i, c in enumerate(results)
            if c["exit_code"]
            or "ruff" in c["command"]
            or any(
                "verify_phase8_frozen" in part or "test_tools_phase7.py" in part
                for part in c["command"]
            )
        ]
        commands = [results[i]["command"] for i in positions]
        for i, command in enumerate(commands):
            commands[i] = [
                f"--basetemp={scratch / ('retry-' + str(i))}"
                if part.startswith("--basetemp=")
                else part
                for part in command
            ]
    for index, command in enumerate(commands):
        try:
            completed = subprocess.run(
                command,
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=1800,
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
        if positions is None:
            results.append(result)
        else:
            position = positions[index]
            earlier = results[position]
            result["previous_attempts"] = [
                *earlier.get("previous_attempts", []),
                {k: v for k, v in earlier.items() if k != "previous_attempts"},
            ]
            results[position] = result
        (root / "docs" / "phase-8-results.json").write_text(
            json.dumps({"phase": 8, "complete": False, "checks": results}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            f"{'PASS' if result['exit_code'] == 0 else 'FAIL'}: {subprocess.list2cmdline(command)}",
            flush=True,
        )
    report = {
        "phase": 8,
        "complete": True,
        "recorded_at": datetime.now(UTC).isoformat(),
        "live_api_used": False,
        "checks": results,
        "ok": all(result["exit_code"] == 0 for result in results),
    }
    (root / "docs" / "phase-8-results.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
