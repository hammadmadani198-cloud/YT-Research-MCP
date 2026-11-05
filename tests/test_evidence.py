from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from youtube_niche_mcp.domain.evidence import NumericEvidence
from youtube_niche_mcp.domain.provenance import Provenance
from youtube_niche_mcp.domain.states import EvidenceState

UNKNOWN_STATES = [
    state
    for state in EvidenceState
    if state
    not in {EvidenceState.AVAILABLE, EvidenceState.APPROXIMATE, EvidenceState.PARTIAL_COVERAGE}
]


@pytest.mark.parametrize("state", UNKNOWN_STATES)
def test_unknown_is_null_and_never_zero(state, provenance):
    evidence = NumericEvidence(state=state, reason="Unobserved", provenance=provenance)
    assert evidence.value is None
    assert evidence.model_dump()["value"] is None
    with pytest.raises(ValidationError):
        NumericEvidence(state=state, value=0, reason="Unobserved", provenance=provenance)


def test_observed_zero_is_distinct_from_missing(provenance):
    evidence = NumericEvidence(state="available", value=0, reason="Observed", provenance=provenance)
    assert evidence.value == 0
    assert evidence.state == EvidenceState.AVAILABLE


def test_pending_stays_pending_after_serialization(provenance):
    item = NumericEvidence(state="pending_maturity", reason="Not yet mature", provenance=provenance)
    restored = NumericEvidence.model_validate_json(item.model_dump_json())
    assert restored.state == EvidenceState.PENDING_MATURITY
    assert restored.value is None


@pytest.mark.parametrize("state", ["available", "approximate"])
def test_available_requires_value(state, provenance):
    with pytest.raises(ValidationError):
        NumericEvidence(state=state, reason="Missing", provenance=provenance)


@pytest.mark.parametrize("value", [True, "0", float("nan"), float("inf")])
def test_invalid_numeric_values(value, provenance):
    with pytest.raises(ValidationError):
        NumericEvidence(state="available", value=value, reason="Bad input", provenance=provenance)


def test_publication_is_distinct_from_observation(provenance):
    assert provenance.published_at != provenance.observed_at
    assert provenance.maturity_at < provenance.observed_at
    assert provenance.available_at == provenance.observed_at


def test_naive_datetime_rejected(provenance):
    values = provenance.model_dump()
    values["observed_at"] = datetime(2026, 10, 2)
    with pytest.raises(ValidationError):
        Provenance.model_validate(values)


def test_observation_cannot_be_made_available_retroactively(provenance):
    values = provenance.model_dump()
    values["available_at"] = provenance.observed_at - timedelta(days=1)
    with pytest.raises(ValidationError, match="available_at"):
        Provenance.model_validate(values)


def test_maturity_cannot_precede_publication(provenance):
    values = provenance.model_dump()
    values["maturity_at"] = provenance.published_at - timedelta(days=1)
    with pytest.raises(ValidationError, match="maturity_at"):
        Provenance.model_validate(values)
