# Phase 7 workflows

All examples below use the MCP `tools/call` argument envelope and synthetic illustrative IDs. An unpopulated installation returns insufficient evidence. Registering tools does not seed observations, permissions, taxonomy or a statistical history.

1. Discover a candidate using `youtube_niche_discover`. Read route limitations and the returned boundary IDs.
2. Research a returned boundary with `youtube_niche_research`, or pass an existing research_id. A new frozen frame needs advanced definitions/measurement/rubric; internal review/admin APIs establish scoped evidence and permissions.
3. Pass the returned research_id to focused gaps, risk, packaging, history and demand tools. Preserve next_cursor when paging.
4. Compare 2–10 returned research IDs with compatible profiles. Read each row’s state, F18 scope, maturity and creator fit. Optional sorting is explicitly separate.
5. Analyze a channel with the same research_id to inspect its scoped floor/outcomes and separately dated current size. Compare canonical channel IDs descriptively.
6. Create a niche or competitor watch definition. Read/update/disable it by watch_id and expected_revision. An external scheduler would have to execute snapshots; none is supplied here.

## Example requests

### youtube_niche_research

```json
{
  "request": {
    "boundary_id": "technical-history-v1",
    "mode": "standard"
  }
}
```

### youtube_niche_discover

```json
{
  "request": {
    "query": "technical history",
    "mode": "quick"
  }
}
```

### youtube_niche_compare

```json
{
  "request": {
    "research_ids": [
      "saved-research-a",
      "saved-research-b"
    ]
  }
}
```

### youtube_niche_outliers

```json
{
  "request": {
    "research_id": "saved-research-a",
    "limit": 10
  }
}
```

### youtube_niche_content_gaps

```json
{
  "request": {
    "research_id": "saved-research-a",
    "limit": 10
  }
}
```

### youtube_niche_packaging

```json
{
  "request": {
    "research_id": "saved-research-a",
    "limit": 10
  }
}
```

### youtube_niche_audience_demand

```json
{
  "request": {
    "research_id": "saved-research-a",
    "limit": 10
  }
}
```

### youtube_niche_sustainability

```json
{
  "request": {
    "research_id": "saved-research-a",
    "limit": 10
  }
}
```

### youtube_niche_risk

```json
{
  "request": {
    "research_id": "saved-research-a",
    "limit": 10
  }
}
```

### youtube_niche_geo_language

```json
{
  "request": {
    "research_id": "saved-research-a",
    "limit": 10
  }
}
```

### youtube_niche_history

```json
{
  "request": {
    "research_id": "saved-research-a",
    "limit": 10
  }
}
```

### youtube_niche_watchlist

```json
{
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
```

### youtube_competitor_analyze

```json
{
  "request": {
    "channel_id": "UC0000000000000000000001",
    "research_id": "saved-research-a"
  }
}
```

### youtube_competitor_compare

```json
{
  "request": {
    "channel_ids": [
      "UC0000000000000000000001",
      "UC0000000000000000000002"
    ],
    "research_id": "saved-research-a"
  }
}
```

### youtube_competitor_watch

```json
{
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
```

## Explicit refresh example

```json
{
  "request": {
    "channel_id": "UC0000000000000000000001",
    "acquisition": {
      "refresh": true,
      "request_id": "new-metadata-capture",
      "channel_ids": [
        "UC0000000000000000000001"
      ]
    }
  }
}
```

This can call channels.list only after a configured key and valid administrative source permission exist. A new request identity appends a new dated capture. Replay does not spend again. Acquired current metadata cannot alter old frozen results. Requested geographic context is planning context, not an audience observation.

## Host configuration

Use [mcp-config.example.json](mcp-config.example.json), replacing absolute paths. The stdio executable is the repository virtualenv Python with `-m youtube_niche_mcp.server`, and cwd is the repository. Set YTNMCP_DB_PATH to an absolute existing migrated database. Optional YOUTUBE_API_KEY/NEXLEV_API_KEY are inherited process environment variables; neither is embedded in the example. No key is needed for stored tools, startup, status or verify. No global configuration was changed.