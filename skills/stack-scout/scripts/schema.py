"""A small JSON Schema subset checker, standard library only.

Supported keywords: type (a name or a list of names), required, properties,
additionalProperties (false or a schema), items, enum, pattern, minimum,
maximum, minItems, maxItems. Any other keyword raises
ValueError("unsupported keyword: <k>"), so a schema cannot ask for more than
this checker does.

Usage: python schema.py <name> <file>
Prints {"ok": true} (exit 0) or {"ok": false, "errors": [...]} (exit 2).
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

KEYWORDS = frozenset({
    "type", "required", "properties", "additionalProperties", "items", "enum",
    "pattern", "minimum", "maximum", "minItems", "maxItems",
})

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
}

_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load(name):
    """Read ROOT/schema/<name>.schema.json."""
    path = ROOT / "schema" / f"{name}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _check_keywords(node):
    """Raise ValueError for any keyword the checker does not support."""
    if not isinstance(node, dict):
        raise ValueError(f"schema must be an object, got {type(node).__name__}")
    for key in node:
        if key not in KEYWORDS:
            raise ValueError(f"unsupported keyword: {key}")
    if "type" in node:
        names = node["type"] if isinstance(node["type"], list) else [node["type"]]
        for t in names:
            if t not in _TYPES:
                raise ValueError(f"unsupported type: {t}")
    for sub in node.get("properties", {}).values():
        _check_keywords(sub)
    if isinstance(node.get("additionalProperties"), dict):
        _check_keywords(node["additionalProperties"])
    if "items" in node:
        _check_keywords(node["items"])


def _key(path, key):
    return f"{path}.{key}" if _NAME.match(key) else f"{path}[{json.dumps(key)}]"


def _same(a, b):
    """Equality that keeps bools apart from numbers, as JSON does."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    return a == b


def _walk(value, node, path, errors):
    if "type" in node:
        names = node["type"] if isinstance(node["type"], list) else [node["type"]]
        if not any(_TYPES[t](value) for t in names):
            errors.append(f"{path}: expected {' or '.join(names)}")
            return
    if "enum" in node and not any(_same(value, e) for e in node["enum"]):
        errors.append(f"{path}: not one of {json.dumps(node['enum'])}")
    if isinstance(value, str) and "pattern" in node:
        if not re.search(node["pattern"], value):
            errors.append(f"{path}: does not match {node['pattern']}")
    if _TYPES["number"](value):
        if "minimum" in node and value < node["minimum"]:
            errors.append(f"{path}: below minimum {node['minimum']}")
        if "maximum" in node and value > node["maximum"]:
            errors.append(f"{path}: above maximum {node['maximum']}")
    if isinstance(value, list):
        if "minItems" in node and len(value) < node["minItems"]:
            errors.append(f"{path}: fewer than {node['minItems']} items")
        if "maxItems" in node and len(value) > node["maxItems"]:
            errors.append(f"{path}: more than {node['maxItems']} items")
        if "items" in node:
            for i, item in enumerate(value):
                _walk(item, node["items"], f"{path}[{i}]", errors)
    if isinstance(value, dict):
        props = node.get("properties", {})
        for key in node.get("required", []):
            if key not in value:
                errors.append(f"{_key(path, key)}: required")
        extra = node.get("additionalProperties", True)
        for key, item in value.items():
            if key in props:
                _walk(item, props[key], _key(path, key), errors)
            elif extra is False:
                errors.append(f"{_key(path, key)}: not allowed")
            elif isinstance(extra, dict):
                _walk(item, extra, _key(path, key), errors)


def validate(instance, schema):
    """Return every error as '<json path>: <message>'; [] when valid."""
    _check_keywords(schema)
    errors = []
    _walk(instance, schema, "$", errors)
    return errors


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8")
    if len(argv) != 2:
        print(json.dumps({"ok": False, "errors": ["usage: schema.py <name> <file>"]}))
        return 2
    name, file = argv
    try:
        loaded = load(name)
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "errors": [f"$: cannot load schema {name}: {exc}"]}))
        return 2
    try:
        instance = json.loads(pathlib.Path(file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "errors": [f"$: cannot read {file}: {exc}"]}))
        return 2
    errors = validate(instance, loaded)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}))
        return 2
    print(json.dumps({"ok": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
