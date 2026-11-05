"""Request boundary: existing storage, fixed errors, explicit acquisition and bounded results."""

import sqlite3
from contextlib import contextmanager

import anyio
from pydantic import ValidationError

from youtube_niche_mcp.analysis.repository import AnalysisUnavailable
from youtube_niche_mcp.db.migrations import MigrationError, validate_migrations
from youtube_niche_mcp.history.repository import HistoryRepository
from youtube_niche_mcp.services.safety import safe_json
from youtube_niche_mcp.tools import competitors, views, watches
from youtube_niche_mcp.tools.acquisition import acquire
from youtube_niche_mcp.tools.errors import PublicError, failure
from youtube_niche_mcp.tools.research import ResearchEngine
from youtube_niche_mcp.tools.serialization import bounded


class PublicSurface:
    def __init__(self, settings, *, history=None, youtube_transport=None, nexlev_transport=None):
        self.settings, self.history = settings, history
        self.youtube_transport, self.nexlev_transport = youtube_transport, nexlev_transport
        self.secrets = tuple(
            k.get_secret_value() for k in (settings.youtube_api_key, settings.nexlev_api_key) if k
        )

    @contextmanager
    def repository(self, write):
        if self.history is not None:
            yield self.history
            return
        # mode=rw/ro cannot create the database. No migration on any tool call.
        if not self.settings.db_path.is_file():
            raise PublicError("insufficient_evidence")
        connection = sqlite3.connect(
            f"{self.settings.db_path.resolve().as_uri()}?mode={'rw' if write else 'ro'}",
            uri=True,
            timeout=self.settings.db_timeout_seconds,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        if not write:
            connection.execute("PRAGMA query_only=ON")
        try:
            applied = validate_migrations(connection)
            if len(applied) < 6:
                raise PublicError("schema_upgrade_required")
            yield HistoryRepository(connection, secrets=self.secrets)
            if connection.in_transaction:
                connection.commit()
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    async def dispatch(self, name, request):
        quota, warnings = [], []
        try:
            safe_json(request.model_dump(mode="json"), self.secrets)
            acquisition = getattr(request, "acquisition", None)
            mutation = "watch" in name and request.action in {"create", "update", "disable"}
            write = (
                name == "youtube_niche_research"
                or mutation
                or bool(acquisition and acquisition.refresh)
            )
            with self.repository(write) as history:
                safe_json(request.model_dump(mode="json"), history.secrets)
                engine = ResearchEngine(history)
                if acquisition:
                    with anyio.fail_after(90):
                        quota, warnings = await acquire(
                            history,
                            self.settings,
                            request,
                            youtube_transport=self.youtube_transport,
                            nexlev_transport=self.nexlev_transport,
                            usage=quota,
                            warnings=warnings,
                        )
                if name == "youtube_niche_research":
                    decision, reused = engine.research(request)
                    result = views.overview(
                        engine,
                        decision.run.run_id,
                        reused=reused,
                        request=request,
                        sorting=request.sorting,
                    )
                    if request.history_preference == "required" and result.data[
                        "history_maturity"
                    ].get("immature"):
                        warnings.append(
                            "Required historical dimensions are immature; no "
                            "current-count backfill."
                        )
                    if request.geographic_context:
                        result.data["requested_geographic_context"] = request.geographic_context
                        warnings.append(
                            "Requested geography is planning context, not observed "
                            "audience location."
                        )
                elif name == "youtube_niche_discover":
                    result = views.discover(engine, request)
                elif name == "youtube_niche_compare":
                    result = views.compare(engine, request)
                elif name == "youtube_competitor_analyze":
                    result = competitors.analyze(engine, request)
                elif name == "youtube_competitor_compare":
                    result = competitors.compare(engine, request)
                elif "watch" in name:
                    result = watches.manage(
                        history,
                        "niche" if name == "youtube_niche_watchlist" else "competitor",
                        request,
                        lambda bid: bid in engine.boundaries(),
                    )
                else:
                    result = views.overview(
                        engine,
                        request.research_id,
                        focus=name.removeprefix("youtube_niche_"),
                        request=request,
                    )
                result = result.model_copy(
                    update={
                        "quota": quota
                        or [
                            {
                                "provider": "youtube",
                                "requests": 0,
                                "recorded_assumed_cost": 0,
                                "quota_state": "no_requests",
                            },
                            {
                                "provider": "nexlev",
                                "requests": 0,
                                "actual_charged_cost": 0,
                                "quota_state": "no_requests",
                            },
                        ],
                        "warnings": [*result.warnings, *warnings],
                        "capabilities": {
                            "evidence_mode": "explicit_refresh"
                            if acquisition and acquisition.refresh
                            else "stored_only",
                            "youtube": "configured"
                            if self.settings.youtube_api_key
                            else "not_configured",
                            "nexlev": "configured"
                            if self.settings.nexlev_api_key
                            else "not_configured",
                            "semantic_rest": "orchestrator_only",
                            "scheduler": "absent",
                        },
                    }
                )
                return bounded(result, (*self.secrets, *history.secrets))
        except PublicError as exc:
            result = failure(exc.state)
        except AnalysisUnavailable as exc:
            state = {
                "policy_permission_required": "permission_required",
                "insufficient_sample": "insufficient_evidence",
                "insufficient_history": "history_unavailable",
                "source_conflict": "source_conflict",
            }.get(exc.state, "insufficient_evidence")
            result = failure(state)
        except (MigrationError, PermissionError):
            result = failure("database_unavailable")
        except (ValueError, ValidationError, TypeError):
            result = failure("invalid_input")
        except TimeoutError:
            result = failure("internal_error")
        except sqlite3.Error as exc:
            code = getattr(exc, "sqlite_errorcode", 0) & 255
            result = failure(
                "database_busy"
                if code in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}
                else "database_unavailable"
            )
        except Exception:
            result = failure("internal_error")
        return result.model_copy(update={"quota": quota, "warnings": warnings})
