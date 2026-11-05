"""Local configuration lifecycle with expiry and optimistic revisions; no scheduler."""

import json
from datetime import timedelta

from youtube_niche_mcp.db.transactions import atomic
from youtube_niche_mcp.domain.foundation import timestamp
from youtube_niche_mcp.services.safety import safe_json
from youtube_niche_mcp.tools.errors import PublicError
from youtube_niche_mcp.tools.schemas import PublicResult
from youtube_niche_mcp.tools.serialization import page


def public_watch(row):
    return {
        "watch_id": row["watch_id"],
        "watch_type": row["watch_type"],
        "subject": json.loads(row["subject_json"]),
        "preferences": json.loads(row["profile_json"]),
        "enabled": bool(row["enabled"]),
        "revision": row["revision"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "expires_at": row["expires_at"],
        "owner_context": row["owner_context"],
        "last_checked_at": None,
        "scheduler": "absent",
        "execution": "intent_only",
        "state": "configured" if row["enabled"] else "disabled",
    }


def manage(history, kind, request, boundary_exists):
    c, now = history.connection, history.clock()
    if not c.execute("SELECT 1 FROM sqlite_master WHERE name='research_watches'").fetchone():
        raise PublicError("schema_upgrade_required")
    with atomic(c):
        if request.action == "list":
            rows = c.execute(
                "SELECT * FROM research_watches WHERE watch_type=? AND owner_context=? "
                "AND expires_at>? ORDER BY watch_id LIMIT 1001",
                (kind, request.owner_context, timestamp(now)),
            ).fetchall()
            if len(rows) > 1000:
                raise PublicError("budget_exceeded")
            items, cursor = page(
                [public_watch(r) for r in rows], request, [kind, request.owner_context]
            )
            return PublicResult(
                state="available",
                summary="Stored watch intent; no recurring execution.",
                evidence=items,
                next_cursor=cursor,
                data={"count": len(rows), "scheduler": "absent"},
            )
        row = c.execute(
            "SELECT * FROM research_watches WHERE watch_id=?", (request.watch_id,)
        ).fetchone()
        if row and (row["watch_type"] != kind or row["owner_context"] != request.owner_context):
            raise PublicError("not_found")
        if row and row["expires_at"] <= timestamp(now):
            raise PublicError("not_found")
        if request.action == "create":
            if kind == "niche":
                if not boundary_exists(request.boundary_id):
                    raise PublicError("insufficient_evidence")
                subject = {
                    "boundary_id": request.boundary_id,
                    "target_channels": sorted(set(request.target_channels)),
                }
            else:
                subject = {"channel_ids": sorted(set(request.channel_ids))}
            body = safe_json(subject, history.secrets)
            profile = safe_json(request.profile.model_dump(mode="json"), history.secrets)
            expires = timestamp(request.expires_at or (now + timedelta(days=365)))
            if expires <= timestamp(now):
                raise PublicError("invalid_input")
            if row:
                if (
                    row["subject_json"] != body
                    or row["profile_json"] != profile
                    or (request.expires_at and row["expires_at"] != expires)
                ):
                    raise PublicError("revision_conflict")
            else:
                c.execute(
                    "INSERT INTO research_watches VALUES(?,?,?,?,1,1,?,?,NULL,?,?)",
                    (
                        request.watch_id,
                        kind,
                        body,
                        profile,
                        timestamp(now),
                        timestamp(now),
                        request.owner_context,
                        expires,
                    ),
                )
        elif not row:
            raise PublicError("not_found")
        elif request.action in {"update", "disable"}:
            if row["revision"] != request.expected_revision:
                raise PublicError("revision_conflict")
            # Subject identity is immutable; a changed boundary/target set is a new definition.
            if kind == "niche" and (request.boundary_id or request.target_channels):
                supplied = {
                    "boundary_id": request.boundary_id
                    or json.loads(row["subject_json"])["boundary_id"],
                    "target_channels": sorted(set(request.target_channels))
                    or json.loads(row["subject_json"])["target_channels"],
                }
                if safe_json(supplied) != row["subject_json"]:
                    raise PublicError("invalid_input")
            if (
                kind == "competitor"
                and request.channel_ids
                and sorted(set(request.channel_ids))
                != json.loads(row["subject_json"])["channel_ids"]
            ):
                raise PublicError("invalid_input")
            profile = (
                safe_json(request.profile.model_dump(mode="json"), history.secrets)
                if request.action == "update"
                else row["profile_json"]
            )
            expires = timestamp(request.expires_at) if request.expires_at else row["expires_at"]
            if expires <= timestamp(now):
                raise PublicError("invalid_input")
            c.execute(
                (
                    "UPDATE research_watches SET "
                    "profile_json=?,enabled=?,revision=revision+1,updated_at=?,expires_at=?"
                    " WHERE watch_id=? AND revision=?"
                ),
                (
                    profile,
                    0 if request.action == "disable" else row["enabled"],
                    timestamp(now),
                    expires,
                    request.watch_id,
                    request.expected_revision,
                ),
            )
        row = c.execute(
            "SELECT * FROM research_watches WHERE watch_id=?", (request.watch_id,)
        ).fetchone()
    return PublicResult(
        state="configured" if row["enabled"] else "disabled",
        summary="Local watch definition stored; scheduler absent.",
        data=public_watch(row),
        reused_run=False,
        warnings=["Watch intent does not execute snapshots or monitoring."],
        next_available_actions=["read", "update", "disable"],
    )
