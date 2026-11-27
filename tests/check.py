"""Offline repository checks. Run: python tests/check.py"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKET = ROOT / ".claude-plugin" / "marketplace.json"
NAME = "stack-scout"


def _load(path, failures):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        failures.append(f"{path.name} does not parse: {exc}")
        return None


def main() -> int:
    failures = []
    count = 0

    count += 1
    plugin = _load(PLUGIN, failures)
    count += 1
    market = _load(MARKET, failures)
    plugin = plugin if isinstance(plugin, dict) else {}
    market = market if isinstance(market, dict) else {}
    plugins = market.get("plugins") or [{}]
    first = plugins[0] if isinstance(plugins[0], dict) else {}

    count += 1
    if plugin.get("name") != NAME:
        failures.append(f"plugin.json name is {plugin.get('name')!r}, expected {NAME!r}")

    count += 1
    if first.get("name") != NAME:
        failures.append(f"marketplace.json plugins[0].name is {first.get('name')!r}, expected {NAME!r}")

    count += 1
    versions = (
        plugin.get("version"),
        (market.get("metadata") or {}).get("version"),
        first.get("version"),
    )
    if len(set(versions)) != 1 or versions[0] is None:
        failures.append(
            "versions differ: plugin.json %r, marketplace metadata %r, plugins[0] %r" % versions
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
