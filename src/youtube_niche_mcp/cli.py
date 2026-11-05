import argparse
import asyncio
import json
import sqlite3
import sys
from pathlib import Path

from youtube_niche_mcp import __version__
from youtube_niche_mcp.config import ConfigurationError, Settings
from youtube_niche_mcp.db.connection import connect
from youtube_niche_mcp.db.migrations import MigrationError, migrate
from youtube_niche_mcp.db.status import integrity, status
from youtube_niche_mcp.logging import configure_logging
from youtube_niche_mcp.services.capabilities import capabilities, operational_status
from youtube_niche_mcp.services.catalog import PLANNED_TOOLS
from youtube_niche_mcp.services.verification import check_mcp, verify


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="youtube-niche-mcp")
    root.add_argument("--version", action="version", version=__version__)
    root.add_argument("--db", type=Path, help="Override SQLite path (put before the command)")
    subcommands = root.add_subparsers(dest="command", required=True)
    subcommands.add_parser("verify", help="Non-destructive offline foundation checks")
    subcommands.add_parser("migrate", help="Explicitly initialize/apply database migrations")
    subcommands.add_parser("serve", help="Run the local MCP server on stdio")
    for command, operations in (
        ("db", ("status", "integrity")),
        ("tool", ("list",)),
        ("config", ("check",)),
        ("api", ("capability",)),
        ("history", ("status", "purge-expired")),
        ("snapshot", ("status",)),
        ("eligibility", ("rules",)),
        ("taxonomy", ("status",)),
        ("cohort", ("status",)),
        ("provider", ("status", "capabilities", "quota", "contract", "cache-status")),
    ):
        group = subcommands.add_parser(command)
        nested = group.add_subparsers(dest="operation", required=True)
        for operation in operations:
            nested.add_parser(operation)
    analysis = subcommands.add_parser("analysis")
    operations = analysis.add_subparsers(dest="operation", required=True)
    operations.add_parser("formulas")
    inspect = operations.add_parser("inspect")
    inspect.add_argument("run_id")
    run = operations.add_parser("run")
    run.add_argument("--cohort", required=True)
    run.add_argument("--video-cohort")
    run.add_argument("--options", type=Path, required=True)
    historical = operations.add_parser("historical")
    historical.add_argument("--cohort", required=True)
    historical.add_argument("--video-cohort")
    historical.add_argument("--options", type=Path, required=True)
    qualitative = operations.add_parser("qualitative")
    qualitative.add_argument("--cohort", required=True)
    qualitative.add_argument("--video-cohort")
    qualitative.add_argument("--options", type=Path, required=True)
    annotate = operations.add_parser("annotate")
    annotate.add_argument("--input", type=Path, required=True)
    decision = subcommands.add_parser("decision", help="Internal offline robustness/synthesis")
    decision_ops = decision.add_subparsers(dest="operation", required=True)
    decision_run = decision_ops.add_parser("run")
    decision_run.add_argument("--options", type=Path, required=True)
    decision_inspect = decision_ops.add_parser("inspect")
    decision_inspect.add_argument("run_id")
    decision_ops.add_parser("f17-config")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        settings = Settings.from_env()
        if args.db is not None:
            settings = settings.model_copy(update={"db_path": args.db})
        configure_logging(settings)
        if args.command == "serve":
            from youtube_niche_mcp.server import create_server

            create_server(settings).run(transport="stdio")
            return 0
        if args.command == "verify":
            result = verify(settings)
        elif args.command == "decision":
            from youtube_niche_mcp.analysis.repository import AnalysisUnavailable
            from youtube_niche_mcp.decision.models import DecisionOptions, SortConfig
            from youtube_niche_mcp.decision.service import DecisionService
            from youtube_niche_mcp.history.repository import HistoryRepository

            if args.operation == "f17-config":
                result = {
                    "ok": True,
                    "sorting_only": True,
                    "schema": SortConfig.model_json_schema(),
                }
            else:
                if not settings.db_path.exists():
                    raise MigrationError("Explicitly migrate before decision analysis")
                with connect(settings.db_path, read_only=args.operation == "inspect") as connection:
                    if status(connection)["migration_state"] != "current":
                        raise MigrationError("Explicitly migrate before decision analysis")
                    service = DecisionService(HistoryRepository(connection))
                    try:
                        bundle = (
                            service.inspect(args.run_id)
                            if args.operation == "inspect"
                            else service.analyze(
                                DecisionOptions.model_validate_json(
                                    args.options.read_text(encoding="utf-8")
                                )
                            )
                        )
                        result = {"ok": True, **bundle.model_dump(mode="json")}
                    except AnalysisUnavailable as exc:
                        result = {"ok": False, "state": exc.state, "message": str(exc)}
        elif args.command == "analysis":
            from youtube_niche_mcp.analysis.models import FORMULAS, VERSION, AnalysisOptions
            from youtube_niche_mcp.analysis.repository import AnalysisUnavailable
            from youtube_niche_mcp.analysis.service import AnalysisService
            from youtube_niche_mcp.history.repository import HistoryRepository

            if args.operation == "formulas":
                from youtube_niche_mcp.analysis.historical_models import (
                    HISTORY_FORMULAS,
                    HISTORY_VERSION,
                )

                result = {
                    "ok": True,
                    "version": VERSION,
                    "formulas": list(FORMULAS),
                    "offline": True,
                    "public_tools": 0,
                    "public_tools_scope": "internal_phase3_formula_catalog",
                    "registered_public_tools": 15,
                    "historical_version": HISTORY_VERSION,
                    "historical_formulas": list(HISTORY_FORMULAS),
                }
                from youtube_niche_mcp.qualitative.models import DIMENSIONS

                result["qualitative_version"] = "phase5-v1"
                result["qualitative_dimensions"] = list(DIMENSIONS)
                result["decision_dimensions"] = ["F17", "F18", "decision"]
                result["decision_version"] = "phase6-v1"
            else:
                if not settings.db_path.exists():
                    raise MigrationError("Explicitly migrate before stored-frame analysis")
                secrets = tuple(
                    k.get_secret_value()
                    for k in (settings.youtube_api_key, settings.nexlev_api_key)
                    if k
                )
                with connect(
                    settings.db_path,
                    read_only=args.operation == "inspect",
                    timeout=settings.db_timeout_seconds,
                ) as connection:
                    if status(connection)["migration_state"] != "current":
                        raise MigrationError("Migrate explicitly before analysis")
                    service = AnalysisService(HistoryRepository(connection, secrets=secrets))
                    if args.operation == "historical":
                        from youtube_niche_mcp.analysis.historical_models import HistoricalOptions
                        from youtube_niche_mcp.analysis.historical_service import HistoricalService

                        service = HistoricalService(HistoryRepository(connection, secrets=secrets))
                    if args.operation in {"qualitative", "annotate"}:
                        from youtube_niche_mcp.qualitative.models import (
                            Annotation,
                            QualitativeOptions,
                        )
                        from youtube_niche_mcp.qualitative.service import QualitativeService

                        service = QualitativeService(HistoryRepository(connection, secrets=secrets))
                    try:
                        if args.operation == "annotate":
                            annotation = service.annotate(
                                Annotation.model_validate_json(
                                    args.input.read_text(encoding="utf-8")
                                )
                            )
                            print(json.dumps({"ok": True, **annotation.model_dump(mode="json")}))
                            return 0
                        bundle = (
                            service.inspect(args.run_id)
                            if args.operation == "inspect"
                            else service.analyze(
                                args.cohort,
                                (
                                    HistoricalOptions
                                    if args.operation == "historical"
                                    else QualitativeOptions
                                    if args.operation == "qualitative"
                                    else AnalysisOptions
                                ).model_validate_json(args.options.read_text(encoding="utf-8")),
                                video_cohort_id=args.video_cohort,
                            )
                        )
                        result = {"ok": True, **bundle.model_dump(mode="json")}
                    except AnalysisUnavailable as exc:
                        result = {"ok": False, "state": exc.state, "message": str(exc)}
        elif args.command == "config":
            result = {"ok": True, **settings.safe_summary()}
        elif args.command == "provider":
            from dataclasses import asdict

            from youtube_niche_mcp.collectors.nexlev.contracts import (
                ENDPOINTS,
                ROUTES,
                VERSION,
                capability_report,
            )
            from youtube_niche_mcp.collectors.nexlev.models import RETENTION

            result = {
                "ok": True,
                "provider": "nexlev",
                "offline": True,
                "contract_version": VERSION,
                "capabilities": capability_report(settings.nexlev_api_key is not None),
                "routes": list(ROUTES),
                "retention_seconds": RETENTION,
                "retention_state": "contract_review_required",
            }
            if args.operation == "contract":
                result["documented_endpoints"] = {k: asdict(v) for k, v in ENDPOINTS.items()}
            if args.operation in {"quota", "cache-status"}:
                result["records"] = []
                if settings.db_path.exists():
                    with connect(settings.db_path, read_only=True) as connection:
                        if status(connection)["migration_state"] != "current":
                            raise MigrationError(
                                "Migrate explicitly before provider DB diagnostics"
                            )
                        query = (
                            "SELECT q.endpoint,q.request_count,q.bucket,q.requested_at,d.* "
                            "FROM quota_requests q JOIN provider_quota_details d USING(request_id)"
                            if args.operation == "quota"
                            else "SELECT source,COUNT(*) AS entries,"
                            "MIN(expires_at) AS earliest_expiry "
                            "FROM live_cache WHERE source LIKE 'nexlev:%' GROUP BY source"
                        )
                        result["records"] = [dict(row) for row in connection.execute(query)]
        elif args.command == "eligibility":
            from youtube_niche_mcp.eligibility.rules import RULES
            from youtube_niche_mcp.history.retention import RETENTION_CLASSES

            result = {
                "ok": True,
                "rules": [r.model_dump(mode="json") for r in RULES],
                "retention_classes": RETENTION_CLASSES,
                "live_collection_enabled": False,
            }
        elif args.command in {"taxonomy", "cohort"}:
            result = {"ok": True, "state": "not_initialized", "records": []}
            if settings.db_path.exists():
                with connect(settings.db_path, read_only=True) as connection:
                    if status(connection)["migration_state"] != "current":
                        raise MigrationError("Migrate explicitly before inspecting Phase 2 records")
                    if args.command == "taxonomy":
                        rows = connection.execute(
                            "SELECT node_id,taxonomy_version,label,level,parent_id "
                            "FROM taxonomy_nodes "
                            "ORDER BY taxonomy_version,node_id"
                        )
                    else:
                        rows = connection.execute(
                            "SELECT cohort_id,created_at,known_at,research_run,expires_at "
                            "FROM cohort_definitions ORDER BY created_at,cohort_id"
                        )
                    result.update(state="initialized", records=[dict(row) for row in rows])
        elif args.command == "api":
            from dataclasses import asdict

            from youtube_niche_mcp.api.contracts import QuotaContract

            history = operational_status(settings)
            result = {
                "ok": True,
                "capabilities": [
                    item.model_dump(mode="json")
                    for item in capabilities(settings, history_count=history["history_count"])
                ],
                "quota_contract": asdict(QuotaContract()),
            }
        elif args.command in {"history", "snapshot"}:
            if args.operation == "purge-expired":
                from youtube_niche_mcp.history.repository import HistoryRepository

                if not settings.db_path.exists():
                    raise MigrationError("Initialize with migrate before retention maintenance")
                with connect(settings.db_path, timeout=settings.db_timeout_seconds) as connection:
                    if status(connection)["migration_state"] != "current":
                        raise MigrationError("Migrate explicitly before retention maintenance")
                    result = {"ok": True, "deleted": HistoryRepository(connection).purge_expired()}
            else:
                result = operational_status(settings)
        elif args.command == "tool":
            result = {"ok": True, **asyncio.run(check_mcp()), "planned_tools": list(PLANNED_TOOLS)}
        elif args.command == "migrate":
            with connect(settings.db_path, timeout=settings.db_timeout_seconds) as connection:
                installed = migrate(connection)
                result = {"ok": True, "installed_migrations": installed, **status(connection)}
        else:
            with connect(
                settings.db_path, read_only=True, timeout=settings.db_timeout_seconds
            ) as connection:
                result = (
                    integrity(connection)
                    if args.operation == "integrity"
                    else {"ok": True, **status(connection)}
                )
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok", True) else 1
    except (ConfigurationError, MigrationError, sqlite3.Error, OSError) as exc:
        message = (
            str(exc)
            if isinstance(exc, ConfigurationError | MigrationError)
            else (
                "Database or filesystem operation failed; check path, permissions, "
                "and migration state"
            )
        )
        print(
            json.dumps({"ok": False, "error_type": type(exc).__name__, "message": message}),
            file=sys.stderr,
        )
        return 2
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_type": type(exc).__name__,
                    "message": "Operational check failed; run foundation tests for diagnostics",
                }
            ),
            file=sys.stderr,
        )
        return 2
