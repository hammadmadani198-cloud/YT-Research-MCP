"""Reject credential-bearing cache/manifests rather than persisting them."""

import json
import re
from hashlib import sha256

FORBIDDEN = {
    "x_goog_api_key",
    "x_api_key",
    "client_secret",
    "cookie",
    "set_cookie",
    "key",
    "api_key",
    "apikey",
    "youtube_api_key",
    "nexlev_api_key",
    "authorization",
    "password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
}


def safe_json(value, secrets: tuple[str, ...] = ()) -> str:
    def check(item):
        if isinstance(item, dict):
            for key, child in item.items():
                normalized = re.sub(r"(?<=[a-z])(?=[A-Z])", "_", str(key)).lower().replace("-", "_")
                if normalized in FORBIDDEN:
                    raise ValueError("Credential-bearing data is not permitted")
                check(key)
                check(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                check(child)
        elif isinstance(item, str) and any(secret and secret in item for secret in secrets):
            raise ValueError("Credential-bearing data is not permitted")

    check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def identity(value, secrets: tuple[str, ...] = ()) -> str:
    return sha256(safe_json(value, secrets).encode()).hexdigest()
