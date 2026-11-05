"""Pure multi-axis research states. Sorting has no access to this function."""

from decimal import Decimal, InvalidOperation

from youtube_niche_mcp.decision.models import AXES

UNKNOWN = {"unknown", "source_conflict", "pending_maturity", "policy_permission_required"}


def usable(metric):
    return (
        metric is not None
        and metric.state not in UNKNOWN
        and not metric.state.startswith("insufficient")
    )


def number(metric, path=()):
    if not usable(metric):
        return None
    value = metric.details if path else metric.value
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def grade(value, rule):
    if value is None:
        return "unknown"
    positive = value >= rule.threshold if rule.direction == "at_least" else value <= rule.threshold
    return "supports" if positive else "concern"


def assemble(metrics, rubric, *, policy_state, classifications=None):
    """No hidden numeric thresholds; every numeric judgment uses the caller's rubric."""
    axes = {}
    for name, formula_ids in AXES.items():
        source = [metrics[f] for f in formula_ids if f in metrics]
        rules = [r for r in rubric.rules if r.formula_id in formula_ids]
        judgments = [
            {
                "formula_id": r.formula_id,
                "path": list(r.path),
                "raw": number(metrics.get(r.formula_id), r.path),
                "state": grade(number(metrics.get(r.formula_id), r.path), r),
                "direction": r.direction,
                "threshold": r.threshold,
                "reference": r.reference,
            }
            for r in rules
        ]
        states = {j["state"] for j in judgments}
        state = (
            "mixed"
            if {"supports", "concern"} <= states
            else "concern"
            if "concern" in states
            else "supports"
            if states == {"supports"}
            else "unknown"
            if judgments
            else "observed_ungraded"
            if any(usable(m) for m in source)
            else "unknown"
        )
        axes[name] = {
            "state": state,
            "judgments": judgments,
            "source_metrics": [
                {
                    "run_id": m.analysis_run_id,
                    "formula_id": m.formula_id,
                    "state": m.state,
                    "value": m.value,
                    "details": m.details,
                }
                for m in source
            ],
            "annotation_ids": sorted(
                {i for m in source for i in m.details.get("annotation_confidences", {})}
            ),
            "warnings": sorted({w for m in source for w in m.warnings}),
        }

    def detail(fid):
        m = metrics.get(fid)
        return m.details if usable(m) else {}

    rights = detail("rights_legal").get("assets", [])
    factual = detail("factual_editorial").get("reviews", [])
    policy = detail("platform_policy").get("snapshots", [])
    production = detail("F16").get("cases", [])
    risk = []
    if any(a.get("dependency") == "high" or a.get("clearance") != "verified" for a in rights):
        risk.append("rights_clearance_dependency")
        axes["rights"]["state"] = "concern"
    elif rights:
        axes["rights"]["state"] = "supports"
    if any(
        a.get("verification_burden") in {"high", "unknown"}
        or a.get("correction_burden") in {"high", "unknown"}
        or a.get("allegation_verification_needed")
        or a.get("disputed_claims")
        or a.get("volatile")
        for a in factual
    ):
        risk.append("factual_verification_dependency")
        axes["factual_risk"]["state"] = "concern"
    elif factual:
        axes["factual_risk"]["state"] = "supports"
    if any(a.get("review_flags") for a in policy):
        risk.append("platform_policy_review_dependency")
        axes["platform_policy"]["state"] = "concern"
    elif policy and policy_state == "fresh":
        axes["platform_policy"]["state"] = "supports"
    if policy_state != "fresh":
        risk.append("policy_refresh_required")
        axes["platform_policy"]["state"] = "unknown"
    if production and all(p.get("complete_task_inventory") for p in production):
        if axes["production"]["state"] == "observed_ungraded":
            axes["production"]["state"] = "supports"
    elif production:
        axes["production"]["state"] = "unknown"
    if detail("source_to_story").get("checked_credible_accessible_ids"):
        axes["sources"]["state"] = (
            "concern"
            if detail("source_to_story").get("single_fragile_source_dependency")
            else "supports"
        )
    gaps = detail("content_gaps").get("gaps", [])
    if gaps:
        axes["differentiation"]["state"] = (
            "supports" if any(g["state"] == "supported_gap" for g in gaps) else "observed_ungraded"
        )
    pilot = detail("F23")
    if (
        pilot.get("cash_limit_exceeded")
        or pilot.get("hour_limit_exceeded")
        or pilot.get("runway_covers_K_maturity") is False
    ):
        axes["pilot_downside"]["state"] = "concern"

    unknowns = [
        name
        for name in rubric.required_axes
        if axes[name]["state"] in {"unknown", "observed_ungraded"}
    ]
    history = {f: metrics[f].state if f in metrics else "missing" for f in rubric.required_history}
    immature = [
        f
        for f in rubric.required_history
        if not usable(metrics.get(f)) or metrics[f].state != "available"
    ]
    if classifications and any(c["verified"] < c["denominator"] for c in classifications.values()):
        unknowns.append("critical_classification_uncertainty")
    supports = [a for a, d in axes.items() if d["state"] == "supports"]
    concerns = [a for a, d in axes.items() if d["state"] in {"concern", "mixed"}]
    if risk:
        state = "high_rights_or_policy_dependency"
    elif axes["production"]["state"] == "concern":
        state = "high_execution_burden"
    elif unknowns:
        state = "insufficient_evidence"
    elif immature:
        state = "history_immature"
    elif concerns:
        state = (
            "weak_under_goal"
            if axes["performance"]["state"] == "concern"
            and axes["ordinary_floor"]["state"] == "concern"
            else "mixed_evidence"
        )
    else:
        state = "supported"
    return {
        "state": state,
        "axes": axes,
        "supports": supports,
        "concerns": concerns,
        "unknowns": sorted(unknowns),
        "history_maturity": {
            "required": history,
            "immature": immature,
            "available_required": len(history) - len(immature),
            "required_count": len(history),
            "measurements": {
                f: {
                    "state": m.state,
                    "mature": m.mature,
                    "pending": m.pending,
                    "unknown": m.unknown,
                    "included": m.included,
                    "numerator": m.numerator,
                    "denominator": m.denominator,
                    "details": m.details,
                }
                for f in ("F10", "F11", "F12", "F13", "F20", "F21")
                if (m := metrics.get(f)) is not None
            },
            "scope": (
                "Maturity of retained panels and age-matched observations; "
                "absent windows are not inferred"
            ),
        },
        "risk_gates": risk,
        "insufficiency_gates": sorted(unknowns),
        "meaning": (
            "Evidence supports further consideration under tested assumptions; not creator success"
        ),
    }


def compare(base, variant, rubric):
    changes = []
    for rule in rubric.rules:
        left, right = (
            number(base.get(rule.formula_id), rule.path),
            number(variant.get(rule.formula_id), rule.path),
        )
        flip = grade(left, rule) != grade(right, rule) and left is not None and right is not None
        delta = right - left if left is not None and right is not None else None
        material = flip or (
            delta is not None
            and rule.material_tolerance is not None
            and abs(delta) > rule.material_tolerance
        )
        changes.append(
            {
                "formula_id": rule.formula_id,
                "path": list(rule.path),
                "base": left,
                "variant": right,
                "delta": delta,
                "rule_flip": flip,
                "material": material,
            }
        )
    return changes
