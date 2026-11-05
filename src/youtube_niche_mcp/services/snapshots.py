"""Explicit prospective capture of known IDs. No scheduler or historical backfill."""

from youtube_niche_mcp import __version__
from youtube_niche_mcp.api.client import YouTubeClient
from youtube_niche_mcp.collectors.normalize import normalize
from youtube_niche_mcp.db.transactions import atomic
from youtube_niche_mcp.domain.foundation import Outcome, timestamp, valid_id
from youtube_niche_mcp.history.repository import HistoryRepository
from youtube_niche_mcp.services.safety import identity, safe_json


class SnapshotService:
    def __init__(self, client: YouTubeClient, repository: HistoryRepository):
        self.client, self.repository = client, repository

    async def capture(
        self,
        job_id: str,
        *,
        video_ids: list[str] | None = None,
        channel_ids: list[str] | None = None,
        batch_stats: bool = False,
    ) -> dict:
        if not job_id or len(job_id) > 128:
            raise ValueError("Explicit bounded capture identity required")
        targets = {"video": sorted(set(video_ids or [])), "channel": sorted(set(channel_ids or []))}
        safe_json([job_id, targets], self.client.secret_values())
        if any(not valid_id(kind, value) for kind, values in targets.items() for value in values):
            raise ValueError("Malformed snapshot target")
        target_hash = identity([targets, batch_stats])
        connection = self.repository.connection
        existing = connection.execute(
            "SELECT * FROM snapshot_jobs WHERE job_id=?", (job_id,)
        ).fetchone()
        if existing and existing["targets_hash"] != target_hash:
            raise ValueError("Job replay cannot change targets or route")
        if existing and existing["finished_at"]:
            return self.status(job_id)
        if existing is None:
            with atomic(connection):
                connection.execute(
                    "INSERT INTO snapshot_jobs VALUES (?, ?, NULL, ?, ?, ?)",
                    (job_id, timestamp(self.client.clock()), "running", target_hash, __version__),
                )
        for kind, values in targets.items():
            done = {
                row[0]
                for row in connection.execute(
                    "SELECT entity_id FROM snapshot_targets WHERE job_id=? AND entity_kind=?",
                    (job_id, kind),
                )
            }
            pending = [value for value in values if value not in done]
            for result in await self.client.hydrate(
                kind, pending, batch_stats=batch_stats and kind == "video"
            ):
                observation = normalize(result, kind, job_id)
                with atomic(connection):
                    observation_id = self.repository.append(observation)
                    p = observation.provenance
                    connection.execute(
                        "INSERT INTO snapshot_targets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            job_id,
                            kind,
                            result.entity_id,
                            observation.outcome.value,
                            observation_id,
                            timestamp(observation.request_at),
                            timestamp(p.observed_at),
                            timestamp(p.available_at),
                            observation.outcome_detail,
                            observation.http_status,
                        ),
                    )
        failures = connection.execute(
            "SELECT COUNT(*) FROM snapshot_targets WHERE job_id=? AND outcome!=?",
            (job_id, Outcome.AVAILABLE.value),
        ).fetchone()[0]
        with atomic(connection):
            connection.execute(
                "UPDATE snapshot_jobs SET finished_at=?, status=? WHERE job_id=?",
                (
                    timestamp(self.client.clock()),
                    "partial_response" if failures else "completed",
                    job_id,
                ),
            )
        return self.status(job_id)

    def status(self, job_id: str) -> dict:
        job = self.repository.connection.execute(
            "SELECT * FROM snapshot_jobs WHERE job_id=?", (job_id,)
        ).fetchone()
        targets = [
            dict(row)
            for row in self.repository.connection.execute(
                "SELECT * FROM snapshot_targets WHERE job_id=? ORDER BY entity_kind, entity_id",
                (job_id,),
            )
        ]
        return {"job": dict(job) if job else None, "targets": targets}
