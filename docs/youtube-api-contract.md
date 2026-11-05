# YouTube API contract — verified 2026-10-02

Only official Google/YouTube documentation was used. This is a local public-data
client contract, not proof of this application's approval or actual project quota.
The normal test/verify/startup paths make no YouTube calls.

| Endpoint / official reference | Fields used | Assumed cost / bucket | Paging and implementation limits | Missing/error semantics |
| --- | --- | --- | --- | --- |
| [search.list](https://developers.google.com/youtube/v3/docs/search/list) | id, snippet identifiers | 1 / search | maxResults 0–50, default 5; nextPageToken; bounded pages; channel video search can cap at 500; totalResults is approximate | Preserve duplicates and malformed IDs; search is discovery evidence, never a census |
| [channels.list](https://developers.google.com/youtube/v3/docs/channels/list) | id, snippet, statistics, contentDetails.uploads | 1 / general | comma-separated IDs; local conservative chunks of 50; no claim of an undocumented ID maximum; maxResults 0–50 for supported paging | Omitted IDs remain API_missing; forbidden/not-found are structured outcomes |
| [videos.list](https://developers.google.com/youtube/v3/docs/videos/list) | id, snippet, statistics, contentDetails, status | 1 / general | local chunks of 50; id requests omit maxResults/pageToken; documented maxResults 1–50 does not apply to id filtering | Missing IDs cannot distinguish deleted/private; no zero replacement |
| [playlistItems.list](https://developers.google.com/youtube/v3/docs/playlistItems/list) | snippet.resourceId, contentDetails.videoId/videoPublishedAt | 1 / general | maxResults 0–50; nextPageToken; uploads catalog route preserves all occurrences | Inaccessible playlist, malformed items and partial traversal remain visible |
| [playlists.list](https://developers.google.com/youtube/v3/docs/playlists/list) | id, snippet, contentDetails | 1 / general | maxResults 0–50; nextPageToken; public channelId route | Owner-only mine/content-owner filters unsupported |
| [commentThreads.list](https://developers.google.com/youtube/v3/docs/commentThreads/list) | id, snippet, replies | 1 / general | maxResults 1–100; nextPageToken with videoId; embedded replies may be incomplete | commentsDisabled is unavailable, not zero comments; fetch replies separately |
| [comments.list](https://developers.google.com/youtube/v3/docs/comments/list) | id, snippet | 1 / general | parentId replies; maxResults 1–100, nextPageToken | Missing/forbidden replies remain incomplete; no owner moderation access |
| [videos.batchGetStats](https://developers.google.com/youtube/v3/docs/videos/batchGetStats) | id, statistics, snippet.publishTime, contentDetails.duration | 1 / video_stats | GET videos:batchGetStats; no documented maximum ID count or pagination; local configurable conservative chunk, opt-in | summary.failedVideoIds tracked individually; summary-only failures without IDs cannot be assigned invented identities |

Quota is centralized and injectable in `api/contracts.py`: every actual request,
including retries, invalid responses and additional pages, is accounted. Default
documented daily buckets are search 100, general 10,000, video_stats 10,000;
these are assumptions, not remaining-balance claims. See the
[quota calculator](https://developers.google.com/youtube/v3/determine_quota_cost)
(updated 2026-09-15) and
[June 1/3 revision entries](https://developers.google.com/youtube/v3/revision_history).
Resets are midnight Pacific; the ledger stores UTC request times and supports bucket
aggregation, not remote balance estimation. Batch reference updated 2026-09-14.

[Channel properties](https://developers.google.com/youtube/v3/docs/channels):
subscriberCount is rounded down to three significant figures; hiddenSubscriberCount
means a missing public count, even if an inconsistent payload also contains a number.
snippet.publishedAt is account creation, not niche entry. Uploads playlist IDs support
catalog enumeration; they do not prove complete historical coverage.

[Video properties](https://developers.google.com/youtube/v3/docs/videos):
snippet.publishedAt normally records publication after a private upload becomes public;
owner-private, unlisted and members-only cases may instead report upload time. Store
the API timestamp and its semantic qualification, not an unconditional public claim.
Batch snippet.publishTime is explicitly upload time. In
[playlist item properties](https://developers.google.com/youtube/v3/docs/playlistItems),
snippet.publishedAt is playlist addition; contentDetails.videoPublishedAt is publication.
Provider/index time, MCP first-seen, request, observation, availability and decision
times remain separate.

[August revision entry](https://developers.google.com/youtube/v3/revision_history)
and channel/video properties describe playback-start public views effective
2026-08-24 across formats, announced 2026-08-27. Cumulative totals can mix prior
regimes. Captures carry a metric-definition label; no conversion to engaged attention
or earnings is implemented. Search region is viewability and relevanceLanguage is
a hint, neither establishes audience demographics or language eligibility.

[Captions download](https://developers.google.com/youtube/v3/docs/captions/download)
requires OAuth and permission to edit the video; the public API key does not grant
caption access. Download costs 200 units. Captions are not implemented.

[Developer policies](https://developers.google.com/youtube/terms/developer-policies)
require limited non-authorized data to be refreshed/deleted within 30 days, and do
not generally permit derived metrics. Local observations expire at 30 days; refresh
adds a new capture rather than renewing an old historical value. An explicit retention
purge removes expired rows (the documented exception to append-only collection).
Queries exclude expired evidence. Backups of research data would require the same
retention handling; the Git bundles contain code/specifications only.

[Additional derived/storage policy](https://developers.google.com/youtube/terms/derived-metrics-policy)
allows accepted analytics clients statistical/derived retention up to 36 calendar
months; titles, creator names, descriptions and comment text still follow the 30-day
rule. Acceptance of this application is unknown. No extended-retention setting or
derived calculation is enabled in Phase 1. Provider access is not a policy exception.
Owner metrics and private analytics remain explicitly unavailable/authorization-gated.

Network errors expose endpoint, whitelisted reason, status and outcome only. API keys
are sent in the Google API-key header; redirects are disabled. No response error
message, URL, key, authorization header or credential is logged or persisted.
The header mapping is documented in Google's
[system parameters](https://docs.cloud.google.com/apis/docs/system-parameters)
(updated 2026-09-30; checked 2026-10-02).
