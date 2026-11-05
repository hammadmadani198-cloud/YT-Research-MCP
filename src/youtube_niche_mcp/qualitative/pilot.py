"""C93/F23 declared loss/time exposure and evidence maturity, with no income model."""

from datetime import timedelta
from decimal import Decimal


def pilot_downside(profile):
    if profile is None:
        return {"state": "creator_input_required", "value": None, "income_assumed": False}
    releases = sorted(profile.releases, key=lambda r: (r.publication_at, r.release_id))
    planned = [(r, r.publication_at + timedelta(days=r.delay_days)) for r in releases]
    release_hours = sum((t.hours for r in releases for t in r.tasks), Decimal(0))
    release_cash = sum((t.cash for r in releases for t in r.tasks), Decimal(0))
    hours = profile.setup_hours + release_hours + profile.evaluation_hours + profile.overhead_hours
    cash = profile.setup_cash + release_cash + profile.contracted_overhead_cash
    outflows = [
        (profile.setup_at, "setup", profile.setup_cash),
        (profile.overhead_at, "contracted_overhead", profile.contracted_overhead_cash),
    ]
    outflows.extend(
        (r.cash_outflow_at or date, r.release_id, sum((t.cash for t in r.tasks), Decimal(0)))
        for r, date in planned
    )
    cumulative, schedule = Decimal(0), []
    for date, label, amount in sorted(outflows, key=lambda item: (item[0], item[1])):
        cumulative += amount
        schedule.append(
            {
                "at": date.isoformat(),
                "outflow": amount,
                "label": label,
                "cumulative_no_income_deficit": cumulative,
            }
        )
    maturity = sorted(date + timedelta(days=profile.outcome_age_days) for _, date in planned)
    first, complete = maturity[0], maturity[-1]
    count = len(releases)
    return {
        "state": "declared_scenario",
        "value": cash,
        "currency": profile.currency,
        "setup_cash": profile.setup_cash,
        "release_cash": release_cash,
        "contracted_overhead_cash": profile.contracted_overhead_cash,
        "setup_hours": profile.setup_hours,
        "release_hours": release_hours,
        "evaluation_hours": profile.evaluation_hours,
        "overhead_hours": profile.overhead_hours,
        "planned_hours": hours,
        "planned_cash_loss": cash,
        "planned_attempts": count,
        "peak_no_income_deficit": cumulative,
        "outflow_schedule": schedule,
        "cash_limit_exceeded": cash > profile.cash_limit
        if profile.cash_limit is not None
        else None,
        "hour_limit_exceeded": hours > profile.hour_limit
        if profile.hour_limit is not None
        else None,
        "first_mature_not_before": first.isoformat(),
        "complete_K_mature_not_before": complete.isoformat(),
        "runway_covers_K_maturity": profile.runway_until >= complete
        if profile.runway_until
        else None,
        "maturity_dates": [
            {
                "release_id": r.release_id,
                "publication_at": date.isoformat(),
                "mature_not_before": (date + timedelta(days=profile.outcome_age_days)).isoformat(),
            }
            for r, date in planned
        ],
        "evidence_requirements": {
            "F7": {
                "required": "documented hit/anchor followed by five eligible future uploads "
                "at comparable ages",
                "planned_upload_count": count,
                "history_state": "unresolved_anchor_and_followup_history",
            },
            "F19": {
                "required": "ten comparable attempts per entrant plus frozen "
                "entrant/independence evidence",
                "planned_upload_count": count,
                "ten_attempts_planned": count >= 10,
                "history_state": "unresolved_entrant_history",
            },
            "F10_F13": {
                "required": "repeated prospective comparable snapshots; "
                "current totals do not reconstruct history",
                "history_state": "unresolved_repeated_snapshots",
            },
            "F20": {
                "required": "pre/post anchor history and stable comparable panel",
                "history_state": "unresolved_pre_post_history",
            },
            "F21": {
                "required": "multiple comparable observation windows and stable panel",
                "history_state": "unresolved_multiwindow_history",
            },
        },
        "income_assumed": False,
        "break_even_criteria_reference": profile.break_even_criteria_reference,
        "limitations": [
            "Declared exposure and evidence runway are not a success or income forecast",
            "Release costs use explicit cash outflow dates when supplied, "
            "otherwise delayed publication dates; revise for earlier commitments",
            "Maturity dates do not guarantee capture availability or satisfy history prerequisites",
        ],
    }
