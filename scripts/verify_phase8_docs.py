"""Validate UTF-8 release documents, all public examples, host profiles and lock versions."""

import importlib.metadata
import json
import re
from pathlib import Path

from youtube_niche_mcp.config import Settings
from youtube_niche_mcp.services.catalog import PLANNED_TOOLS
from youtube_niche_mcp.tools.schemas import INPUTS

ROOT = Path(__file__).resolve().parent.parent


def main():
    files = sorted(
        set(
            [
                ROOT / "README.md",
                ROOT / "docs/architecture.md",
                ROOT / "docs/methodology.md",
                ROOT / "docs/research-requirements-map.md",
                *ROOT.glob("docs/*release*.md"),
                *ROOT.glob("docs/phase-8-*.md"),
            ]
        )
    )
    for path in files:
        text = path.read_bytes().decode("utf-8", errors="strict")
        assert "\ufffd" not in text and "\u00e2\u20ac" not in text, path
        assert not re.search(r"AIza[0-9A-Za-z_-]{35}|-----BEGIN (?:RSA |EC )?PRIVATE KEY", text), (
            path
        )
    examples = json.loads((ROOT / "docs/phase-8-tool-examples.json").read_text())
    assert {e["name"] for e in examples} == set(PLANNED_TOOLS)
    for row in examples:
        INPUTS[row["name"]].model_validate(row["arguments"]["request"])
    profiles = json.loads((ROOT / "docs/mcp-config.release.example.json").read_text())
    for name, config in profiles.items():
        server = config["mcpServers"]["youtube-niche-finder"]
        assert server["type"] == "stdio" and server["args"] == ["-m", "youtube_niche_mcp.server"]
        settings = Settings.from_env(server["env"])
        assert settings.db_path.is_absolute() and Path(server["cwd"]).is_absolute(), name
    count = 0
    for line in (ROOT / "requirements-dev.lock").read_text().splitlines():
        match = re.match(r"([\w.-]+)==([^;\s]+)", line)
        if match:
            name, version = match.groups()
            assert importlib.metadata.version(name) == version, name
            count += 1
    print(
        json.dumps(
            {
                "ok": True,
                "utf8_documents": len(files),
                "examples": len(examples),
                "profiles": len(profiles),
                "locked_distributions": count,
            }
        )
    )


if __name__ == "__main__":
    main()
