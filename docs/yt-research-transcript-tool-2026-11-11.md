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
