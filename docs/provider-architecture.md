# Capability-based providers

ObservationProvider remains the Phase 1 observation contract. CapabilityProvider is
the optional capability-reporting protocol: a provider need not implement every
acquisition operation. NexLev adds an allowlisted explicit REST client plus external
EvidenceBatch ingestion; it does not replace the official YouTube observation pipeline.

Each capability has available, not_configured, not_documented_for_rest,
orchestrator_only, plan_restricted, owner_authorization_required, quota_limited,
temporarily_unavailable or unsupported state as applicable. REST and orchestrated
access are independent. Configuration-only status never probes network or writes DB.
Runtime client calls can report per-route failures/probed state without changing
official YouTube capabilities. No-key or failing NexLev leaves official-only operation
available. See nexlev-api-contract.md for current documented routes and absence findings.

Provider trust/retention/route clocks are explicit, with official hydration for public
facts and local adjudication for eligibility/cohorts. Provider history is auxiliary;
financial estimates are firewalled; selected discovery cannot define population rates.
See nexlev-integration.md and nexlev-trust-model.md for API, persistence and lifecycle.
