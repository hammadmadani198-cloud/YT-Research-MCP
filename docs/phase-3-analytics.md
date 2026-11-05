# Offline core analytics — Phase 3

Version 0.4.0 is the next minor release after the 0.3.5 provider bridge: it adds an
internal analytics API, a versioned formula contract and additive schema v5.
No dependencies changed. The public research tool catalog remains 0 registered / 15 planned.

Implementation-authoritative equations, inputs, denominators, edge cases and source
precedence: [phase-3-formula-contract.md](phase-3-formula-contract.md). Only F1–F9,
failure floor, F19 and F22 are available. They describe frozen evidence, not niche
quality, profitability, ranking, recommendation or a population success probability.

## Architecture and invocation

`analysis/models.py` defines explicit options, frozen input frames, resolved outcomes,
manifests and results. `repository.py` bulk reads existing cohort/history/taxonomy/group
tables. `outcomes.py` owns maturity, canonical official count/precision, retention,
conflict and known-at-time rules. `baselines.py`, `floor.py`, `repeatability.py`,
`breadth.py`, `concentration.py`, `exposure.py` and `bounds.py` share those outcomes.
`numerics.py` uses 28-digit Decimal ratios/logs and explicit type-7 quantiles.
`service.py` computes a metric bundle and optionally persists it. No formula module
imports HTTP clients, calls providers, runs network hydration or rebuilds membership.

```python
from youtube_niche_mcp.analysis.models import AnalysisOptions
from youtube_niche_mcp.analysis.service import AnalysisService

profile = AnalysisOptions.model_validate_json(profile_json)
bundle = AnalysisService(history).analyze(
    "frozen-entrant-frame", profile, video_cohort_id="frozen-eligible-video-frame"
)
```

Channel/entrant runs require an eligible-video frame with exactly the same Boundary.
Video-only runs use that cohort directly. All frames must have been frozen by cutoff;
the cutoff cannot be in the future. F1 baseline and rule-anchor landmarks require
the video membership frame already known at the landmark. Topic/group evidence is
resolved at frozen clocks; later provider classifications cannot revise membership.
Original discovery occurrences remain elsewhere; canonical membership keys control N.

Explicit development CLI (PowerShell from the repository):

```powershell
& .\.venv\Scripts\python.exe -m youtube_niche_mcp analysis formulas
& .\.venv\Scripts\python.exe -m youtube_niche_mcp analysis run --cohort ENTRY_ID --video-cohort VIDEO_ID --options profile.json
& .\.venv\Scripts\python.exe -m youtube_niche_mcp analysis inspect RUN_ID
```

`run` needs an existing explicitly migrated DB and stored frames; `inspect` opens
read-only. `formulas`, startup, status and normal verify need no data/network and do
not run analytics. CLI failures suppress untrusted exception inputs/secrets; known
structured unavailable-frame errors report a state. Library `AnalysisUnavailable.state`
provides the same structured policy/sample insufficiency when a frame cannot be read.

Required profile fields: cutoff, age_days, tolerance_seconds, goal, low_threshold,
own_minimum, peer_video_minimum, peer_channel_minimum, pooling_k, breadth_k,
classification_minimum, exposure_days and first_k (5/10/null). Optional candidate_id
requires baseline_cutoff; explicit anchor_id or anchor_channel_id with anchor_cutoff
selects F7. The declared missing, independence, quantile and observation policies are
versioned fields, never hidden defaults. No universal view goal is supplied.

`finite_frame_reference` is a reviewed declaration that the researched denominator
is enumerated; an open discovery feed cannot establish it. `coverage` lists reviewed
channel catalog coverage through a known past time, its available_at and evidence
reference. Lack of coverage never turns a no-hit entrant into a known miss. These are
trusted research-profile declarations, not independently certified completeness or
a claim to have enumerated YouTube. Provider winner feeds alone cannot create entrant
denominators. F19 requires a frozen entrant cohort.

## Outcomes, metrics and retention

An exact target outcome requires an official video count observed in the forward
age/tolerance window, available by cutoff and retained at actual read time. Current
lifetime views outside that window are insufficient history. Provider outlier/VPH/
averages/RPM/revenue/monetization/quality/geography and auxiliary channel history never
become those counts. Counts remain integers; unrounded Decimal values serialize as
strings with raw numerators and denominators. Pending is not a miss; unknown is not 0.

Valid earlier age-matched evidence survives a later deleted/private outcome while
still permitted. Otherwise unavailable content stays unknown. Contemporaneous official
count disagreement and frozen identity conflicts produce source_conflict. Approximate
and rounded counts are not silently upgraded to exact outcomes. Expiry/permission
revocation gates both new computation and reading saved derivatives.

Each result records formula/version/run/cohort/Boundary/cutoff/age/tolerance/goal,
resolved-video sample counts (`sample_unit=video_outcome`), ownership diagnostics,
the formula's actual numerator/denominator/value/unit/state, warnings and input hash.
Channel/group denominators, contributing baseline counts and follow-up position counts
are separately named in result details; they are never substituted for upload N.
Unavailable unconfigured F1/F2/F7 results are included explicitly in a bundle.

Schema v5 adds exactly analysis_runs, analysis_metric_results and analysis_outcomes,
with append-only update triggers and cascading deletion from existing cohort frames.
No duplicate sources/history/conflicts/cohorts/cache tables. Runs hash formula/software
version, full options and frozen input identity; creation time is audit metadata only.
Identical replay returns the saved manifest/results; changed inputs/options create a
new identity. Historical runs retain their original results until expiry; later
evidence cannot rewrite them. Read revalidates retained dependency IDs and permissions.
Explicit purge removes expired runs/results/outcomes before historical inputs.
No derived cache is used. No raw titles/comments/transcripts are copied into analyses.

Each run is conservatively bounded by every loaded relevant retained input, including
metadata needed for canonical publication/channel identity. Extended statistics-only
permission does not revive expired identity text or an expired frozen cohort. A frame
without retained publication identity becomes insufficient instead of reconstructed.
No extended permission is configured in the real DB; synthetic tests explicitly
record scoped fixture permissions. Analysis does not confer storage authorization.

## Formula and evidence limits

F2 follows log-space shrinkage, with a channel-balanced peer log median and video-
weighted diagnostic. The 1,750 raw-median example is not substituted for F2. F5 first
calculates each channel's Q25, then the median of those floors. F7 reports full R5/R10
only for complete mature, positioned follow-ups; partial known-only summaries and
absent/unpositioned states remain separate. Grouped F19 uses the earliest frozen
member entry clock and one combined chronological first-K exposure for sister channels.
Raw-channel F4 and creator-unit F19 denominators are explicitly distinguished.

F8 counts documented independent units; unknown ownership is provisional channel
coverage. Multi-label topics count for breadth, with equal fractional reach allocation
only for named topic HHI. Unclassified/conflicted mass is exposed; coverage gates topic
results. F9 includes channel, creator-unit and topic views plus top-channel-removal
diagnostic without good/bad labels. F22 is [h/n,(h+u)/n] for the declared finite frame;
it is not a confidence interval or a probability for undiscovered entrants.

Synthetic A–H fixtures demonstrate broad/moderate performance, viral-heavy weak floor,
one-hit entrants, stopped/low/zero output, missing history, sister groups, concentrated
topics and broad topics. Deep-size test uses 100 channels / 3,000 videos and a fixed
bulk SELECT budget, without fragile timing assertions. These are bias tests, not
fresh empirical YouTube facts. Current tests do not validate predictive usefulness.

STOP at Phase 3. F10–F18, F20–F21 and F23 remain unimplemented. Exact Phase 4 scope:
F10 historical velocity/acceleration, F11 demand momentum, F12 observed supply change,
F13 older-catalog contribution, F20 ordinary post-hit baseline change and F21 winner
replacement. Qualitative/production/risk, robustness/final decision, public tools and
integrated release remain later phases.
