"""F17 runs after synthesis; cannot access or modify decisions/confidence."""

from decimal import Decimal

from youtube_niche_mcp.decision.synthesis import number


def sorting_index(metrics, config, *, essential_evidence_complete=True):
    if config is None:
        return {"state": "disabled", "value": None, "sorting_only": True}
    rows, included, excluded = [], [], []
    for d in config.dimensions:
        raw = number(metrics.get(d.formula_id))
        normalized = None
        unclipped = None
        if raw is not None:
            unclipped = (raw - d.low) / (d.high - d.low)
            normalized = min(Decimal(1), max(Decimal(0), unclipped))
            if d.direction == "lower":
                normalized = 1 - normalized
            included.append(d.formula_id)
        else:
            excluded.append(d.formula_id)
        rows.append(
            {
                **d.model_dump(mode="json"),
                "raw": raw,
                "normalized": normalized,
                "clipped": unclipped is not None and not 0 <= unclipped <= 1,
                "missing": raw is None,
            }
        )
    insufficient = (
        not essential_evidence_complete
        or not included
        or any(r["missing"] and r["essential"] for r in rows)
        or (excluded and not config.allow_partial)
    )
    weight = sum((Decimal(r["weight"]) for r in rows if not r["missing"]), Decimal(0))
    value = (
        None
        if insufficient
        else sum(
            (r["normalized"] * Decimal(r["weight"]) for r in rows if not r["missing"]), Decimal(0)
        )
        / weight
        * 100
    )
    return {
        "state": "insufficient_dimensions"
        if insufficient
        else "partial_index"
        if excluded
        else "sorting_index_available",
        "value": value,
        "included": included,
        "excluded": excluded,
        "dimensions": rows,
        "included_weight_denominator": weight,
        "config": config.model_dump(mode="json"),
        "sorting_only": True,
        "essential_evidence_complete": essential_evidence_complete,
        "warning": "Research sorting only; never approval, risk override or confidence",
    }


def sort_runs(results):
    """Only explicit available indices sort; tie breaker is immutable run ID."""
    return sorted(
        results,
        key=lambda r: (
            r["value"] is None,
            -Decimal(r["value"]) if r["value"] is not None else 0,
            r["run_id"],
        ),
    )
