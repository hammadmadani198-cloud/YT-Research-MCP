"""F18 specification agreement plus separate ordinal coverage/quality components."""

from youtube_niche_mcp.analysis.numerics import ratio


def robustness(evidence, synthesis, comparisons, options):
    components = {}
    for name, item in evidence["coverage"].items():
        if name == "qualitative":
            continue
        components[name + "_coverage"] = {
            **item,
            "state": "complete"
            if item["denominator"] and item["numerator"] == item["denominator"]
            else "partial"
            if item["numerator"]
            else "missing",
        }
    for field, item in evidence["classifications"].items():
        components[field + "_quality"] = {
            "state": "verified"
            if item["denominator"] and item["verified"] == item["denominator"]
            else "conflicted"
            if item["conflicted_ids"]
            else "unverified",
            "verified": item["verified"],
            "denominator": item["denominator"],
            "provider_only_ids": item["provider_only_ids"],
            "conflicted_ids": item["conflicted_ids"],
        }
    components["history_maturity"] = {
        "state": "mature" if not synthesis["history_maturity"]["immature"] else "immature",
        **synthesis["history_maturity"],
    }
    components["source_agreement"] = {
        "state": "conflicted" if evidence["conflicts"] else "no_observed_conflict",
        "conflicts": evidence["conflicts"],
        "warning": "No observed conflict does not prove exhaustive source agreement",
    }
    components["ownership"] = {
        "state": "unresolved"
        if evidence["ownership"]["unknown_relationship_channels"]
        else "documented"
        if evidence["ownership"]["documented_groups"]
        else "missing",
        **evidence["ownership"],
    }
    components["route_diversity"] = {
        "state": "multiple_routes"
        if len(evidence["routes"]["routes"]) > 1
        else "single_or_missing_route",
        **evidence["routes"],
    }
    components["policy_freshness"] = evidence["policy"]
    for kind in ("production", "source", "rights", "policy", "factual", "premise", "comment_theme"):
        item = evidence["coverage"]["qualitative"].get(kind)
        components[kind + "_review"] = {
            **(item or {}),
            "state": "reviewed"
            if item and "human" in item["source_types"]
            else "provider_or_model_only"
            if item
            else "missing",
        }
    family_matrix = {}
    for family in options.sensitivity.required_families:
        rows = [r for r in comparisons if r["family"] == family]
        available = [r for r in rows if r["comparable"]]
        state = (
            "sensitive"
            if any(r["material"] or not r["same_decision"] for r in available)
            else "unavailable"
            if not available
            else "partially_tested"
            if len(available) != len(rows)
            else "stable"
        )
        family_matrix[family] = {
            "state": state,
            "planned": len(rows),
            "comparable": len(available),
            "run_ids": [r["run_id"] for r in rows],
            "flip_labels": [
                r["label"] for r in available if r["material"] or not r["same_decision"]
            ],
        }
    components["sensitivity"] = family_matrix
    comparable = [r for r in comparisons if r["comparable"]]
    consistent = sum(r["same_decision"] for r in comparable)
    hard_low = bool(
        synthesis["insufficiency_gates"]
        or evidence["conflicts"]
        or synthesis["history_maturity"]["immature"]
        or evidence["policy"]["state"] != "fresh"
        or any(
            components[k + "_review"]["state"] == "provider_or_model_only"
            for k in ("production", "source", "rights", "policy", "factual")
        )
    )
    critical_quality = all(
        components[f + "_quality"]["state"] == "verified" for f in evidence["classifications"]
    )
    complete = all(
        components[n + "_coverage"]["state"] == "complete"
        for n in ("channels", "videos", "topic_classification")
    )
    reviewed = all(
        components[k + "_review"]["state"] == "reviewed"
        for k in ("production", "source", "rights", "policy", "factual", "premise")
    )
    stable = bool(family_matrix) and all(v["state"] == "stable" for v in family_matrix.values())
    confidence = (
        "low"
        if hard_low
        or any(v["state"] in {"sensitive", "unavailable"} for v in family_matrix.values())
        else "high"
        if critical_quality
        and complete
        and reviewed
        and stable
        and components["ownership"]["state"] == "documented"
        and components["route_diversity"]["state"] == "multiple_routes"
        else "medium"
    )
    matrix = {
        axis: {
            family: {
                "state": "sensitive"
                if any(
                    axis in r["changed_axes"]
                    for r in comparisons
                    if r["family"] == family and r["comparable"]
                )
                else family_matrix[family]["state"],
                "run_ids": family_matrix[family]["run_ids"],
            }
            for family in family_matrix
        }
        for axis in synthesis["axes"]
    }
    for axis in matrix:
        matrix[axis]["history"] = components["history_maturity"]["state"]
        matrix[axis]["sources"] = components["source_agreement"]["state"]
    return {
        "confidence": confidence,
        "config": options.f18_config,
        "assessment_scope": {
            "required_axes": list(options.rubric.required_axes),
            "required_history": list(options.rubric.required_history),
            "required_sensitivity_families": list(options.sensitivity.required_families),
            "warning": (
                "Confidence applies only to this declared scope; "
                "omitted axes and checks remain visible"
            ),
        },
        "components": components,
        "matrix": matrix,
        "consistent_specifications": consistent,
        "comparable_specifications": len(comparable),
        "planned_specifications": len(comparisons),
        "specification_agreement": ratio(consistent, len(comparable)),
        "unavailable": [r["label"] for r in comparisons if not r["comparable"]],
        "warning": (
            "Specification agreement and ordinal evidence confidence are not "
            "success probability or statistical confidence intervals"
        ),
        "grade_rule": (
            "High requires complete critical coverage, verified "
            "classifications/ownership, mature history, human critical "
            "reviews, multiple routes, no conflicts and all required "
            "sensitivity families stable. Low for critical "
            "gaps/conflicts/immature history or required "
            "sensitive/unavailable checks; medium otherwise."
        ),
    }
