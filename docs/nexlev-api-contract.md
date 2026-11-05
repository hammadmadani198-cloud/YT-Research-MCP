# NexLev REST contract review — 2026-10-02

Reviewed the current official API index and all twelve linked API pages before
writing the client. This is a documentation review, without authenticated requests.
The five requested research_specs/nexlev/NEXLEV_* audit files are absent; the locked
Phase 2.5 brief and the seven unchanged original research files supply requirements.

Base https://prod.dashboard.nexlev.io, Authorization: Bearer NEXLEV_API_KEY.
[Quickstart](https://docs.nexlev.io/docs/api/quickstart),
[authentication](https://docs.nexlev.io/docs/api/authentication).
Keys remain process secrets; no remote MCP OAuth client or ChatGPT credentials.

The implemented allowlist is deliberately smaller than the complete API:

| Route suffix | Method and public path | Required input | Documented quota |
| --- | --- | --- | ---: |
| channel_about | GET /api/external/channels/about | id | 1 |
| channel_videos | GET /api/external/channels/videos | id | 1 |
| video_details | GET /api/external/videos/details | videoId | 1 |
| transcript | GET /api/external/videos/transcript | videoId | 1 |
| subtitle | GET /api/external/videos/subtitle | videoId | 1 |
| comments | GET /api/external/videos/comments | videoId | 1 |
| youtube_search | GET /api/external/youtube/search | query | 1 |
| similar_channels | POST /api/external/similar-channels/search | channelId | 20; level 4: 60 |
| similar_videos | POST /api/external/similar-videos/videos | videoId | 10 |
| similar_thumbnails | POST /api/external/similar-thumbnails/search | text OR image_url | 10 |
| channel_analytics | POST /api/external/analytics/channel-analytics | channelId | 10 |
| short_vs_long | GET /api/external/analytics/channel-analytics/:channelId/short-vs-long-views | channelId | 1 |
| geography_revenue_estimate | POST /api/external/analytics/channel-analytics/geography-revenue | channelId | 20 |
| rpm_estimate | GET /api/external/videos/rpm | videoId | 1 |
| niche_overview | POST /api/external/niche-overview/analyze | channelId | 20 |
| channel_analysis.create | GET /api/external/channels/analysis/job/create | channel_id | 20 |
| channel_analysis.status | GET /api/external/channels/analysis/job/status | job_id | 1 |

Sources: [channel content](https://docs.nexlev.io/docs/api/channel-content),
[video content](https://docs.nexlev.io/docs/api/video-content),
[YouTube search](https://docs.nexlev.io/docs/api/youtube-search),
[similar channels](https://docs.nexlev.io/docs/api/search-similar-channel),
[similar videos](https://docs.nexlev.io/docs/api/similar-videos),
[similar thumbnails](https://docs.nexlev.io/docs/api/similar-thumbnails),
[channel analytics](https://docs.nexlev.io/docs/api/channel-analytics),
[niche overview](https://docs.nexlev.io/docs/api/analyze-channel-niche),
[async analysis](https://docs.nexlev.io/docs/api/channel-analysis).

Catalogs/comments/search paginate with continuation and request token. Catalog uses
sort_by; search uses sortBy, uploadDate, duration, features, geo, lang and type.
No undocumented transcript track-selection parameter is sent. Selected language
and languageMenu are preserved, with generated/translated/original unknown when
the response does not establish them. Subtitle URLs are metadata, never fetched.

Similar channels is currently SYNCHRONOUS (levels 1–3 up to five minutes; level 4
up to fifteen), not an invented async job. Its client timeout is separately
configurable, defaults to 300 seconds, and expensive POST calls are not retried.
Similar thumbnails requires explicit Deep mode. Channel analysis is documented
async: job create/status, bounded foreground polling and persisted job events.

[Quota](https://docs.nexlev.io/docs/api/rate-limits): successful requests consume
endpoint units; failed 4xx/5xx are free; cached results are free where documented
(channel analysis cached flag). Plan balance resets on billing cycle, not an
invented universal daily budget. Search has 20 requests/minute; analysis create
100/hour and status 500/hour. Account allowance is unknown until independently
observed. 401 means invalid/missing auth; 429 quota/rate limit. 403 is handled
conservatively as plan_restricted without exposing server text; an endpoint-specific
403 cause is not established by the reviewed generic docs. 408/5xx/transport
failure means temporary unavailability; retries are bounded for safe GETs only.

No complete supported REST request contract for semantic Niche Finder, semantic
faceless outliers, small-channel viral, suggested catalog or latest faceless was
found in this API reference or targeted official-domain searches. These remain
orchestrator_only, with rest_state=not_documented_for_rest. A mention of
/videos/video-search in the search page does not specify the catalog parameters,
cost and response contract, so it is not enabled. Daily history, faceless classifier
and monetization claims also use external ingestion. This absence finding is
limited to reviewed public documentation; it does not assert the product lacks
these features. [MCP channel search](https://docs.nexlev.io/docs/mcp/channel-search)
and [daily analytics](https://docs.nexlev.io/docs/mcp/daily-analytics) describe
orchestrated access with plan-specific daily allowances, separate from REST quota.

The API pages do not establish long-term raw text or historical storage rights.
Retention is contract_review_required: raw 15 minutes, text 1 hour, normalized
observations/history 24 hours, with no automatically granted extended permission.
These are conservative local expiry limits, not assertions of contractual rights.
Private owner analytics, CMS calls, promotions, Swipefile and generation remain
deferred/excluded. No private endpoint reverse engineering is permitted.
