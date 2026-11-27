"""Offline repository checks. Run: python tests/check.py"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKET = ROOT / ".claude-plugin" / "marketplace.json"
NAME = "stack-scout"


def _load(path, failures):
    """Parse a JSON object file; record a failure and return {} if it cannot."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        failures.append(f"{path.name} does not parse: {exc}")
        return {}
    if not isinstance(data, dict):
        failures.append(f"{path.name} is not a JSON object")
        return {}
    return data


def _dict(value):
    return value if isinstance(value, dict) else {}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    failures = []
    count = 0

    count += 1
    plugin = _load(PLUGIN, failures)
    count += 1
    market = _load(MARKET, failures)

    plugins = market.get("plugins")
    if isinstance(plugins, list) and plugins:
        first = _dict(plugins[0])
    else:
        first = {}
    metadata = _dict(market.get("metadata"))

    count += 1
    if plugin.get("name") != NAME:
        failures.append(f"plugin.json name is {plugin.get('name')!r}, expected {NAME!r}")

    count += 1
    if first.get("name") != NAME:
        failures.append(f"marketplace.json plugins[0].name is {first.get('name')!r}, expected {NAME!r}")

    count += 1
    versions = (plugin.get("version"), metadata.get("version"), first.get("version"))
    if not (isinstance(versions[0], str) and versions[0] and all(v == versions[0] for v in versions)):
        failures.append(
            "versions must be equal strings: plugin.json %r, marketplace metadata %r, plugins[0] %r"
            % versions
        )

    count += 1
    if plugin.get("license") != "MIT":
        failures.append(f"plugin.json license is {plugin.get('license')!r}, expected 'MIT'")

    count += 1
    if not (ROOT / "LICENSE").is_file():
        failures.append("LICENSE is missing")

    if failures:
        for message in failures:
            print(f"FAIL: {message}")
        return 1
    print(f"ok: {count} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
