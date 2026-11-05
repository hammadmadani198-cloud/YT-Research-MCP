"""Compare stored discovery evidence, never trust a caller's apparent result total."""

import json
from collections import defaultdict
from hashlib import sha256

from youtube_niche_mcp.domain.foundation import timestamp
from youtube_niche_mcp.services.safety import safe_json


def digest(body):
    return sha256(safe_json(body).encode()).hexdigest()


def evidence_digest(run, pages, occurrences, cutoff):
    def known(rows):
        return [dict(r) for r in rows if r["observed_at"] <= cutoff and r["available_at"] <= cutoff]

    return digest({"run": dict(run), "pages": known(pages), "occurrences": known(occurrences)})


def read_protocols(connection, panels, now, definitions):
    wanted = {rid for p in panels if p for rid in p.discovery_run_ids}
    runs = {
        r["run_id"]: dict(r)
        for r in connection.execute("SELECT * FROM discovery_runs")
        if r["run_id"] in wanted
    }
    pages, occurrences = defaultdict(list), defaultdict(list)
    for r in connection.execute("SELECT * FROM discovery_pages ORDER BY run_id,page_number"):
        if r["run_id"] in wanted:
            pages[r["run_id"]].append(dict(r))
    for r in connection.execute("SELECT * FROM discovery_results ORDER BY run_id,rank"):
        if r["run_id"] in wanted:
            occurrences[r["run_id"]].append(dict(r))
    output = []
    for p in panels:
        if p is None:
            output.append(None)
            continue
        body, found, input_ids, expiries, evidence_manifests = [], set(), [], [], []
        state = "available" if p.discovery_run_ids else "insufficient_panel_history"
        for rid in sorted(p.discovery_run_ids):
            r = runs.get(rid)
            if not r:
                state = "insufficient_panel_history"
                continue
            if r["expires_at"] <= timestamp(now):
                state = "policy_permission_required"
                continue
            if (
                r["started_at"] > timestamp(p.cutoff)
                or not r["finished_at"]
                or r["finished_at"] > timestamp(p.cutoff)
            ):
                state = "insufficient_panel_history"
                continue
            input_ids.append(rid)
            evidence_manifests.append(
                {
                    "run_id": rid,
                    "cutoff": timestamp(p.cutoff),
                    "hash": evidence_digest(r, pages[rid], occurrences[rid], timestamp(p.cutoff)),
                }
            )
            expiries.append(r["expires_at"])
            manifest = json.loads(r["filters_json"])
            body.append(
                {
                    k: r[k]
                    for k in (
                        "query",
                        "route",
                        "provider",
                        "sort_order",
                        "region",
                        "language",
                        "mode",
                        "page_size",
                        "collection_version",
                    )
                }
            )
            body[-1]["filters"] = manifest
            pp = pages[rid]
            budget = manifest.get("max_pages")
            complete = bool(pp) and r["outcome"] == "available"
            complete &= [q["page_number"] for q in pp] == list(range(1, len(pp) + 1))
            complete &= bool(not pp or not pp[0]["request_token"])
            for i, page in enumerate(pp):
                complete &= page["available_at"] <= timestamp(p.cutoff)
                complete &= page["observed_at"] <= timestamp(p.cutoff)
                complete &= page["outcome"] == "available"
                if i:
                    complete &= page["request_token"] == pp[i - 1]["next_token"]
            complete &= bool(pp) and (not pp[-1]["next_token"] or len(pp) == budget)
            if not complete and state == "available":
                state = "partial_coverage"
            for occurrence in occurrences[rid]:
                if (
                    occurrence["available_at"] <= timestamp(p.cutoff)
                    and occurrence["observed_at"] <= timestamp(p.cutoff)
                    and occurrence["outcome"] == "available"
                    and occurrence["result_type"] == "video"
                ):
                    found.add(occurrence["result_id"])
        definition = definitions[p.video_cohort_id or p.cohort_id]
        rules = {
            k: definition[k]
            for k in (
                "long_form_rule",
                "format_rule",
                "live_rule",
                "language_rule",
                "faceless_rule",
                "allow_archived_live",
                "include_uncertain",
                "entry_rule",
            )
        }
        identity_body = {
            "routes": sorted(body, key=safe_json),
            "boundary": definition["boundary"],
            "rules": rules,
            "capability_mode": p.capability_mode,
            "provider_source_version": p.provider_source_version,
        }
        output.append(
            {
                "hash": digest(identity_body),
                "definition": identity_body,
                "state": state,
                "found": found,
                "input_ids": input_ids,
                "expiries": expiries,
                "coverage_epoch": p.coverage_epoch,
                "coverage_reference": p.coverage_reference,
                "evidence_manifests": evidence_manifests,
            }
        )
    return tuple(output)


def comparable_protocol(old, new):
    if old is None or new is None:
        return "insufficient_panel_history"
    for p in (old, new):
        if p["state"] not in {"available", "partial_coverage"}:
            return p["state"]
    if old["coverage_epoch"] != new["coverage_epoch"]:
        return "coverage_not_comparable"
    if old["hash"] != new["hash"]:
        return "unstable_discovery_protocol"
    return "partial_coverage" if "partial_coverage" in {old["state"], new["state"]} else "available"
