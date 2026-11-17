# YT Research: youtube_get_transcript (November 2026)

Status: new independent caption tool. Watch Videos Future Fix stays HOLD.

## Setup
In the active Windows project virtual environment:
```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[transcripts]"
```
The MCP must run with `YT_RESEARCH_GENERAL=1`. Restart its backend and refresh
the ChatGPT MCP tools list after deploying code changes.

## Request
All public YT Research tools take one `request` object:
```json
{"name":"youtube_get_transcript","arguments":{"request":{"video_id":"Ks-_Mh1QhMc","languages":["en"],"offset":0,"limit":150,"output_format":"json"}}}
```
`video_id` accepts an 11-character YouTube ID or a valid HTTPS YouTube
watch, shorts, live, or youtu.be URL. `languages` defaults to `["en"]`.
`output_format` is `json`, `text`, or `srt`. JSON uses `items`;
text/SRT uses `metadata.content`. The result reports `source`, `language`,
`caption_type`, `total_segments`, `offset`, and `next_offset`.
Use the returned `next_offset` to paginate long videos.

## Providers and boundaries
1. `youtube-transcript-api` extracts public captions if accessible.
2. On failure, local `yt-dlp` retrieves subtitle files only. Audio/video
   media are never downloaded by this tool.
3. If both providers fail or captions are missing, output is `unavailable`.
   No transcript, narration, translation, or timecodes are invented.
4. `caption_type=unknown` on yt-dlp fallback means the metadata did not
   establish whether a subtitle track was manual or auto-generated.
5. Output is on-demand and not persisted in project source or GitHub.
   Respect third-party caption permissions and YouTube access rules.

## Verification
- Offline/mock tests cover ID/URL validation, VTT parsing, pagination,
  format output, provider fallback, missing-captions behavior.
- Live reference video `Ks-_Mh1QhMc`: transcript API 428 cues;
  independent yt-dlp fallback 428 cues at time of acceptance.
- These checks do not guarantee every video has public captions or that
  external providers will remain available.

## 2026-11-12 provider diagnostics
- The metadata.provider_diagnostics array shows sanitized per-provider reason
  codes: rate_limited, access_denied, ip_blocked, request_blocked,
  authentication_required, language_unavailable, captions_disabled,
  video_unavailable, captions_unavailable, timeout, or provider_error.
- Successful primary responses return an empty diagnostics array. If yt-dlp
  succeeds, the primary failure code remains. If both fail, the overall
  state is unavailable, with one reason for each provider.
- Rate limits should be respected; do not hammer endpoints or bypass
  YouTube's protections.
- November 12 live verification: all seven previously failing videos worked
  through connected MCP. On Original OT08, the primary caption API worked,
  but independent yt-dlp attempt returned HTTP 429 Too Many Requests.
  Historical failures were not logged with reason codes; their exact cause
  cannot be reconstructed retroactively.


## 2026-11-17: optional third Go InnerTube fallback
1. Existing route order remains: youtube-transcript-api, then yt-dlp, then Go.
2. Configure `YT_RESEARCH_GO_TRANSCRIPT_BIN` as an absolute local executable
   path. This Windows installation uses
   `D:\LocalMCPs\YouTubeNicheFinderMCP\data\vendor-go-transcript\yt-transcript.exe`.
   The local MCP launcher sets the variable automatically.
3. Upstream reference: https://github.com/edouard-claude/yt-transcript ,
   revision `69796edb8ecb14603105e287efde68665304a6ae`.
   Source and binary were locally copied after user-reported developer
   permission; local `data/` is git-ignored and is not shared on GitHub.
4. Go only executes if both earlier providers fail and the local executable is
   configured. Results use `source=go_innertube`; previous failure codes remain
   in `metadata.provider_diagnostics`; a successful result includes
   `metadata.go_fallback_configured`. Fallback uses the first requested
   language and rejects an unexpected language or video ID.
5. This method fetches existing captions, not speech-to-text or audio media.
   Sustained access, provider-side restrictions, and complete uptime are not
   guaranteed. Do not hammer endpoints after HTTP 429.
6. Integration acceptance: targeted tests and forced-fallback live checks
   with two Romanov videos confirmed 1,137 and 835 caption cues respectively.
