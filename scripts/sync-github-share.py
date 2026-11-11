"""Securely synchronize committed YT Research source via a disposable GitHub clone."""

from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent
REMOTE = os.environ.get(
    "YT_RESEARCH_GITHUB_REMOTE", "https://github.com/hammadmadani198-cloud/YT-Research-MCP.git"
).strip()
BLOCKED = (
    re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    re.compile(r"(?:ghp_|gho_|ghu_|ghs_|ghr_|github_pat_)[a-zA-Z0-9_]{20,}"),
    re.compile(r"sk-or-v1-[0-9a-fA-F]{20,}"),
    re.compile(r"-----BEGIN\s+(?:RSA\s+|OPENSSH\s+|EC\s+)?PRIVATE\s+KEY-----"),
)
TEXT_EXT = {
    ".py",
    ".md",
    ".txt",
    ".toml",
    ".json",
    ".yaml",
    ".yml",
    ".ps1",
    ".sh",
    ".cfg",
    ".ini",
    ".example",
}
BLOCKED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "data",
    "tunnel",
    "jobs",
    "artifacts",
    "backups",
    ".github-token",
}
SHARE_README = """# YT Research — YouTube Research MCP

A Python MCP server for evidence-grounded public YouTube research.
**15 active research tools**, with YouTube metadata, outliers and caption retrieval.

## Capabilities
- Search public videos and retrieve public video/channel metadata.
- Paginate up to 300 uploads; identify provisional 2x/5x/10x
  current-view age-cohort outliers and recent 30/90-day publishing windows.
- Plan four video-inspection stages and review evidence-labelled Watch jobs.
- Save public view snapshots for future actual historical view checkpoints.
- Export evidence as local JSON/CSV. Local data is not shared.
- Retrieve public YouTube captions with timestamps using youtube_get_transcript:
  youtube-transcript-api first, yt-dlp subtitle-only fallback.

## Install (Python 3.12+)
Create a virtualenv and install dependencies:
  py -3.12 -m venv .venv
  .venv/Scripts/python.exe -m pip install -e ".[dev,transcripts]"
Set YT_RESEARCH_GENERAL=1 and your own YOUTUBE_API_KEY in the process
environment. Launch the server using python -m youtube_niche_mcp.server.
On Windows, scripts/run-yt-research.ps1 also sets the general-research profile.

## Important limitations
- Ratios use current lifetime views, NOT actual historical Day-7/30 views.
- Historical milestones exist only if actual past snapshots were saved.
- WatchMCP is optional and separate; its source, media and model credentials
  are NOT bundled with this repository. Video reliability needs live validation.
- Old niche/F1-F23 implementation remains for rollback but is disabled with
  YT_RESEARCH_GENERAL=1. NexLev is disabled in the active profile.
- No private analytics, local databases, model keys or user media are included.
- Transcripts are returned only on demand; they are not stored in this repo.
  Third-party captions can be unavailable, blocked, or subject to reuse rules.
- See docs/yt-research-outlier-inspection-v1-2026-11-05.md for methodology.

## Sharing and future updates
GitHub repository starts private. Share by inviting collaborators.
For public sharing, first review privacy, copyrights and dependencies.
To sync future committed changes, authorize GitHub CLI and install
the source post-commit hook using:
  python scripts/sync-github-share.py --install-hook
Each push uses a temporary GitHub checkout on D: and removes it after
pushing. No permanent duplicate checkout is required.

No open-source license has been selected. Public visibility by itself
does not grant third-party reuse rights.
"""


def run(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    done = subprocess.run(
        [*args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if check and done.returncode:
        raise RuntimeError(f"{args[0]} command failed: {done.stderr[-350:]}")
    return done


def safe_file(name: str) -> bool:
    path = Path(name)
    parts = set(part.lower() for part in path.parts)
    if parts.intersection(BLOCKED_PARTS):
        return False
    if path.name.lower() in {".env", ".env.local", ".npmrc", "id_rsa"}:
        return False
    return path.suffix.lower() not in {
        ".sqlite",
        ".sqlite3",
        ".db",
        ".pem",
        ".p12",
        ".pfx",
        ".log",
        ".bundle",
        ".bak",
        ".key",
    }


def scan(name: str, content: bytes) -> None:
    if Path(name).suffix.lower() not in TEXT_EXT and not name.startswith(".env"):
        return
    text = content.decode("utf-8", "replace")
    for rule in BLOCKED:
        if rule.search(text):
            raise RuntimeError(f"Possible credential detected; export stopped: {name}")


def sync(*, push: bool = False) -> bool:
    """Export only safe committed files; push using an auto-deleted temporary clone."""
    archive = subprocess.check_output(["git", "archive", "--format=zip", "HEAD"], cwd=SOURCE)
    extracted: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        for item in bundle.infolist():
            if item.is_dir() or not safe_file(item.filename):
                continue
            if item.filename.startswith("/") or ".." in Path(item.filename).parts:
                raise RuntimeError("Unsafe path in source git archive.")
            blob = bundle.read(item)
            scan(item.filename, blob)
            extracted[item.filename] = blob
    extracted["README.md"] = SHARE_README.encode("utf-8")
    extracted[".yt-research-share-marker"] = b"YT Research share mirror v1\n"
    source_ignore = extracted.get(".gitignore", b"")
    extracted[".gitignore"] = source_ignore + (
        b"\n# GitHub copy never includes local credentials or runtime state\n"
        b"tunnel/\njobs/\nartifacts/\n*.bak\n*.pem\n*.p12\n*.pfx\n"
    )
    print(f"SAFE_FILES={len(extracted)}")
    if not push:
        print("CREDENTIAL_SCAN=PASS. Use --push to sync.")
        return False
    if not re.fullmatch(r"https://github\.com/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+(?:\.git)?", REMOTE):
        raise RuntimeError("GitHub remote must be an HTTPS github.com repository.")
    tmp_parent = SOURCE / "data" / "github-sync-temp"
    tmp_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="yt-share-", dir=tmp_parent) as folder:
        checkout = Path(folder) / "repository"
        run(
            "git",
            "clone",
            "--quiet",
            "--single-branch",
            "--branch",
            "main",
            REMOTE,
            str(checkout),
            cwd=SOURCE,
        )
        if not (checkout / ".yt-research-share-marker").is_file():
            raise RuntimeError("Remote is not a verified YT Research share repository.")
        run("git", "config", "user.name", "YT Research Backup", cwd=checkout)
        run(
            "git",
            "config",
            "user.email",
            "350302801+hammadmadani198-cloud@users.noreply.github.com",
            cwd=checkout,
        )
        tracked = run("git", "ls-files", "-z", cwd=checkout).stdout
        for relative in tracked.split("\x00"):
            if relative and relative not in extracted:
                candidate = checkout / relative
                if candidate.is_file():
                    candidate.unlink()
        for relative, blob in extracted.items():
            dest = checkout / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.is_file() or dest.read_bytes() != blob:
                dest.write_bytes(blob)
        run("git", "add", "--all", cwd=checkout)
        changed = run("git", "diff", "--cached", "--quiet", cwd=checkout, check=False)
        if changed.returncode not in (0, 1):
            raise RuntimeError("Unable to check staged GitHub changes.")
        if changed.returncode == 1:
            sha = run("git", "rev-parse", "--short", "HEAD", cwd=SOURCE).stdout.strip()
            run("git", "commit", "-m", f"Sync tested YT Research source {sha}", cwd=checkout)
            print(f"Updated share repository from source {sha}.")
        local_sha = run("git", "rev-parse", "HEAD", cwd=checkout).stdout.strip()
        run("git", "push", "origin", "main", cwd=checkout)
        remote_line = run("git", "ls-remote", "origin", "refs/heads/main", cwd=checkout)
        remote_sha = remote_line.stdout.split()[0] if remote_line.stdout.strip() else ""
        if local_sha != remote_sha:
            raise RuntimeError("GitHub push verification failed: remote commit differs.")
        print("GITHUB_SYNC=SUCCESS (temporary clone cleaned automatically)")
        return changed.returncode == 1


def install_hook() -> None:
    hook = SOURCE / ".git" / "hooks" / "post-commit"
    if hook.exists():
        current = hook.read_text(encoding="utf-8", errors="replace")
        if "YT Research GitHub share sync" in current:
            print("Post-commit sync hook is already installed.")
            return
        raise RuntimeError("Existing post-commit hook found. Do not overwrite it; review first.")
    body = (
        "#!/bin/sh\n"
        "# YT Research GitHub share sync — source commits trigger safe mirror push\n"
        'root="$(git rev-parse --show-toplevel)"\n'
        'py="$root/.venv/Scripts/python.exe"\n'
        'if [ ! -f "$py" ]; then py=python; fi\n'
        '"$py" "$root/scripts/sync-github-share.py" --push '
        '>> "$root/.git/yt-share-sync.log" 2>&1 || '
        'echo "YT Research GitHub sync failed; inspect .git/yt-share-sync.log" >&2\n'
        "exit 0\n"
    )
    hook.write_text(body, encoding="utf-8", newline="\n")
    hook.chmod(0o755)
    print("AUTO_SYNC_HOOK=INSTALLED (runs after future source Git commits)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--install-hook", action="store_true")
    args = ap.parse_args()
    sync(push=args.push)
    if args.install_hook:
        install_hook()


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        print(f"SYNC_ERROR={exc}", file=sys.stderr)
        raise SystemExit(1) from None
