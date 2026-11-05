"""Deterministic data acquisition, outlier evidence and inspection stage tests."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from youtube_niche_mcp import inspection_research as inspection
from youtube_niche_mcp import outlier_research as outlier
from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.general_research import GeneralResult

CHANNEL = "UC" + "x" * 22
NOW = datetime(2026, 11, 5, 10, tzinfo=UTC)


def sample_row(i, *, views=1000, age=15, duration="PT15M", live=False):
    return {
        "id": f"{i:011d}",
        "title": f"Video {i}",
        "views": views,
        "published_at": (NOW - timedelta(days=age)).isoformat(),
        "duration": duration,
        "is_live_archive": live,
        "metadata_source": "youtube_data_api",
    }


def test_parse_public_duration():
    assert outlier.duration_seconds("PT1H3M10S") == 3790
    assert outlier.duration_seconds("P1DT5M") == 86700
    assert outlier.duration_seconds(600) == 600
    assert outlier.duration_seconds("unknown") is None


def test_leave_one_out_age_bucket_outlier_without_fake_historical_views():
    rows = [sample_row(i) for i in range(6)]
    rows.append(sample_row(6, views=9000))
    rows.append(sample_row(7, views=80000, age=900))
    rows.append(sample_row(8, duration="PT30S", views=1_000_000))
    rows.append(sample_row(9, live=True, views=1_000_000))
    result = outlier.compute_outliers(
        rows,
        outlier.OutlierScanRequest(channel_id=CHANNEL, min_peer_sample=5),
        now=NOW,
    )
    top = next(x for x in result.items if x["id"] == "00000000006")
    assert top["coarse_age_cohort_ratio"] == 9.0
    assert top["peer_sample"] == 6
    assert top["outlier_band"] == "5x+"
    assert top["historical_age_matched"] is False
    assert result.metadata["excluded"]["short_or_under_min_duration"] == 1
    assert result.metadata["excluded"]["livestream"] == 1
    assert result.metadata["windows"]["last_30_days"]["eligible_count"] == 7
    assert result.metadata["windows"]["last_90_days"]["eligible_count"] == 7
    assert result.metadata["windows"]["all_sampled"]["eligible_count"] == 8


def test_tiny_cohort_is_insufficient_not_fake_green():
    rows = [sample_row(0, views=30000), sample_row(1)]
    result = outlier.compute_outliers(rows, outlier.OutlierScanRequest(channel_id=CHANNEL), now=NOW)
    assert all(item["coarse_age_cohort_ratio"] is None for item in result.items)
    assert all(item["confidence"] == "insufficient" for item in result.items)


@pytest.mark.anyio
async def test_pagination_hydrates_public_video_metadata(monkeypatch):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.calls = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def request(self, endpoint, params):
            self.calls.append((endpoint, params))
            if endpoint == "channels.list":
                return SimpleNamespace(
                    body={
                        "items": [
                            {"contentDetails": {"relatedPlaylists": {"uploads": "UU" + "x" * 22}}}
                        ]
                    }
                )
            if endpoint == "playlistItems.list":
                offset = 2 if params.get("pageToken") == "NEXT" else 0
                values = ["A" * 10 + str(i) for i in range(offset, offset + 2)]
                return SimpleNamespace(
                    body={
                        "items": [{"contentDetails": {"videoId": v}} for v in values],
                        **({"nextPageToken": "NEXT"} if offset == 0 else {}),
                    }
                )
            if endpoint == "videos.list":
                return SimpleNamespace(
                    body={
                        "items": [
                            {
                                "id": v,
                                "snippet": {
                                    "title": "Royal documentary " + v,
                                    "publishedAt": "2026-10-14T11:00:00Z",
                                    "channelId": CHANNEL,
                                },
                                "statistics": {"viewCount": "2000"},
                                "contentDetails": {"duration": "PT12M"},
                            }
                            for v in params["id"].split(",")
                        ]
                    }
                )
            raise AssertionError(endpoint)

    monkeypatch.setattr(outlier, "YouTubeClient", FakeClient)
    result = await outlier.collect(
        Settings(youtube_api_key=SecretStr("fake")),
        outlier.DeepUploadsRequest(channel_id=CHANNEL, max_uploads=4),
    )
    assert result.source == "youtube_data_api"
    assert len(result.items) == 4
    assert result.items[0]["duration_seconds"] == 720
    assert all(item["views"] == 2000 for item in result.items)


@pytest.mark.anyio
async def test_outlier_inspection_plan_has_four_timestamped_windows():
    result = await inspection.plan(
        Settings(), inspection.PlanRequest(video_id="N7JanqWb9W0", duration_seconds=915)
    )
    assert result.state == "available"
    assert [x["stage"] for x in result.items] == list(inspection.STAGE_NAMES)
    assert result.items[0]["start"] == "00:00:00"
    assert result.items[-1]["end"] == "00:15:15"
    assert all(x["status"] == "planned_not_inspected" for x in result.items)
    assert all(x["watch_request"]["question"] for x in result.items)
    assert all(x["watch_request"]["processing_mode"] == "local_first" for x in result.items)


@pytest.mark.anyio
async def test_inspection_review_flags_transcript_only(monkeypatch):
    async def fake_status(req):
        return GeneralResult(
            state="partial",
            summary="Transcript only",
            metadata={
                "status": "completed",
                "engine": "local",
                "frames_available": 0,
                "transcript_available": True,
                "result": "Narration text",
            },
        )

    monkeypatch.setattr(inspection, "watch_status", fake_status)
    result = await inspection.review(
        inspection.ReviewRequest(
            stages=[inspection.CompletedStage(stage="opening", job_id="a" * 32)]
        )
    )
    assert result.state == "partial"
    assert result.items[0]["evidence_label"] == "transcript_only"
    assert result.metadata["complete_four_stage_coverage"] is False


def test_optional_title_family_filter_is_not_a_forced_niche_rule():
    rows = [sample_row(i) for i in range(7)]
    req = outlier.OutlierScanRequest(
        channel_id=CHANNEL,
        min_peer_sample=3,
        include_title_terms=["Video"],
        exclude_title_terms=["Video 0"],
    )
    result = outlier.compute_outliers(rows, req, now=NOW)
    assert result.metadata["eligible_total"] == 6
    assert result.metadata["excluded"]["outside_selected_title_family"] == 1
    assert result.metadata["title_family_terms"]["exclude"] == ["Video 0"]


def test_completed_broadcast_metadata_is_not_assumed_livestream():
    raw = {
        "snippet": {"liveBroadcastContent": "none"},
        "liveStreamingDetails": {
            "scheduledStartTime": "2026-10-20T17:00:00Z",
            "actualStartTime": "2026-10-20T17:00:12Z",
            "actualEndTime": "2026-10-20T17:59:00Z",
        },
    }
    assert outlier.classify_broadcast(raw) == "completed_broadcast_or_premiere"
    raw["snippet"]["liveBroadcastContent"] = "live"
    assert outlier.classify_broadcast(raw) == "currently_live"
    raw["snippet"]["liveBroadcastContent"] = "upcoming"
    assert outlier.classify_broadcast(raw) == "upcoming"


def test_completed_documentary_premieres_retained_default_and_excludable():
    rows = []
    for i in range(10):
        row = sample_row(i, views=1000 + i * 500)
        row["title"] = f"Full Documentary: Royalty {i}"
        row["broadcast_kind"] = "completed_broadcast_or_premiere"
        row["broadcast_metadata_present"] = True
        row["is_live_archive"] = False
        rows.append(row)
    req = outlier.OutlierScanRequest(channel_id=CHANNEL, min_peer_sample=3)
    included = outlier.compute_outliers(rows, req, now=NOW)
    assert included.metadata["eligible_total"] == 10
    assert included.metadata["broadcast_ambiguous_retained"] == 10
    assert included.metadata["excluded"]["livestream"] == 0
    strict = outlier.compute_outliers(
        rows,
        outlier.OutlierScanRequest(
            channel_id=CHANNEL, broadcast_policy="exclude_all_broadcast_metadata"
        ),
        now=NOW,
    )
    assert strict.state == "insufficient_evidence"
    assert strict.metadata["excluded"]["broadcast_archives_by_policy"] == 10
