"""Bounded projections and context-bound pagination, never internal DB dumps."""

import base64
import json
import re
from hashlib import sha256

from youtube_niche_mcp.services.safety import FORBIDDEN, safe_json
from youtube_niche_mcp.tools.errors import PublicError
from youtube_niche_mcp.tools.schemas import MetricCard

HIDDEN = FORBIDDEN | {
    "manifest",
    "metadata_json",
    "record_json",
    "claim_json",
    "definition_json",
    "payload_json",
    "provenance_json",
    "raw",
    "raw_text",
    "text",
    "transcript",
    "comments",
    "text_original",
    "text_display",
    "frozen_discovery",
    "sql",
    "traceback",
    "stack",
    "db_path",
    "path",
    "log",
    "logs",
    "provider_raw",
    "rationale",
    "approval_reference",
    "verified_by",
    "cookie",
    "reasoning",
    "chain_of_thought",
    "profile_id",
    "hours_per_week",
    "monthly_cash",
    "skills",
    "team_size",
    "releases_per_week_capacity_before_additional_overhead",
}
SENSITIVE = re.compile(
    r"(?i)(?:[a-z]:[\\/]|(?:^|\s)/(?:users|home|tmp|etc)/|bearer\s|api[_-]?key\s*[=:]|(?:select|insert|update|delete)\s.+\b(?:from|into|table)\b)"
)


def project(value, secrets=(), *, depth=0, budget=None):
    """Bound each branch, label omissions, strip unsafe fields and credential strings."""
    if isinstance(value, str):
        if SENSITIVE.search(value) or any(s and s in value for s in secrets):
            return "[withheld]"
        return value[:360] + ("… [truncated]" if len(value) > 360 else "")
    if not isinstance(value, (dict, tuple, list)):
        return value
    budget = budget if budget is not None else [1200]
    budget[0] -= 1
    if budget[0] < 0 or depth > 7:
        return {"omitted": True}
    if isinstance(value, dict):
        pairs = [(k, v) for k, v in value.items() if str(k).lower().replace("-", "_") not in HIDDEN]
        result = {}
        for k, v in pairs[:40]:
            if not SENSITIVE.search(str(k)) and not any(s and s in str(k) for s in secrets):
                if k in {"channel_ids", "target_channels"} and isinstance(v, (tuple, list)):
                    # Validated watch targets are primary subjects, rather than detail examples.
                    result[str(k)] = [project(x, secrets) for x in v[:100]]
                    if len(v) > 100:
                        result[str(k)].append({"omitted_items": len(v) - 100})
                else:
                    result[str(k)[:120]] = project(v, secrets, depth=depth + 1, budget=budget)
        if len(pairs) > 40:
            result["omitted_fields"] = len(pairs) - 40
        return result
    if isinstance(value, (tuple, list)):
        result = [project(v, secrets, depth=depth + 1, budget=budget) for v in value[:20]]
        if len(value) > 20:
            result.append({"omitted_items": len(value) - 20})
        return result
    return value


def card(metric, secrets=(), *, include_details=True):
    d = metric.model_dump(mode="json")
    return MetricCard(
        dimension=metric.formula_id,
        state=metric.state,
        value=d["value"],
        numerator=d["numerator"],
        denominator=d["denominator"],
        unit=metric.unit,
        age_days=metric.age_days,
        goal=metric.goal,
        mature=metric.mature,
        pending=metric.pending,
        unknown=metric.unknown,
        details=project(d["details"], secrets) if include_details else {},
        warnings=project(d["warnings"], secrets),
    )


def page(items, request, context):
    digest = sha256(safe_json([context, items]).encode()).hexdigest()[:24]
    offset = 0
    if request.cursor:
        try:
            token = json.loads(base64.urlsafe_b64decode(request.cursor.encode()).decode())
            if (
                set(token) != {"context", "offset"}
                or token["context"] != digest
                or type(token["offset"]) is not int
            ):
                raise ValueError
            offset = token["offset"]
            if not 0 <= offset < len(items):
                raise ValueError
        except (ValueError, TypeError, UnicodeError):
            raise PublicError("invalid_input") from None
    end = offset + request.limit
    cursor = (
        base64.urlsafe_b64encode(safe_json({"context": digest, "offset": end}).encode()).decode()
        if end < len(items)
        else None
    )
    return items[offset:end], cursor


PRIMARY = {
    "research_id",
    "channel_id",
    "video_id",
    "watch_id",
    "boundary_id",
    "annotation_id",
    "subject",
    "entity_id",
    "entity_kind",
    "state",
}

# Reserve space for SDK content/metadata and the JSON-RPC transport envelope.
RESULT_BYTE_LIMIT = 116000


def compact_confidence(value):
    """Project ordinal states, scope and agreement counts; never recalculate confidence."""
    result = {k: v for k, v in value.items() if not isinstance(v, (dict, list))}
    f18 = value.get("F18")
    if isinstance(f18, dict):
        result["F18"] = {
            k: v
            for k, v in f18.items()
            if k
            in {
                "confidence",
                "assessment_scope",
                "consistent_specifications",
                "comparable_specifications",
                "planned_specifications",
                "specification_agreement",
            }
        }
        components = f18.get("components", {})
        result["F18"]["component_states"] = {
            k: v.get("state") for k, v in components.items() if isinstance(v, dict) and "state" in v
        }
    for name in ("history_maturity", "critical_missing_evidence", "sensitivity_flags"):
        item = value.get(name)
        if isinstance(item, list):
            result[name] = item[:4]
            if len(item) > 4:
                result[name].append({"omitted_items": len(item) - 4})
        elif isinstance(item, dict):
            result[name] = {k: v for k, v in item.items() if not isinstance(v, (dict, list))}
    return result


def quota_totals(entries):
    """Keep all attempt/cost totals when detail receipts exceed the response budget."""
    groups = {}
    for entry in entries:
        provider = entry.get("provider", "unknown")
        row = groups.setdefault(
            provider,
            {
                "provider": provider,
                "requests": 0,
                "documented_cost_total": 0,
                "known_charged_cost_total": 0,
                "unknown_charge_requests": 0,
                "detail_omitted": True,
                "receipt_source": "local_quota_ledger",
            },
        )
        count = entry.get("requests", entry.get("request_count", 1))
        row["requests"] += count
        cost = entry.get("documented_cost", entry.get("recorded_assumed_cost"))
        row["documented_cost_total"] += cost if isinstance(cost, (int, float)) else 0
        charged = entry.get("actual_charged_cost", entry.get("charged_cost"))
        if charged is None:
            row["unknown_charge_requests"] += count
        else:
            row["known_charged_cost_total"] += charged
    return list(groups.values())


def minimal_confidence(value):
    f18 = value.get("F18")
    return {
        "level": value.get("level", "unknown"),
        "F18": {
            k: v
            for k, v in f18.items()
            if k
            in {
                "confidence",
                "consistent_specifications",
                "comparable_specifications",
                "planned_specifications",
                "specification_agreement",
            }
        }
        | {"assessment_scope": {"detail_omitted": True}}
        if isinstance(f18, dict)
        else f18,
        "detail_omitted": True,
    }


def bounded(result, secrets=()):
    """Compact oversized detail before retaining all primary rows under the byte ceiling."""
    data = project(result.model_dump(mode="json"), secrets, budget=[12000])
    safe_json(data, secrets)
    # Do not recursively truncate result arrays: schema-bearing fields remain typed.
    result = result.model_copy(
        update={
            "summary": project(result.summary, secrets),
            "boundary": project(result.boundary, secrets),
            "confidence": project(result.confidence, secrets),
            "supports": project(result.supports, secrets)[:20],
            "concerns": project(result.concerns, secrets)[:20],
            "unknowns": project(result.unknowns, secrets)[:20],
            "warnings": [project(w, secrets) for w in result.warnings[:20]],
            "data": project(result.data, secrets),
            "evidence": [project(e, secrets) for e in result.evidence[:20]],
            "provenance": project(result.provenance, secrets),
            "capabilities": project(result.capabilities, secrets),
        }
    )
    if len(result.model_dump_json().encode()) > RESULT_BYTE_LIMIT:
        rows = []
        for item in result.evidence:
            row = {k: v for k, v in item.items() if k in PRIMARY}
            if "confidence" in item:
                row["confidence"] = compact_confidence(item["confidence"])
            if "axes" in item:
                row["axes"] = item["axes"]
            row["detail_omitted"] = True
            rows.append(row)
        kept = {
            k: v
            for k, v in result.data.items()
            if k
            in {
                "recommendation_state",
                "count",
                "scheduler",
                "winner",
                "scope",
            }
        }
        kept["truncation"] = {
            "reason": "response_byte_limit",
            "byte_limit": RESULT_BYTE_LIMIT,
            "primary_rows_retained": len(rows),
            "detail_compacted": True,
            "next_step": "Use the focused tool or a smaller page for evidence detail.",
        }
        result = result.model_copy(
            update={
                "metrics": [
                    m.model_copy(update={"details": {"omitted": True}}) for m in result.metrics
                ],
                "data": kept,
                "evidence": rows,
                "confidence": compact_confidence(result.confidence),
                "warnings": [
                    *result.warnings[:19],
                    "Detail compacted by response byte limit; primary subjects retained.",
                ],
            }
        )
    if len(result.model_dump_json().encode()) > RESULT_BYTE_LIMIT:
        result = result.model_copy(
            update={
                "metrics": [],
                "supports": [],
                "concerns": [],
                "unknowns": [],
                "evidence": [
                    {k: v for k, v in row.items() if k in PRIMARY or k == "detail_omitted"}
                    | (
                        {"confidence": minimal_confidence(row["confidence"])}
                        if "confidence" in row
                        else {}
                    )
                    for row in result.evidence
                ],
                "confidence": minimal_confidence(result.confidence),
                "boundary": {
                    k: v
                    for k, v in result.boundary.items()
                    if k in {"boundary_id", "taxonomy_version", "node_ids"}
                },
                "provenance": {
                    k: v
                    for k, v in result.provenance.items()
                    if k
                    in {
                        "decision_run_id",
                        "decision_run_ids",
                        "analysis_run_ids",
                        "cohort_id",
                        "video_cohort_id",
                        "cutoff",
                        "input_hash",
                    }
                },
                "quota": quota_totals(result.quota),
            }
        )
        result.data["truncation"]["metric_detail_omitted"] = True
        result.data["truncation"]["confidence_scope_detail_omitted"] = True
    assert len(result.model_dump_json().encode()) <= RESULT_BYTE_LIMIT, "Response budget exceeded"
    safe_json(result.model_dump(mode="json"), secrets)
    return result
