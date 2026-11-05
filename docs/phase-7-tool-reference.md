# Phase 7 tool reference

Package 0.8.0; schema v7; exactly 15 tools. Every call uses `{ "request": { ... } }`. Examples are illustrative, synthetic identifiers; use actual returned IDs. An empty installation returns insufficient evidence, never synthetic research. Full JSON schemas were defined before registration in [the contract](phase-7-tool-contract.md); [machine-readable schemas](phase-7-schemas.json) are authoritative for fields and constraints.

## Common response and limits

All tools return `state`, `summary`, `research_id`, `reused_run`, `boundary`, typed `metrics`, `evidence`, `confidence`, `supports`, `concerns`, `unknowns`, `warnings`, `provenance`, `quota`, `capabilities`, `data`, `next_cursor`, and `next_available_actions`. Missing dimensions are listed, values remain null, and pending observations are counted separately. A focused tool retains the niche recommendation in `data.recommendation_state`; its own historical availability may differ.

F18 exposes its ordinal level, component assessments, specification agreement, declared assessment scope, critical missing evidence, history maturity and sensitivity flags. It is not success probability. F17 is absent unless explicitly requested; its shared-service index, weights, endpoints and configuration appear as `sorting_only_F17`. Comparison order can follow an available explicit index, while each recommendation and confidence stays unchanged.

Page inputs use `limit` 1–20 (default 10) and an opaque context-bound cursor. Cursors bind the subject and current retained dataset; expired or changed data invalidates a cursor. Comparison accepts 2–10 unique IDs. Nested projections allow at most 20 examples per list, 40 fields per map, 360 characters per string and seven levels; omissions are labeled. Responses are capped at 120,000 UTF-8 bytes. Full overview cards provide summaries; focused tools provide bounded details. Raw transcript/comment text, reviewer rationale, SQL, filesystem paths, private diagnostics and credentials are withheld.

## Storage, providers and errors

Stored evidence is the default; read tools open existing storage read-only. No call initializes or migrates a database. New research uses the frozen eligibility, cohort, core, historical, qualitative and decision services; the same inputs produce the same immutable run ID. Reuse is preferred. New frames require an explicit advanced measurement profile, compatible frame definitions and a caller-declared decision rubric. Evidence acquisition does not automatically adjudicate taxonomy, speech, facelessness or permissions.

Research, discovery and single-competitor analysis can request `acquisition.refresh=true`, an explicit `request_id`, and bounded channel/video IDs, search or similar-channel expansion. A configured key and an existing valid source-scoped administrative retention permission are both required for YouTube collection. `provider_policy=prefer_nexlev` plus `similar_channel` explicitly enables the documented similar-channels REST route when its key/permission exists. Unsupported semantic/outlier discovery REST is never substituted; retained external provider evidence can still be read. NexLev failures degrade to stored official evidence.

YouTube quota reports request class, recorded documented assumptions, bucket and contract version; actual remote charged units are null. NexLev reports documented and known charged cost, free-cache indicators and bucket; unknown charges remain null. Failed attempts retain quota entries. Timeout and partial acquisition preserve collected records and report limitations. Read-only tools report zero requests. Search is bounded to 2/6/20 pages; channel/video ceilings are 25/250, 50/800, 100/3000. Approximate lower targets are 15/100, 30/300, 60/1000. Review ceilings are 25/100/500, sensitivity ceilings 8/24/48, similarity depths 1/1/2. These are exploratory budgets, not statistical guarantees. No transcript/comment collection or new automated qualitative review is added; existing permitted reviews are sampled within the mode budget.

Fixed structured failure states include invalid_input, insufficient_evidence, provider_not_configured, provider_quota_limited, permission_required, history_unavailable, policy_refresh_required, incompatible_runs, source_conflict, internal_error, schema_upgrade_required, not_found, revision_conflict and budget_exceeded. Provider failures during explicit acquisition can instead be warnings on a usable stored result. Exceptions never disclose their text.

Watches use the sole new table `research_watches`, schema v7. They are mutable local intent, separate from immutable research evidence. Create is identity-safe replay; update/disable require expected_revision; targets are immutable and require a new watch ID to change. Owner context is a local namespace, not authentication. Expiry defaults to 365 days; expired watches are unavailable. `last_checked_at=null`, `scheduler=absent`, `execution=intent_only`. No scheduled collection, next execution, or monitoring claim.

## `youtube_niche_research`

Research a niche using retained evidence and the frozen eligibility, analytics, qualitative and decision services. Reuse a research ID or resolve a stored boundary/query; explicit advanced profiles create immutable runs. Quick/standard/deep are bounded research budgets. Stored-only by default; refresh is explicit and permission-gated. Returns multi-axis state and F18, never a success forecast.

Returns frozen frame coverage, eligible/entrant counts, F1–F16/F19–F23 summaries, ordinary floor, qualitative axes and F18-backed synthesis. English is the frozen supported language profile. History requirements cannot reconstruct prior counts. Creator constraints and pilot downside remain separate from generic niche evidence.

Required request fields: conditional subject/profile (see schema). Optional fields: limit, cursor, query, boundary_id, research_id, mode, target_spoken_language, geographic_context, history_preference, creator_profile, sorting, advanced, acquisition.

Output: common envelope above; `metrics`, multi-axis state, frame coverage, reviews, history and provenance.

Provider/network/quota: stored by default; explicitly gated refresh may consume the documented quota.

Persistence: immutable shared-service runs and explicit acquisition manifests.

Errors: fixed common vocabulary; missing evidence remains structured, never zero. Retention: transitive source expiry/permission gates remain binding. No raw text or secret access.

Example call:
```json
{
  "name": "youtube_niche_research",
  "arguments": {
    "request": {
      "boundary_id": "technical-history-v1",
      "mode": "standard"
    }
  }
}
```

Result shape (illustrative, not a measured result):
```json
{
  "state": "available",
  "summary": "Scoped retained evidence or stored watch intent",
  "research_id": "saved-research-a",
  "evidence": [],
  "confidence": {
    "level": "unknown",
    "F18": null
  },
  "data": {
    "missingness": "explicit"
  },
  "next_cursor": null
}
```

## `youtube_niche_discover`

Find stored taxonomy candidates and their official/provider discovery routes, weak cases and coverage. Candidate generation does not imply opportunity or rank by viral scores. Explicit refresh can collect bounded official search or documented NexLev similar-channel evidence.

Returns taxonomy nodes/levels, boundary IDs, deduplicated channel/video counts, declared weak routes, observed entrant-frame evidence and route coverage. It never ranks candidates by provider score. Zero search results do not establish niche absence.

Required request fields: query. Optional fields: limit, cursor, taxonomy_version, mode, acquisition.

Output: common envelope above; paginated `evidence` rows and `data` descriptors.

Provider/network/quota: stored by default; explicitly gated refresh may consume the documented quota.

Persistence: read-only projection (explicit refresh may append captures on discover/analyze).

Errors: fixed common vocabulary; missing evidence remains structured, never zero. Retention: transitive source expiry/permission gates remain binding. No raw text or secret access.

Example call:
```json
{
  "name": "youtube_niche_discover",
  "arguments": {
    "request": {
      "query": "technical history",
      "mode": "quick"
    }
  }
}
```

Result shape (illustrative, not a measured result):
```json
{
  "state": "available",
  "summary": "Scoped retained evidence or stored watch intent",
  "research_id": "saved-research-a",
  "evidence": [],
  "confidence": {
    "level": "unknown",
    "F18": null
  },
  "data": {
    "missingness": "explicit"
  },
  "next_cursor": null
}
```

## `youtube_niche_compare`

Compare 2–10 researched niches across performance, floor, repeatability, entrants, breadth, concentration, history, production, risk and confidence. Reject incompatible mode/age/goal/frame profiles. No default winner; explicit F17 is separately labeled sorting-only.

Requires compatible modes, outcome ages, goals, tolerances, measurement conventions, classification rules, rubric and frame-window lengths. Boundaries, confidence, maturity and creator fit appear per row. No default winner.

Required request fields: research_ids. Optional fields: sorting.

Output: common envelope above; paginated `evidence` rows and `data` descriptors.

Provider/network/quota: stored-only, no provider key required, zero HTTP/quota.

Persistence: read-only projection (explicit refresh may append captures on discover/analyze).

Errors: fixed common vocabulary; missing evidence remains structured, never zero. Retention: transitive source expiry/permission gates remain binding. No raw text or secret access.

Example call:
```json
{
  "name": "youtube_niche_compare",
  "arguments": {
    "request": {
      "research_ids": [
        "saved-research-a",
        "saved-research-b"
      ]
    }
  }
}
```

Result shape (illustrative, not a measured result):
```json
{
  "state": "available",
  "summary": "Scoped retained evidence or stored watch intent",
  "research_id": "saved-research-a",
  "evidence": [],
  "confidence": {
    "level": "unknown",
    "F18": null
  },
  "data": {
    "missingness": "explicit"
  },
  "next_cursor": null
}
```

## `youtube_niche_outliers`

Inspect canonical candidate hits with internal F1 lift, absolute reach, baseline, ordinary floor, F7 follow-ups and F20 chronology. Provider outlier scores are separate context and cannot establish niche quality.

Returns absolute goal hits plus the declared F1 candidate even below the absolute goal. F1 uses only its canonical candidate baseline; other candidates explicitly lack F1. F7 and F20 are anchor-specific. T4 outlier scores appear separately; an outlier alone cannot support a niche.

Required request fields: research_id. Optional fields: limit, cursor.

Output: common envelope above; paginated `evidence` rows and `data` descriptors.

Provider/network/quota: stored-only, no provider key required, zero HTTP/quota.

Persistence: read-only projection (explicit refresh may append captures on discover/analyze).

Errors: fixed common vocabulary; missing evidence remains structured, never zero. Retention: transitive source expiry/permission gates remain binding. No raw text or secret access.

Example call:
```json
{
  "name": "youtube_niche_outliers",
  "arguments": {
    "request": {
      "research_id": "saved-research-a",
      "limit": 10
    }
  }
}
```

Result shape (illustrative, not a measured result):
```json
{
  "state": "available",
  "summary": "Scoped retained evidence or stored watch intent",
  "research_id": "saved-research-a",
  "evidence": [],
  "confidence": {
    "level": "unknown",
    "F18": null
  },
  "data": {
    "missingness": "explicit"
  },
  "next_cursor": null
}
```

## `youtube_niche_content_gaps`

Inspect evidence-gated content and packaging gap states with demand, supply, differentiation, feasibility and sample coverage. Low supply alone is insufficient demand evidence.

Returns the frozen supported_gap, possible_gap, saturated, insufficient_demand_evidence, insufficient_supply_evidence, insufficient_differentiation or unknown states; scoped review payloads include demand/supply references, differentiation and feasibility. Topic nodes and source type are shown; reviews do not invent a creative premise.

Required request fields: research_id. Optional fields: limit, cursor.

Output: common envelope above; paginated `evidence` rows and `data` descriptors.

Provider/network/quota: stored-only, no provider key required, zero HTTP/quota.

Persistence: read-only projection (explicit refresh may append captures on discover/analyze).

Errors: fixed common vocabulary; missing evidence remains structured, never zero. Retention: transitive source expiry/permission gates remain binding. No raw text or secret access.

Example call:
```json
{
  "name": "youtube_niche_content_gaps",
  "arguments": {
    "request": {
      "research_id": "saved-research-a",
      "limit": 10
    }
  }
}
```

Result shape (illustrative, not a measured result):
```json
{
  "state": "available",
  "summary": "Scoped retained evidence or stored watch intent",
  "research_id": "saved-research-a",
  "evidence": [],
  "confidence": {
    "level": "unknown",
    "F18": null
  },
  "data": {
    "missingness": "explicit"
  },
  "next_cursor": null
}
```

## `youtube_niche_packaging`

Describe retained reviewed title/thumbnail mechanisms, composition, density, homogeneity and auxiliary similarity. Returns sample coverage and uncertainty; no CTR inference or forecast.

Returns reviewed title mechanisms, compositions, text density, thumbnail coverage, homogeneity/saturation and packaging gaps. Provider similarity remains T4. No CTR prediction.

Required request fields: research_id. Optional fields: limit, cursor.

Output: common envelope above; paginated `evidence` rows and `data` descriptors.

Provider/network/quota: stored-only, no provider key required, zero HTTP/quota.

Persistence: read-only projection (explicit refresh may append captures on discover/analyze).

Errors: fixed common vocabulary; missing evidence remains structured, never zero. Retention: transitive source expiry/permission gates remain binding. No raw text or secret access.

Example call:
```json
{
  "name": "youtube_niche_packaging",
  "arguments": {
    "request": {
      "research_id": "saved-research-a",
      "limit": 10
    }
  }
}
```

Result shape (illustrative, not a measured result):
```json
{
  "state": "available",
  "summary": "Scoped retained evidence or stored watch intent",
  "research_id": "saved-research-a",
  "evidence": [],
  "confidence": {
    "level": "unknown",
    "F18": null
  },
  "data": {
    "missingness": "explicit"
  },
  "next_cursor": null
}
```

## `youtube_niche_audience_demand`

Inspect separate public demand dimensions F3/F4/F8/F9/F11/F14/F19 and reviewed gap demand. No private overlap, retention, watch time or returning-viewer inference.

Keeps F3 attainment, F4 entrant frame, F8 breadth, F9 concentration, F11 momentum, F14 public engagement, F19 exposure and reviewed demand signals separate. No private audience overlap, retention or watch-time inference.

Required request fields: research_id. Optional fields: limit, cursor.

Output: common envelope above; paginated `evidence` rows and `data` descriptors.

Provider/network/quota: stored-only, no provider key required, zero HTTP/quota.

Persistence: read-only projection (explicit refresh may append captures on discover/analyze).

Errors: fixed common vocabulary; missing evidence remains structured, never zero. Retention: transitive source expiry/permission gates remain binding. No raw text or secret access.

Example call:
```json
{
  "name": "youtube_niche_audience_demand",
  "arguments": {
    "request": {
      "research_id": "saved-research-a",
      "limit": 10
    }
  }
}
```

Result shape (illustrative, not a measured result):
```json
{
  "state": "available",
  "summary": "Scoped retained evidence or stored watch intent",
  "research_id": "saved-research-a",
  "evidence": [],
  "confidence": {
    "level": "unknown",
    "F18": null
  },
  "data": {
    "missingness": "explicit"
  },
  "next_cursor": null
}
```

## `youtube_niche_sustainability`

Inspect repeatability, breadth, momentum, older catalog, idea depth, sources, series and production burden with historical maturity. Descriptive dimensions do not guarantee longevity.

Returns repeatability, breadth, momentum, older catalog, idea feasibility, series structure, source-to-story and production burden with history maturity. No longevity guarantee.

Required request fields: research_id. Optional fields: limit, cursor.

Output: common envelope above; paginated `evidence` rows and `data` descriptors.

Provider/network/quota: stored-only, no provider key required, zero HTTP/quota.

Persistence: read-only projection (explicit refresh may append captures on discover/analyze).

Errors: fixed common vocabulary; missing evidence remains structured, never zero. Retention: transitive source expiry/permission gates remain binding. No raw text or secret access.

Example call:
```json
{
  "name": "youtube_niche_sustainability",
  "arguments": {
    "request": {
      "research_id": "saved-research-a",
      "limit": 10
    }
  }
}
```

Result shape (illustrative, not a measured result):
```json
{
  "state": "available",
  "summary": "Scoped retained evidence or stored watch intent",
  "research_id": "saved-research-a",
  "evidence": [],
  "confidence": {
    "level": "unknown",
    "F18": null
  },
  "data": {
    "missingness": "explicit"
  },
  "next_cursor": null
}
```

## `youtube_niche_risk`

Inspect separate rights/reuse, platform-policy, factual/editorial, production dependency, creator capacity and policy freshness assessments. Returns unresolved reviews; no legal verdict or fair-use duration.

Separates rights/reuse, platform policy, factual/editorial burden, production dependency, creator constraints and policy freshness. Missing review is unknown; no legal verdict or safe reuse duration.

Required request fields: research_id. Optional fields: limit, cursor.

Output: common envelope above; paginated `evidence` rows and `data` descriptors.

Provider/network/quota: stored-only, no provider key required, zero HTTP/quota.

Persistence: read-only projection (explicit refresh may append captures on discover/analyze).

Errors: fixed common vocabulary; missing evidence remains structured, never zero. Retention: transitive source expiry/permission gates remain binding. No raw text or secret access.

Example call:
```json
{
  "name": "youtube_niche_risk",
  "arguments": {
    "request": {
      "research_id": "saved-research-a",
      "limit": 10
    }
  }
}
```

Result shape (illustrative, not a measured result):
```json
{
  "state": "available",
  "summary": "Scoped retained evidence or stored watch intent",
  "research_id": "saved-research-a",
  "evidence": [],
  "confidence": {
    "level": "unknown",
    "F18": null
  },
  "data": {
    "missingness": "explicit"
  },
  "next_cursor": null
}
```

## `youtube_niche_geo_language`

Inspect verified/likely/unknown/conflicting spoken language separately from provider/title/subtitle evidence, declared country and optional geographic context. Provider audience geography is an estimate, never official audience fact.

Returns frozen spoken-language classification/basis, public metadata language and conflicting claims. Declared country is an optional 24-hour permission-checked current metadata display cache, separate from frozen analytical evidence. Channel country is not audience geography; NexLev geography is a T5 estimate.

Required request fields: research_id. Optional fields: limit, cursor.

Output: common envelope above; paginated `evidence` rows and `data` descriptors.

Provider/network/quota: stored-only, no provider key required, zero HTTP/quota.

Persistence: read-only projection (explicit refresh may append captures on discover/analyze).

Errors: fixed common vocabulary; missing evidence remains structured, never zero. Retention: transitive source expiry/permission gates remain binding. No raw text or secret access.

Example call:
```json
{
  "name": "youtube_niche_geo_language",
  "arguments": {
    "request": {
      "research_id": "saved-research-a",
      "limit": 10
    }
  }
}
```

Result shape (illustrative, not a measured result):
```json
{
  "state": "available",
  "summary": "Scoped retained evidence or stored watch intent",
  "research_id": "saved-research-a",
  "evidence": [],
  "confidence": {
    "level": "unknown",
    "F18": null
  },
  "data": {
    "missingness": "explicit"
  },
  "next_cursor": null
}
```

## `youtube_niche_history`

Inspect retained F10/F11/F12/F13/F20/F21 and protocol/maturity states. Unavailable history stays unavailable; current counts never reconstruct the past.

Returns F10/F11/F12/F13/F20/F21 with per-metric availability, panel protocol/coverage comparability and history maturity. Provider history stays auxiliary. No interpolation or current-count backfill.

Required request fields: research_id. Optional fields: limit, cursor.

Output: common envelope above; paginated `evidence` rows and `data` descriptors.

Provider/network/quota: stored-only, no provider key required, zero HTTP/quota.

Persistence: read-only projection (explicit refresh may append captures on discover/analyze).

Errors: fixed common vocabulary; missing evidence remains structured, never zero. Retention: transitive source expiry/permission gates remain binding. No raw text or secret access.

Example call:
```json
{
  "name": "youtube_niche_history",
  "arguments": {
    "request": {
      "research_id": "saved-research-a",
      "limit": 10
    }
  }
}
```

Result shape (illustrative, not a measured result):
```json
{
  "state": "available",
  "summary": "Scoped retained evidence or stored watch intent",
  "research_id": "saved-research-a",
  "evidence": [],
  "confidence": {
    "level": "unknown",
    "F18": null
  },
  "data": {
    "missingness": "explicit"
  },
  "next_cursor": null
}
```

## `youtube_niche_watchlist`

Create, read, list, revise or disable local niche-boundary watch intent with target channels, metrics, cadence and expiry. Revision checks prevent lost updates. Definitions only: no scheduler or automatic monitoring.

Manages a known niche boundary and optional target channels plus desired observations/cadence/history preferences. Local intent only.

Required request fields: action. Optional fields: limit, cursor, watch_id, expected_revision, profile, owner_context, expires_at, boundary_id, target_channels.

Output: common envelope above; paginated `evidence` rows and `data` descriptors.

Provider/network/quota: stored-only, no provider key required, zero HTTP/quota.

Persistence: local watch configuration only.

Errors: fixed common vocabulary; missing evidence remains structured, never zero. Retention: transitive source expiry/permission gates remain binding. No raw text or secret access.

Example call:
```json
{
  "name": "youtube_niche_watchlist",
  "arguments": {
    "request": {
      "action": "create",
      "watch_id": "technical-history-watch",
      "boundary_id": "technical-history-v1",
      "profile": {
        "desired_metrics": [
          "floor",
          "history",
          "risk"
        ],
        "cadence_days": 7,
        "history_required": true
      }
    }
  }
}
```

Result shape (illustrative, not a measured result):
```json
{
  "state": "configured",
  "summary": "Scoped retained evidence or stored watch intent",
  "research_id": null,
  "evidence": [],
  "confidence": {
    "level": "unknown",
    "F18": null
  },
  "data": {
    "missingness": "explicit"
  },
  "next_cursor": null
}
```

## `youtube_competitor_analyze`

Describe a canonical channel's retained official public statistics, eligibility, memberships, scoped channel outcomes, patterns, risks, provider conflicts and history. Niche aggregates remain separate context; unknown subscribers and ownership stay unknown.

Returns official current size with observation dates, hidden subscribers as null, classifications, memberships, ownership, scoped age-matched floor/outcomes, descriptive breakout counts, anchor repeatability, observed uploads/topic/packaging and provider conflicts. Niche-wide production/risk/confidence is labeled separate context; channel-specific review/complete cadence is unknown where unsupported.

Required request fields: channel_id. Optional fields: limit, cursor, research_id, acquisition.

Output: common envelope above; paginated `evidence` rows and `data` descriptors.

Provider/network/quota: stored by default; explicitly gated refresh may consume the documented quota.

Persistence: read-only projection (explicit refresh may append captures on discover/analyze).

Errors: fixed common vocabulary; missing evidence remains structured, never zero. Retention: transitive source expiry/permission gates remain binding. No raw text or secret access.

Example call:
```json
{
  "name": "youtube_competitor_analyze",
  "arguments": {
    "request": {
      "channel_id": "UC0000000000000000000001",
      "research_id": "saved-research-a"
    }
  }
}
```

Result shape (illustrative, not a measured result):
```json
{
  "state": "available",
  "summary": "Scoped retained evidence or stored watch intent",
  "research_id": "saved-research-a",
  "evidence": [],
  "confidence": {
    "level": "unknown",
    "F18": null
  },
  "data": {
    "missingness": "explicit"
  },
  "next_cursor": null
}
```

## `youtube_competitor_compare`

Compare 2–10 canonical channels descriptively by current size, scoped ordinary floor, breakout dependence, repeatability, observed upload chronology, topics, packaging, production and historical coverage. No objectively better creator or private analytics inference.

Descriptive comparison under one optional frozen context: dated current size, floor, breakout counts, repeatability, observed upload chronology, topics, packaging, production/history missingness and ownership. Sister groups do not become independent samples. No best-creator claim.

Required request fields: channel_ids. Optional fields: research_id.

Output: common envelope above; paginated `evidence` rows and `data` descriptors.

Provider/network/quota: stored-only, no provider key required, zero HTTP/quota.

Persistence: read-only projection (explicit refresh may append captures on discover/analyze).

Errors: fixed common vocabulary; missing evidence remains structured, never zero. Retention: transitive source expiry/permission gates remain binding. No raw text or secret access.

Example call:
```json
{
  "name": "youtube_competitor_compare",
  "arguments": {
    "request": {
      "channel_ids": [
        "UC0000000000000000000001",
        "UC0000000000000000000002"
      ],
      "research_id": "saved-research-a"
    }
  }
}
```

Result shape (illustrative, not a measured result):
```json
{
  "state": "available",
  "summary": "Scoped retained evidence or stored watch intent",
  "research_id": "saved-research-a",
  "evidence": [],
  "confidence": {
    "level": "unknown",
    "F18": null
  },
  "data": {
    "missingness": "explicit"
  },
  "next_cursor": null
}
```

## `youtube_competitor_watch`

Manage competitor-specific local watch intent for named channel IDs and desired observations/thresholds/history. Separate from niche-boundary watches; definitions only, without background scheduling.

Manages canonical competitor channel targets, observation preferences, optional thresholds and snapshot/history intent. Separate watch_type and target semantics; no background executor.

Required request fields: action. Optional fields: limit, cursor, watch_id, expected_revision, profile, owner_context, expires_at, channel_ids.

Output: common envelope above; paginated `evidence` rows and `data` descriptors.

Provider/network/quota: stored-only, no provider key required, zero HTTP/quota.

Persistence: local watch configuration only.

Errors: fixed common vocabulary; missing evidence remains structured, never zero. Retention: transitive source expiry/permission gates remain binding. No raw text or secret access.

Example call:
```json
{
  "name": "youtube_competitor_watch",
  "arguments": {
    "request": {
      "action": "create",
      "watch_id": "competitor-watch",
      "channel_ids": [
        "UC0000000000000000000001"
      ],
      "profile": {
        "desired_metrics": [
          "public_statistics",
          "history"
        ],
        "cadence_days": 7,
        "thresholds": {
          "uploads": 1
        }
      }
    }
  }
}
```

Result shape (illustrative, not a measured result):
```json
{
  "state": "configured",
  "summary": "Scoped retained evidence or stored watch intent",
  "research_id": null,
  "evidence": [],
  "confidence": {
    "level": "unknown",
    "F18": null
  },
  "data": {
    "missingness": "explicit"
  },
  "next_cursor": null
}
```

Ten-row comparisons preserve every requested run and compact F18 components to canonical states and counts. Assessment scope, agreement numerator/denominator, history maturity and missingness remain visible; use research and focused tools for the evidence rosters.
