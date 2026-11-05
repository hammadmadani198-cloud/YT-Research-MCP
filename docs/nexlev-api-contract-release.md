# NexLev release REST contract - checked 2026-10-03 UTC

Baseline: nexlev-api-contract.md, checked 2026-10-02. Official twelve API reference pages plus MCP channel/faceless/daily documentation and targeted official-domain searches were rechecked. No authenticated provider request was made. No route was added or reclassified as supported without a complete REST contract.

[Quickstart](https://docs.nexlev.io/docs/api/quickstart) (2026-08-04) still specifies https://prod.dashboard.nexlev.io. [Authentication](https://docs.nexlev.io/docs/api/authentication) (2026-07-13) uses Bearer API keys; absent/invalid headers return 401. Generic docs do not establish every endpoint's 403 cause, so plan_restricted is a conservative client classification. No remote MCP OAuth is installed.

| Implemented route(s) / official reference | Page revision | Current cost / behavior | Diff |
| --- | --- | --- | --- |
| channel_about, channel_videos - [channel content](https://docs.nexlev.io/docs/api/channel-content) | 2026-07-13 | GET about/videos; id; one each; videos sort_by/token | Still valid |
| video_details, comments, transcript, subtitle, rpm_estimate - [video content](https://docs.nexlev.io/docs/api/video-content) | 2026-07-13 | GET details/comments/transcript/subtitle/rpm; videoId; one each; comments continuation/token; subtitle URLs metadata only | Still valid; RPM remains estimate/context |
| youtube_search - [search](https://docs.nexlev.io/docs/api/youtube-search) | 2026-08-04 | GET youtube/search; query, documented filters/token; one; 20/minute/key | Still valid |
| similar_channels - [similarity](https://docs.nexlev.io/docs/api/search-similar-channel) | 2026-09-22 | POST; channelId/channelType/level; 20 for levels 1-3, 60 for 4; synchronous, 5/15-minute maxima; 408 possible | Still valid; no expensive POST retry; public 90-second bound may return unavailable |
| similar_videos - [similar videos](https://docs.nexlev.io/docs/api/similar-videos) | 2026-07-13 | POST videoId; ten | Still valid |
| similar_thumbnails - [thumbnail similarity](https://docs.nexlev.io/docs/api/similar-thumbnails) | 2026-07-13 | POST text OR image_url; ten; explicit Deep/admin operation | Still valid |
| channel_analytics, geography_revenue_estimate, short_vs_long - [analytics](https://docs.nexlev.io/docs/api/channel-analytics) | 2026-07-13 | POST analytics ten; POST geography twenty; GET channel path short-vs-long one | Still valid; geography/revenue provider context only |
| niche_overview - [niche overview](https://docs.nexlev.io/docs/api/analyze-channel-niche) | 2026-07-13 | POST channelId; twenty; seed-channel description, not semantic global niche finder | Still valid |
| channel_analysis.create/status - [async analysis](https://docs.nexlev.io/docs/api/channel-analysis) | 2026-07-10 | GET create(channel_id)/status(job_id); twenty/one; 100/500 hourly; cached handling where documented | Still valid; bounded foreground polling only |

[Quota](https://docs.nexlev.io/docs/api/rate-limits) (2026-07-13) remains billing-cycle balance: successful requests deduct endpoint units, failed 4xx/5xx are free, noted cached results are free, exhausted quota returns 429. Client ledgers distinguish documented cost and observable charge from uncertain timeout/network charge; they do not invent account allowance or remote balance.

| Former/other capability | Current public REST evidence | Release state / change |
| --- | --- | --- |
| Niche Finder semantic/filter | [MCP channel search](https://docs.nexlev.io/docs/mcp/channel-search) describes assistant tools, not a complete REST request | orchestrator_only; unchanged |
| Faceless outliers semantic/filter | MCP faceless/channel search context, no complete REST route found | orchestrator_only; unchanged |
| Small-channel viral | No complete matching REST request found in reviewed sources | orchestrator_only; unchanged |
| Latest faceless | [Faceless MCP tools](https://docs.nexlev.io/docs/mcp/faceless-channels) describe feed/classifier | orchestrator_only; unchanged |
| Suggested catalog | No matching REST request found in reviewed sources | orchestrator_only; unchanged |
| Daily historical analytics | [Daily MCP analytics](https://docs.nexlev.io/docs/mcp/daily-analytics) remains distinct orchestrated access | orchestrator_only; unchanged |
| Faceless classifier and monetization claims | MCP/provider evidence; not official eligibility proof | external ingestion/context only; unchanged |
| Catalog video-search | Search page mentions /videos/video-search but lacks full cost/parameter/response contract | contract_unknown; remains disabled |
| Channel outliers/shorts/playlists, bulk text and Shorts details | Channel/video references document additional REST operations | documented_not_enabled in this project's narrow allowlist; not newly enabled; channel outliers differs from global semantic faceless outliers |

Capability diff: 17 implemented route entries still valid; zero newly enabled, deprecated implemented routes, or observed cost changes; formerly orchestrator-only/contract-unknown features retain their prior state. Account plan access is unknown without credentials. No long-term raw-text/provider-history storage right is established by these pages; existing 15-minute raw, one-hour text and 24-hour normalized/provider-history limits remain contract_review_required and do not grant contractual permission. Provider estimates/classes do not override canonical official evidence or frozen trust/eligibility. Absence of a full public REST contract is limited to this documented review, not a claim that the product lacks a feature.
