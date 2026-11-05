"""Run offline Phase 0 checks and preserve actual command output for review."""

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    scratch = (root / ".pytest-tmp" / f"acceptance-{uuid4().hex}").resolve()
    if not scratch.is_relative_to(root) or scratch.exists():
        raise ValueError("Pytest scratch must be a new directory within this repository")
    scratch.parent.mkdir(parents=True, exist_ok=True)
    python = sys.executable
    commands = [
        [python, "-m", "pip", "check"],
        [python, "-m", "pytest", "-q", "--tb=short", f"--basetemp={scratch}"],
        [python, "-m", "ruff", "check", "."],
        [python, "-m", "ruff", "format", "--check", "."],
        [
            python,
            "-c",
            (
                "import importlib, pkgutil, youtube_niche_mcp; "
                "modules = list(pkgutil.walk_packages(youtube_niche_mcp.__path__, "
                "youtube_niche_mcp.__name__ + '.')); "
                "[importlib.import_module(m.name) for m in modules "
                "if not m.name.endswith('__main__')]; "
                "print('Package imports passed')"
            ),
        ],
        [python, "-m", "youtube_niche_mcp", "--version"],
        [python, "-m", "youtube_niche_mcp", "config", "check"],
        [python, "-m", "youtube_niche_mcp", "tool", "list"],
        [python, "-m", "youtube_niche_mcp", "db", "status"],
        [python, "-m", "youtube_niche_mcp", "db", "integrity"],
        [python, "-m", "youtube_niche_mcp", "verify"],
    ]
    results = []
    for command in commands:
        try:
            completed = subprocess.run(
                command, cwd=root, capture_output=True, text=True, timeout=60, check=False
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
            f"{'PASS' if result['exit_code'] == 0 else 'FAIL'}: {subprocess.list2cmdline(command)}"
        )
    report = {
        "phase": 0,
        "recorded_at": datetime.now(UTC).isoformat(),
        "checks": results,
        "ok": all(result["exit_code"] == 0 for result in results),
    }
    (root / "docs" / "phase-0-results.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
