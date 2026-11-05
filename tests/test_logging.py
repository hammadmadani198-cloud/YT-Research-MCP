import json
import logging

from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.logging import configure_logging


def test_structured_logs_use_stderr_and_redact_key(capsys):
    settings = Settings.from_env({"YOUTUBE_API_KEY": "fixture-secret"})
    logger = logging.getLogger("youtube_niche_mcp.fixture")
    configure_logging(settings)
    logger.info("request fixture-secret")
    output = capsys.readouterr()
    assert output.out == ""
    payload = json.loads(output.err)
    assert payload["event"] == "request [REDACTED]"
    assert payload["level"] == "INFO"


def test_exception_details_do_not_leak_secrets(capsys):
    configure_logging(Settings())
    try:
        raise ValueError("private-exception-details")
    except ValueError:
        logging.getLogger("youtube_niche_mcp.fixture").exception("failed_operation")
    payload = json.loads(capsys.readouterr().err)
    assert payload["exception_type"] == "ValueError"
    assert "private-exception-details" not in str(payload)
