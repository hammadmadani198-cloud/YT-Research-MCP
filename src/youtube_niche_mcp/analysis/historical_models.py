"""Immutable historical options embedded in the existing analysis run manifest."""

from datetime import timedelta
from typing import Literal

from pydantic import AwareDatetime, Field, JsonValue, model_validator

from youtube_niche_mcp.eligibility.models import FrozenModel

HISTORY_VERSION = "phase4-v1"
HISTORY_FORMULAS = ("F10", "F11", "F12", "F13", "F20", "F21")


class Window(FrozenModel):
    start: AwareDatetime
    end: AwareDatetime

    @model_validator(mode="after")
    def ordered(self):
        if self.start >= self.end:
            raise ValueError("Positive explicit half-open window required")
        return self

    @property
    def seconds(self):
        return (self.end - self.start).total_seconds()


class Panel(FrozenModel):
    cohort_id: str
    video_cohort_id: str | None = None
    cutoff: AwareDatetime
    publication: Window
    age_days: int = Field(gt=0, strict=True)
    goal: int = Field(ge=0, strict=True)
    tolerance_seconds: int = Field(default=0, ge=0, le=604800, strict=True)
    discovery_run_ids: tuple[str, ...] = ()
    capability_mode: str = Field(min_length=1)
    provider_source_version: str = Field(min_length=1)
    coverage_reference: str = Field(min_length=1)
    coverage_epoch: str = Field(min_length=1)
    creator_group_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def known(self):
        if self.publication.end > self.cutoff:
            raise ValueError("Publication window cannot follow historical cutoff")
        if len(set(self.discovery_run_ids)) != len(self.discovery_run_ids):
            raise ValueError("Unique discovery runs required")
        return self


class HistoricalOptions(FrozenModel):
    historical_version: Literal["phase4-v1"] = HISTORY_VERSION
    cutoff: AwareDatetime
    age_days: int = Field(gt=0, strict=True)
    goal: int = Field(ge=0, strict=True)
    tolerance_seconds: int = Field(default=0, ge=0, le=604800, strict=True)
    older: Panel | None = None
    newer: Panel | None = None
    observation_window: Window | None = None
    catalog_window: Window | None = None
    catalog_start_cohort: str | None = None
    old_age_days: int = Field(default=90, ge=90, strict=True)
    pre_anchor_cohort: str | None = None
    anchor_id: str | None = None
    anchor_channel_id: str | None = None
    anchor_at: AwareDatetime | None = None
    first_k: Literal[5, 10] = 5
    recent_entry: Window | None = None
    creator_group_version: str = Field(min_length=1)
    provider_history_policy: Literal["exclude", "separate_auxiliary"] = "exclude"
    missing_policy: Literal["never_zero_never_miss"] = "never_zero_never_miss"
    annotation: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def clocks(self):
        for w in (self.observation_window, self.catalog_window, self.recent_entry):
            if w and w.end > self.cutoff:
                raise ValueError("Historical window cannot follow cutoff")
        if self.catalog_window and self.catalog_window.seconds < timedelta(days=30).total_seconds():
            raise ValueError("F13 requires at least 30 days of actual tracking")
        if self.catalog_window and not self.catalog_start_cohort:
            raise ValueError("F13 requires a catalog frame frozen at interval start")
        if self.anchor_at and (self.anchor_at > self.cutoff or not self.pre_anchor_cohort):
            raise ValueError("F20 requires a known landmark and frozen pre frame")
        if (self.anchor_id or self.anchor_channel_id) and not self.anchor_at:
            raise ValueError("Anchor requires declared confirmed-hit landmark")
        for panel in (self.older, self.newer):
            if panel and panel.cutoff > self.cutoff:
                raise ValueError("Panel cannot use future information")
        if self.older and self.newer and self.older.publication.end > self.newer.publication.start:
            raise ValueError("Publication windows must be chronological and non-overlapping")
        return self
