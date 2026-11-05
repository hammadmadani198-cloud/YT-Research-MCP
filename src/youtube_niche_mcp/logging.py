"""JSON logs on stderr; stdout is reserved for MCP framing."""

import json
import logging
import re
import sys
from datetime import UTC, datetime

from youtube_niche_mcp.config import Settings


class JsonFormatter(logging.Formatter):
    def __init__(self, secrets: tuple[str, ...] = ()) -> None:
        super().__init__()
        self.secrets = secrets

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        for secret in self.secrets:
            if secret:
                message = message.replace(secret, "[REDACTED]")
        message = re.sub(
            r"(?i)\b(authorization\s*[:=]\s*(?:bearer\s+)?|bearer\s+|"
            r"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|cookie)\s*[:=]\s*)"
            r"[^\s,;]+",
            r"\1[REDACTED]",
            message,
        )
        result = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": message,
        }
        if record.exc_info and record.exc_info[0]:
            result["exception_type"] = record.exc_info[0].__name__
        return json.dumps(result, ensure_ascii=True)


def configure_logging(settings: Settings) -> None:
    secrets = tuple(
        value.get_secret_value()
        for value in (settings.youtube_api_key, settings.nexlev_api_key)
        if value
    )
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter(secrets))
    logger = logging.getLogger("youtube_niche_mcp")
    logger.handlers[:] = [handler]
    logger.setLevel(settings.log_level)
    logger.propagate = False
