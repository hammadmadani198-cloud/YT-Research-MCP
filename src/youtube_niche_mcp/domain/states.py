from enum import StrEnum


class EvidenceState(StrEnum):
    AVAILABLE = "available"
    APPROXIMATE = "approximate"
    PARTIAL_COVERAGE = "partial_coverage"
    PENDING_MATURITY = "pending_maturity"
    INSUFFICIENT_SAMPLE = "insufficient_sample"
    INSUFFICIENT_HISTORY = "insufficient_history"
    CLASSIFICATION_UNKNOWN = "classification_unknown"
    SOURCE_CONFLICT = "source_conflict"
    POLICY_PERMISSION_REQUIRED = "policy_permission_required"
    OWNER_AUTHORIZATION_REQUIRED = "owner_authorization_required"
    NOT_PUBLICLY_AVAILABLE = "not_publicly_available"


class SourceKind(StrEnum):
    PUBLIC_API = "public_api"
    PROVIDER = "provider"
    HUMAN_ANNOTATION = "human_annotation"
    DERIVED = "derived"
    CREATOR_INPUT = "creator_input"


class Precision(StrEnum):
    EXACT = "exact"
    ROUNDED = "rounded"
    APPROXIMATE = "approximate"
    UNKNOWN = "unknown"
