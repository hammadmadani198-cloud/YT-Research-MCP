import pytest

from youtube_niche_mcp.config import ConfigurationError, Settings


def test_defaults_need_no_api_key():
    settings = Settings.from_env({})
    assert settings.youtube_api_key is None
    assert settings.db_path.name == "research.sqlite3"
    assert not settings.safe_summary()["live_api_required"]


def test_env_override_and_secret_never_serialized():
    key = "fixture-secret-DO-NOT-USE"
    settings = Settings.from_env(
        {
            "YOUTUBE_API_KEY": key,
            "YTNMCP_DB_PATH": "custom.sqlite3",
            "YTNMCP_LOG_LEVEL": "WARNING",
            "YTNMCP_DB_TIMEOUT_SECONDS": "12.5",
        }
    )
    assert settings.db_timeout_seconds == 12.5
    assert settings.log_level == "WARNING"
    assert settings.safe_summary()["youtube_api_key_present"]
    assert key not in settings.model_dump_json()
    assert key not in repr(settings)
    assert key not in str(settings.safe_summary())


def test_blank_api_key_is_absent():
    assert Settings.from_env({"YOUTUBE_API_KEY": " "}).youtube_api_key is None


@pytest.mark.parametrize("value", ["0", "-1", "121", "NaN", "inf", "private-bad-value", ""])
def test_invalid_timeout_has_safe_error(value):
    with pytest.raises(ConfigurationError) as caught:
        Settings.from_env({"YTNMCP_DB_TIMEOUT_SECONDS": value})
    if value:
        assert value not in str(caught.value)


def test_invalid_log_level_does_not_echo_input():
    with pytest.raises(ConfigurationError, match="log_level") as caught:
        Settings.from_env({"YTNMCP_LOG_LEVEL": "secret-value"})
    assert "secret-value" not in str(caught.value)
