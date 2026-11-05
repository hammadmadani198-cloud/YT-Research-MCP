"""Extend existing source/conflict/discovery/claim/cache/quota infrastructure."""

import json
from contextlib import suppress
from datetime import datetime, timedelta

from youtube_niche_mcp.collectors.nexlev.client import ProviderQuotaEntry
from youtube_niche_mcp.collectors.nexlev.contracts import ROUTES, VERSION
from youtube_niche_mcp.collectors.nexlev.models import EvidenceBatch, ProviderRecord, plain_data
from youtube_niche_mcp.db.transactions import atomic
from youtube_niche_mcp.domain.foundation import timestamp
from youtube_niche_mcp.eligibility.models import Claim
from youtube_niche_mcp.eligibility.repository import EligibilityRepository
from youtube_niche_mcp.services.safety import identity, safe_json


def history_anomalies(record, requested_days=None):
    points = sorted(record.history, key=lambda p: p.date)
    flags = set()
    if not points:
        return ["partial_window"] if requested_days else []
    if requested_days and len({p.date.date() for p in points}) < requested_days:
        flags.add("partial_window")
    if all(p.videos == 0 for p in points):
        flags.add("implausible_all_zero_video_count")
    if points[-1].date < record.observed_at - timedelta(days=7):
        flags.add("stale_series")
    for point in points:
        if any(v is not None and v < 0 for v in (point.subscribers, point.views, point.videos)):
            flags.add("impossible_count")
        if point.date > record.observed_at or (
            point.data_fetched_at
            and (point.data_fetched_at > record.observed_at or point.data_fetched_at < point.date)
        ):
            flags.add("timestamp_conflict")
    for left, right in zip(points, points[1:], strict=False):
        if right.date - left.date > timedelta(days=1):
            flags.add("gap")
        if right.date == left.date:
            flags.add("timestamp_conflict")
        if left.subscribers is not None and right.subscribers is not None:
            if right.subscribers < left.subscribers:
                flags.add("negative_delta")
            if left.subscribers > 0 and right.subscribers > left.subscribers * 1.5:
                flags.add("implausible_rebound")
    return sorted(flags)


class NexLevRepository:
    def __init__(self, history, settings=None):
        from youtube_niche_mcp.config import Settings

        settings = settings or Settings.from_env()
        self.history, self.connection = history, history.connection
        self.secrets = history.secrets + tuple(
            key.get_secret_value()
            for key in (settings.youtube_api_key, settings.nexlev_api_key)
            if key is not None
        )
        self.eligibility = EligibilityRepository(history)

    def ingest(self, payload: EvidenceBatch | dict, *, rest_verified=False):
        # Revalidate even preconstructed models. No caller can declare canonical/verified truth.
        try:
            batch = EvidenceBatch.model_validate(
                payload.model_dump(mode="json") if isinstance(payload, EvidenceBatch) else payload
            )
        except ValueError:
            raise ValueError(
                "Invalid external evidence; allowed fields and clocks required"
            ) from None
        body = batch.model_dump(mode="json")
        if batch.access_mode == "documented_rest" and not rest_verified:
            raise ValueError("External ingestion cannot self-attest REST acquisition")
        encoded = safe_json(body, self.secrets)
        content_hash = identity(body, self.secrets)
        if batch.fetch_at > self.history.clock() or any(
            r.available_at > self.history.clock() or r.expires_at <= self.history.clock()
            for r in batch.records
        ):
            raise ValueError("Unavailable or expired evidence cannot be ingested")
        existing = self.connection.execute(
            "SELECT content_hash FROM provider_runs WHERE run_id=?", (batch.batch_id,)
        ).fetchone()
        if existing:
            if existing[0] != content_hash:
                raise ValueError("Immutable ingestion replay differs")
            return self.manifest(batch.batch_id)
        available = max((r.available_at for r in batch.records), default=batch.fetch_at)
        expires = min(
            (r.expires_at for r in batch.records), default=batch.fetch_at + timedelta(days=1)
        )
        with atomic(self.connection):
            self.connection.execute(
                "INSERT INTO provider_runs VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    batch.batch_id,
                    "nexlev",
                    batch.route,
                    timestamp(batch.fetch_at),
                    timestamp(available),
                    timestamp(expires),
                    "evidence_batch",
                    encoded,
                    content_hash,
                ),
            )
            for record in batch.records:
                self._append(batch, record)
            if batch.discovery:
                self._discovery(batch, expires)
        return self.manifest(batch.batch_id)

    def _append(self, batch, record):
        body = record.model_dump(mode="json")
        eid = identity([batch.batch_id, body], self.secrets)
        sid = identity(["nexlev", record.route, body], self.secrets)
        provider = {
            "provider": "nexlev",
            "route": record.route,
            "provider_record_id": record.provider_record_id,
            "provider_created_at": body["provider_created_at"],
            "provider_updated_at": body["provider_updated_at"],
            "provider_capture_at": body["provider_capture_at"],
            "retrieval_at": body["fetch_at"],
            "observed_at": body["observed_at"],
            "available_at": body["available_at"],
            "source_version": VERSION,
        }
        self.history.ensure_entity(
            record.subject.entity_kind, record.subject.entity_id, record.available_at
        )
        self.connection.execute(
            "INSERT OR IGNORE INTO source_records VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                sid,
                record.route,
                "provider",
                VERSION,
                "unknown",
                timestamp(record.fetch_at),
                timestamp(record.observed_at),
                timestamp(record.available_at),
                safe_json(provider, self.secrets),
                timestamp(record.expires_at),
            ),
        )
        flags = history_anomalies(
            record, batch.discovery.requested_history_days if batch.discovery else None
        )
        if record.provider_capture_at and record.provider_capture_at > record.observed_at:
            flags.append("timestamp_conflict")
        if any(c.field == "subscriber_count" and c.value == 0 for c in record.claims):
            flags.append("provider_zero_requires_hydration")
        self.connection.execute(
            "INSERT INTO provider_evidence VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                eid,
                batch.batch_id,
                sid,
                record.subject.entity_kind,
                record.subject.entity_id,
                record.route,
                timestamp(record.observed_at),
                timestamp(record.available_at),
                timestamp(record.expires_at),
                safe_json(body, self.secrets),
                safe_json(flags),
            ),
        )
        for other in self.records(record.subject, record.available_at):
            if other["evidence_id"] != eid:
                self._compare(eid, sid, record, other)
        # Only rubric-supported classifications become Phase 2 provider claims.
        # Proprietary confidence is preserved above but never sets eligibility confidence.
        for c in record.claims:
            if c.field in {"faceless", "spoken_language", "duration_seconds", "audio_language"}:
                if c.value is None:
                    continue
                self.eligibility.append_claim(
                    Claim(
                        subject=record.subject,
                        field="spoken_language" if c.field == "audio_language" else c.field,
                        value=c.value,
                        basis="provider_label",
                        source=record.route,
                        source_version=VERSION,
                        observed_at=record.observed_at,
                        available_at=record.available_at,
                        expires_at=record.expires_at,
                        data_origin="provider_data",
                        reason="Auxiliary provider claim; independent verification required",
                    )
                )

    def _compare(self, eid, sid, record, other):
        previous = ProviderRecord.model_validate_json(other["record_json"])
        old = {c.field: c for c in previous.claims}
        for c in record.claims:
            if c.field not in old or c.value is None or old[c.field].value is None:
                continue
            if c.value == old[c.field].value:
                continue
            if c.field in {"publication_at", "account_created_at", "provider_index_at"}:
                with suppress(ValueError, TypeError):
                    left_date = datetime.fromisoformat(old[c.field].value.replace("Z", "+00:00"))
                    right_date = datetime.fromisoformat(c.value.replace("Z", "+00:00"))
                    if (
                        left_date.tzinfo is not None
                        and right_date.tzinfo is not None
                        and (left_date == right_date)
                    ):
                        continue
            count = c.field in {"view_count", "subscriber_count", "video_count"}
            left_time = previous.provider_capture_at or previous.observed_at
            right_time = record.provider_capture_at or record.observed_at
            if count and left_time != right_time:
                # Normal count changes across different snapshots are retained as observations.
                continue
            self._conflict(
                record.subject,
                c.field,
                other["evidence_id"],
                eid,
                other["source_id"],
                sid,
                "unresolved",
                record.available_at,
            )

    def _conflict(self, subject, field, left, right, left_source, right_source, preferred, at):
        cid = identity([subject.model_dump(), field, left, right])
        self.connection.execute(
            "INSERT OR IGNORE INTO source_conflicts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                cid,
                subject.entity_kind,
                subject.entity_id,
                field,
                left,
                right,
                left_source,
                right_source,
                preferred,
                "nexlev-field-conflict-v1",
                timestamp(at),
                timestamp(at),
            ),
        )

    def _discovery(self, batch, expires):
        context = batch.discovery
        encoded = safe_json(context.model_dump(mode="json"), self.secrets)
        if self.connection.execute(
            "SELECT 1 FROM discovery_runs WHERE run_id=?", (batch.batch_id,)
        ).fetchone():
            raise ValueError("Discovery run identity already owned by another collector")
        at = timestamp(batch.fetch_at)
        self.connection.execute(
            "INSERT INTO discovery_runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                batch.batch_id,
                context.query,
                batch.route,
                "nexlev",
                context.ordering,
                encoded,
                None,
                None,
                context.mode,
                context.limit,
                at,
                at,
                "partial_coverage",
                VERSION,
                timestamp(expires),
            ),
        )
        pages = sorted({r.page_number for r in batch.records}) or [1]
        for page in pages:
            self.connection.execute(
                "INSERT INTO discovery_pages VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    batch.batch_id,
                    page,
                    None,
                    None,
                    at,
                    at,
                    at,
                    "partial_coverage",
                    None,
                    "External pagination context; result count is not population size",
                ),
            )
        ranks = set()
        for record in batch.records:
            if record.rank in ranks:
                raise ValueError("Unique run ranks required, duplicate entities remain separate")
            ranks.add(record.rank)
            self.connection.execute(
                "INSERT INTO discovery_results VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    batch.batch_id,
                    record.rank,
                    record.page_number,
                    record.rank,
                    record.subject.entity_id,
                    record.subject.entity_kind,
                    "provider_candidate",
                    "partial_coverage",
                    timestamp(record.observed_at),
                    timestamp(record.available_at),
                ),
            )

    def records(self, subject, at):
        return [
            dict(row)
            for row in self.connection.execute(
                "SELECT * FROM provider_evidence WHERE entity_kind=? AND entity_id=? "
                "AND observed_at<=? AND available_at<=? AND expires_at>? "
                "ORDER BY available_at,evidence_id",
                (
                    subject.entity_kind,
                    subject.entity_id,
                    timestamp(at),
                    timestamp(at),
                    timestamp(self.history.clock()),
                ),
            )
        ]

    def manifest(self, run_id):
        row = self.connection.execute(
            "SELECT * FROM provider_runs WHERE run_id=? AND expires_at>?",
            (run_id, timestamp(self.history.clock())),
        ).fetchone()
        if not row:
            return {"run": None, "retention_state": "expired_or_missing"}
        body = json.loads(row["manifest_json"])
        if row["run_kind"] != "evidence_batch":
            return {"run": body, "retention_state": "contract_review_required"}
        ids = sorted(
            {(r["subject"]["entity_kind"], r["subject"]["entity_id"]) for r in body["records"]}
        )
        return {
            "run": body,
            "canonical_candidates": ids,
            "occurrences": len(body["records"]),
            "zero_result": len(body["records"]) == 0,
            "population_denominator": None,
            "retention_state": "contract_review_required",
        }

    def record_quota(self, entry: ProviderQuotaEntry):
        safe_json(vars(entry), self.secrets)
        if entry.endpoint not in ROUTES or entry.provider != "nexlev":
            raise ValueError("Known provider route required for quota provenance")
        with atomic(self.connection):
            cursor = self.connection.execute(
                "INSERT INTO quota_requests(endpoint,request_count,assumed_cost,bucket,"
                "requested_at,"
                "contract_version) VALUES (?,?,?,?,?,?)",
                (
                    entry.endpoint,
                    entry.request_count,
                    entry.documented_cost or 0,
                    entry.bucket,
                    entry.requested_at,
                    entry.contract_version,
                ),
            )
            self.connection.execute(
                "INSERT INTO provider_quota_details VALUES (?,?,?,?,?,?,?,?)",
                (
                    cursor.lastrowid,
                    entry.provider,
                    entry.access_mode,
                    entry.documented_cost,
                    entry.charged_cost,
                    entry.cached_free,
                    entry.http_status,
                    entry.plan_state,
                ),
            )

    def record_job_event(self, entry):
        allowed = {"job_id", "channel_id", "state", "route", "at", "cached", "poll_limit"}
        if set(entry) != allowed:
            raise ValueError("Only bounded job provenance may be persisted")
        plain_data(entry)
        at = datetime.fromisoformat(entry["at"])
        encoded = safe_json(entry, self.secrets)
        rid = identity(
            [entry, self.connection.execute("SELECT COUNT(*) FROM provider_runs").fetchone()[0]]
        )
        with atomic(self.connection):
            self.connection.execute(
                "INSERT INTO provider_runs VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    rid,
                    "nexlev",
                    entry["route"],
                    timestamp(at),
                    timestamp(at),
                    timestamp(at + timedelta(days=1)),
                    "job_event",
                    encoded,
                    identity(entry),
                ),
            )

    def compare_official(self, observation_id, observation):
        """Canonical public facts come solely from a captured official observation."""
        if not observation.provenance.source.startswith("youtube:"):
            raise ValueError("Official source required")
        from youtube_niche_mcp.eligibility.models import Subject
        from youtube_niche_mcp.eligibility.rules import duration_seconds

        subject = Subject(entity_kind=observation.entity_kind, entity_id=observation.entity_id)
        row = self.connection.execute(
            f"SELECT source_id FROM {observation.entity_kind}_observations WHERE observation_id=?",
            (observation_id,),
        ).fetchone()
        public = {
            "title": observation.metadata.title,
            "publication_at": timestamp(observation.metadata.publication_at)
            if observation.metadata.publication_at
            else None,
            "account_created_at": timestamp(observation.metadata.account_created_at)
            if observation.metadata.account_created_at
            else None,
            "duration_seconds": duration_seconds(observation.metadata.duration),
        }
        public.update({f: e.value for f, e in observation.metrics.items()})
        with atomic(self.connection):
            for record in self.records(subject, observation.provenance.available_at):
                body = ProviderRecord.model_validate_json(record["record_json"])
                for claim in body.claims:
                    value = public.get(claim.field)
                    if claim.trust_class != "T1" or value is None or claim.value is None:
                        continue
                    original = claim.value
                    if claim.field in {"publication_at", "account_created_at"}:
                        with suppress(ValueError):
                            original = timestamp(
                                datetime.fromisoformat(original.replace("Z", "+00:00"))
                            )
                    if value != original:
                        if (
                            claim.field in {"view_count", "subscriber_count", "video_count"}
                            and (body.provider_capture_at or body.observed_at)
                            != observation.provenance.observed_at
                        ):
                            continue
                        self._conflict(
                            subject,
                            claim.field,
                            record["evidence_id"],
                            observation_id,
                            record["source_id"],
                            row[0],
                            observation.provenance.source,
                            observation.provenance.available_at,
                        )
        return {
            "canonical_source": observation.provenance.source,
            "public_values": public,
            "provider_evidence_preserved": True,
        }
