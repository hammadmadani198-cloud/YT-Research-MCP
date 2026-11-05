"""Cold restore a Phase 6 bundle; capture exact checks in its external manifest."""

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def main():
    root = Path(__file__).resolve().parent.parent
    bundle = root.parent / "YouTubeNicheFinderMCP-phase6.bundle"
    manifest_path = root.parent / "YouTubeNicheFinderMCP-phase6-backup-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if hashlib.sha256(bundle.read_bytes()).hexdigest() != manifest["sha256"]:
        raise ValueError("Bundle hash mismatch")
    scratch = root / ".pytest-tmp" / ("phase6-restore-" + uuid4().hex)
    scratch.parent.mkdir(exist_ok=True)
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"YOUTUBE_API_KEY", "NEXLEV_API_KEY"} and not k.startswith("YTNMCP_")
    }
    env["PYTHONUTF8"] = "1"
    records = []

    def run(command, directory=root):
        result = subprocess.run(
            command,
            cwd=directory,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=900,
            check=False,
        )
        records.append(
            {
                "command": command,
                "cwd": str(directory),
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        manifest.update(
            cold_restore_path=str(scratch),
            cold_restore_checks=records,
            verification_state="in_progress",
        )
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(
            ("PASS: " if result.returncode == 0 else "FAIL: ") + subprocess.list2cmdline(command),
            flush=True,
        )
        if result.returncode:
            manifest["verification_state"] = "failed"
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            raise RuntimeError("Cold restore check failed")
        return result.stdout.strip()

    run(["git", "bundle", "verify", str(bundle)])
    run(["git", "clone", str(bundle), str(scratch)])
    env["PYTHONPATH"] = str(scratch / "src")
    env["YTNMCP_DB_PATH"] = str(scratch / ".pytest-tmp" / "probe.sqlite3")
    (scratch / ".pytest-tmp").mkdir(exist_ok=True)
    python = sys.executable
    final = run(["git", "rev-parse", "HEAD"], scratch)
    tag = run(["git", "rev-parse", "phase-6-verified"], scratch)
    if final != tag or final != manifest["final_sha"]:
        raise ValueError("Cold restored Git identity mismatch")
    run(["git", "fsck", "--full"], scratch)
    imports = (
        "import importlib,pkgutil,youtube_niche_mcp; from pathlib import Path; "
        "assert Path(youtube_niche_mcp.__file__).resolve().is_relative_to(Path.cwd()); "
        "mods=list(pkgutil.walk_packages(youtube_niche_mcp.__path__,"
        "youtube_niche_mcp.__name__+'.')); "
        "[importlib.import_module(m.name) for m in mods if not m.name.endswith('__main__')]; "
        "print(youtube_niche_mcp.__file__); print('Import sweep passed:',len(mods))"
    )
    run([python, "-c", imports], scratch)
    run([python, "-m", "pytest", "-q", "--tb=short", "--basetemp=.pytest-tmp/cold-tests"], scratch)
    run([python, "-m", "ruff", "check", "."], scratch)
    run([python, "-m", "ruff", "format", "--check", "."], scratch)
    run([python, "-m", "youtube_niche_mcp", "verify"], scratch)
    run([python, "scripts/verify_phase6_frozen.py"], scratch)
    for name in (
        "PROJECT_STATE.md",
        *[
            str(p.relative_to(root))
            for p in sorted((root / "research_specs").glob("*"))
            if p.is_file()
        ],
    ):
        if (scratch / name).read_bytes() != (root / name).read_bytes():
            raise ValueError("Cold restored artifact bytes mismatch: " + name)
    run(
        [
            python,
            "-m",
            "pytest",
            "-q",
            "-m",
            "stdio",
            "--tb=short",
            "--basetemp=.pytest-tmp/cold-stdio",
        ],
        scratch,
    )
    if run(["git", "status", "--porcelain"], scratch):
        raise ValueError("Cold restore is dirty")
    for item in manifest["preserved_prior_bundles"]:
        path = root.parent / item["name"]
        if (
            path.stat().st_size != item["size"]
            or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]
        ):
            raise ValueError("Earlier bundle changed: " + item["name"])
    manifest.update(
        verification_state="verified",
        verified_at=datetime.now(UTC).isoformat(),
        tag_sha=tag,
        cold_restore_ok=True,
        preserved_prior_bundles_ok=True,
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Cold restore and preserved prior bundles verified", flush=True)


if __name__ == "__main__":
    main()
