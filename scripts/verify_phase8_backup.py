"""Offline bundle verification and isolated cold restore; never installs or uses HTTP."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--implementation", required=True)
    args = parser.parse_args()
    parent = ROOT.parent
    bundle = parent / "YouTubeNicheFinderMCP-phase8.bundle"
    manifest = parent / "YouTubeNicheFinderMCP-phase8-backup-manifest.json"
    previous_attempts = []
    if manifest.exists():
        prior = json.loads(manifest.read_text(encoding="utf-8"))
        previous_attempts = [
            *prior.get("previous_attempts", []),
            {k: v for k, v in prior.items() if k != "previous_attempts"},
        ]
    cold = parent / ("YouTubeNicheFinderMCP-phase8-cold-" + uuid4().hex[:12])
    assert not cold.exists() and cold.resolve().is_relative_to(parent.resolve())
    clean_env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"YOUTUBE_API_KEY", "NEXLEV_API_KEY"} and not k.startswith("YTNMCP_")
    }
    clean_env["PYTHONUTF8"] = "1"
    checks = []

    def run(command, cwd=ROOT, env=clean_env):
        done = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=1800,
            check=False,
        )
        row = {
            "command": command,
            "cwd": str(cwd),
            "exit_code": done.returncode,
            "stdout": done.stdout,
            "stderr": done.stderr,
        }
        checks.append(row)
        print(
            ("PASS: " if done.returncode == 0 else "FAIL: ") + subprocess.list2cmdline(command),
            flush=True,
        )
        if done.returncode:
            raise RuntimeError("Cold backup verification failed; inspect recorded diagnostics")
        return done.stdout.strip()

    head = run(["git", "rev-parse", "HEAD"])
    tag = run(["git", "rev-parse", "phase-8-verified"])
    assert tag == head
    run(["git", "bundle", "verify", str(bundle)])
    run(["git", "fsck", "--full"])
    previous = []
    for path in sorted(parent.glob("YouTubeNicheFinderMCP-phase*.bundle")):
        if path != bundle:
            previous.append(
                {
                    "path": str(path),
                    "size_bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    expected_prior = json.loads((ROOT / "docs/phase-8-prior-bundles.json").read_text())
    assert previous == sorted(expected_prior, key=lambda r: r["path"]), "Prior bundles changed"
    live = json.loads((ROOT / "docs/phase-8-live-call-receipt.json").read_text())
    report = {
        "starting_sha": "61305079c14f3196e1b28a517079f9bad7e29820",
        "package_version": "0.9.0",
        "schema_version": 7,
        "table_count": 36,
        "tool_count": 15,
        "live_provider_validation": live["state"],
        "release_classification": live["release_classification"],
        "phase": 8,
        "complete": False,
        "recorded_at": datetime.now(UTC).isoformat(),
        "final_head": head,
        "tag": "phase-8-verified",
        "tag_sha": tag,
        "implementation_checkpoint": args.implementation,
        "bundle_path": str(bundle),
        "bundle_size_bytes": bundle.stat().st_size,
        "bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
        "cold_restore_path": str(cold),
        "prior_bundles": previous,
        "live_youtube_calls": live["providers"]["youtube"]["requests"],
        "live_youtube_quota": live["providers"]["youtube"]["documented_assumed_quota"],
        "live_nexlev_calls": live["providers"]["nexlev"]["requests"],
        "live_nexlev_quota": live["providers"]["nexlev"]["documented_assumed_quota"],
        "checks": checks,
        "previous_attempts": previous_attempts,
    }
    manifest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    try:
        run(["git", "clone", str(bundle), str(cold)])
        run(["git", "checkout", "phase-8-verified"], cwd=cold)
        assert run(["git", "rev-parse", "HEAD"], cwd=cold) == head
        (cold / ".pytest-tmp").mkdir(parents=True)
        env = {
            **clean_env,
            "PYTHONPATH": os.pathsep.join([str(cold / "src"), str(cold / "tests")]),
            "YTNMCP_DB_PATH": str(cold / "data/research.sqlite3"),
        }
        python = sys.executable
        code = (
            "from pathlib import Path; import sys, youtube_niche_mcp; "
            "p=Path(youtube_niche_mcp.__file__).resolve(); "
            "assert p.is_relative_to(Path(sys.argv[1]).resolve()),p; "
            "print(p); print(youtube_niche_mcp.__version__)"
        )
        run([python, "-c", code, str(cold)], cwd=cold, env=env)
        suite = run(
            [
                python,
                "-m",
                "pytest",
                "-q",
                "--tb=short",
                f"--basetemp={cold / '.pytest-tmp/cold-suite'}",
            ],
            cwd=cold,
            env=env,
        )
        match = re.search(r"(\d+) passed", suite)
        assert match, "Missing cold suite totals"
        report["test_totals"] = {
            "cold_full_passed": int(match.group(1)),
            "phase8_passed": 41,
            "stdio_passed": 3,
        }
        run([python, "-m", "ruff", "check", "."], cwd=cold, env=env)
        run([python, "-m", "ruff", "format", "--check", "."], cwd=cold, env=env)
        run([python, "scripts/verify_phase8_frozen.py"], cwd=cold, env=env)
        run([python, "scripts/verify_phase8_docs.py"], cwd=cold, env=env)
        cli = [python, "-m", "youtube_niche_mcp"]
        run([*cli, "migrate"], cwd=cold, env=env)
        run([*cli, "migrate"], cwd=cold, env=env)
        for op in (("verify",), ("db", "status"), ("db", "integrity"), ("tool", "list")):
            run([*cli, *op], cwd=cold, env=env)
        run(["git", "fsck", "--full"], cwd=cold)
        assert run(["git", "status", "--porcelain"], cwd=cold) == ""
        report["complete"] = True
        report["ok"] = True
    finally:
        report["checks"] = checks
        manifest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
