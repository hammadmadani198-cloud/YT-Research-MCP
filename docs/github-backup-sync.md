# YT Research — GitHub source backup and sharing

## What is backed up

`scripts/sync-github-share.py` exports only **committed, Git-tracked files** from the current local source branch. It produces a new, clean-history repository at `D:\LocalMCPs\YT-Research-GitHub`. The mirror gets an updated YT Research README and a new commit whenever source files change.

## What is never included

The source `.git` history, `.venv`, `.env` secrets, SQLite snapshots, downloaded video/image media, tunnel configuration, personal data under `data`, and separate WatchMCP engine are excluded. A credential-pattern check aborts uploads if common real API tokens or private-key blocks are detected. Always review before making the repository public.

## Setup once

1. Sign in to GitHub CLI on this Windows computer with `gh auth login --web` (approve the login in your own browser; do not share device codes or tokens).
2. Create a *new private* GitHub repository from the local mirror: `gh repo create hammadmadani198-cloud/YT-Research-MCP --private --source D:\LocalMCPs\YT-Research-GitHub --remote origin --push`.
3. Install local auto-sync: `D:\LocalMCPs\YouTubeNicheFinderMCP\.venv\Scripts\python.exe D:\LocalMCPs\YouTubeNicheFinderMCP\scripts\sync-github-share.py --install-hook`.

## After future edits

Every committed source change triggers the local post-commit hook, which updates the sanitized mirror and pushes `main` to GitHub. It cannot sync uncommitted changes. Internet/authentication failures are written to `.git/yt-share-sync.log`; rerun `python scripts/sync-github-share.py --push` after resolving the problem. Check `git -C D:\LocalMCPs\YT-Research-GitHub status` and `git -C D:\LocalMCPs\YT-Research-GitHub log -1 --oneline` for local state.

## Sharing

Private repositories can be shared by inviting selected collaborators in GitHub Settings → Collaborators. To allow anyone to view the repository, explicitly change visibility to Public after privacy and copyright review. Public access does **not** imply an open-source license.

## Limits

The 14-tool general profile is enabled by setting `YT_RESEARCH_GENERAL=1`. Historical F1–F23 modules remain in source for rollback but disabled in active profile. Video inspection requires separately configured WatchMCP and working YouTube download access, which is currently deferred. No automated data snapshots are scheduled.
