# YT Research — GitHub backup, installer archive and auto-sync

## Active locations (5 November 2026)

- **Running MCP code**: `D:\LocalMCPs\YouTubeNicheFinderMCP` (do not move; active Windows tunnel depends on this path).
- **Setup/shareable source ZIP**: `D:\MCPs Setups\YT-Research-MCP-Share-2026-11-05.zip`.
- **Online backup**: https://github.com/hammadmadani198-cloud/YT-Research-MCP (PRIVATE, branch `main`).
- **Sync script**: `scripts/sync-github-share.py` in the running MCP source.
- **Auto-sync hook**: `.git/hooks/post-commit` in the running MCP source.

## No duplicate GitHub working folder

The former `D:\LocalMCPs\YT-Research-GitHub` working copy is not needed.
The sync script connects directly to the online private repository via GitHub CLI/Git authentication.
It creates a temporary checkout under `data/github-sync-temp`, updates sanitized source, commits, pushes, verifies the remote commit, then removes the temporary checkout.
Only **committed** source changes are synchronized. Source `data`, `.env`, tunnel credentials, local video media, Python virtualenv, and full source Git history are never copied.

## Future edits

After editing source, run `git add ...` and `git commit -m "description"` in the actual MCP directory.
The installed post-commit hook calls `python scripts/sync-github-share.py --push` automatically.
If GitHub is offline or authentication expires, the local commit remains valid; inspect `.git/yt-share-sync.log` and rerun `python scripts/sync-github-share.py --push` when available.
To check remote status: `git ls-remote https://github.com/hammadmadani198-cloud/YT-Research-MCP.git refs/heads/main`.

## Sharing and scope

The online GitHub repository stays private until the owner explicitly changes visibility. Invite specific collaborators via GitHub's repository settings. No open-source license was selected.
The setup ZIP is a shareable source archive, **not** a standalone one-click installer; the receiving computer still needs Python dependencies, MCP host config, and its own authorized API keys.
Separate WatchMCP code and live media inspection credentials are not included; Watch network reliability is on future-fix HOLD.
