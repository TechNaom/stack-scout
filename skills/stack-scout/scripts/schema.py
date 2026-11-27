"""A small JSON Schema subset checker, standard library only.

Supported keywords: type (a name or a list of names), required, properties,
additionalProperties (false or a schema), items, enum, pattern, minimum,
maximum, minItems, maxItems. Any other keyword raises
ValueError("unsupported keyword: <k>"), so a schema cannot ask for more than
this checker does. Keyword values are checked, and patterns compiled, before
any instance is looked at.

Strict on purpose: bools are not numbers, 1.0 is not an integer, NaN and
infinities are not numbers, and enum compares numbers by exact type.
Patterns follow JSON Schema (ECMA) meaning: re.search, ASCII \\d \\w \\s, and
an unescaped `$` matches only at the very end (not before a trailing "\\n").

Usage: python schema.py <name> <file>
Prints {"ok": true} (exit 0) or {"ok": false, "errors": [...]} (exit 2).
"""
import json
import math
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

NAMES = ("stack", "facts", "run", "questions", "answers", "labels")

KEYWORDS = frozenset({
    "type", "required", "properties", "additionalProperties", "items", "enum",
    "pattern", "minimum", "maximum", "minItems", "maxItems",
})


def _finite_number(v):
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return True
    return isinstance(v, float) and math.isfinite(v)


_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": _finite_number,
}

_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_PATTERNS = {}


def load(name):
    """Read ROOT/schema/<name>.schema.json for one of the known NAMES."""
    if name not in NAMES:
        raise ValueError(f"unknown schema: {name!r} (known: {', '.join(NAMES)})")
    path = ROOT / "schema" / f"{name}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _ecma(pattern):
    """Turn every unescaped `$` outside a character class into `\\Z`."""
    out = []
    escaped = in_class = False
    for ch in pattern:
        if escaped:
            out.append(ch)
            escaped = False
        elif ch == "\\":
            out.append(ch)
            escaped = True
        elif in_class:
            out.append(ch)
            if ch == "]":
                in_class = False
        elif ch == "[":
            out.append(ch)
            in_class = True
        elif ch == "$":
            out.append(r"\Z")
        else:
            out.append(ch)
    return "".join(out)


def _compile(pattern):
    if pattern not in _PATTERNS:
        _PATTERNS[pattern] = re.compile(_ecma(pattern), re.ASCII)
    return _PATTERNS[pattern]


def _is_count(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def _check_keywords(node):
    """Raise ValueError for an unsupported keyword or a malformed value."""
    if not isinstance(node, dict):
        raise ValueError(f"schema must be an object, got {type(node).__name__}")
    for key in node:
        if key not in KEYWORDS:
            raise ValueError(f"unsupported keyword: {key}")
    if "type" in node:
        t = node["type"]
        names = t if isinstance(t, list) else [t]
        if not names or not all(isinstance(n, str) for n in names):
            raise ValueError(f"type must be a string or a list of strings: {t!r}")
        for n in names:
            if n not in _TYPES:
                raise ValueError(f"unsupported type: {n}")
    if "required" in node:
        r = node["required"]
        if not (isinstance(r, list) and all(isinstance(k, str) for k in r)):
            raise ValueError(f"required must be a list of strings: {r!r}")
    if "enum" in node and not isinstance(node["enum"], list):
        raise ValueError(f"enum must be a list: {node['enum']!r}")
    if "properties" in node:
        if not isinstance(node["properties"], dict):
            raise ValueError("properties must be an object of schemas")
        for sub in node["properties"].values():
            _check_keywords(sub)
    if "additionalProperties" in node:
        extra = node["additionalProperties"]
        if isinstance(extra, dict):
            _check_keywords(extra)
        elif not isinstance(extra, bool):
            raise ValueError(f"additionalProperties must be a boolean or a schema: {extra!r}")
    if "items" in node:
        _check_keywords(node["items"])
    for key in ("minimum", "maximum"):
        if key in node and not _finite_number(node[key]):
            raise ValueError(f"{key} must be a number: {node[key]!r}")
    for key in ("minItems", "maxItems"):
        if key in node and not _is_count(node[key]):
            raise ValueError(f"{key} must be a non-negative integer: {node[key]!r}")
    if "pattern" in node:
        p = node["pattern"]
        if not isinstance(p, str):
            raise ValueError(f"pattern must be a string: {p!r}")
        try:
            _compile(p)
        except re.error as exc:
            raise ValueError(f"pattern does not compile: {p!r}: {exc}") from None


def _key(path, key):
    return f"{path}.{key}" if _NAME.fullmatch(key) else f"{path}[{json.dumps(key)}]"


def _same(a, b):
    """JSON equality: bools, ints and floats never equal each other, at any depth."""
    if type(a) is not type(b):
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
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
        if not _compile(node["pattern"]).search(value):
            errors.append(f"{path}: does not match {node['pattern']}")
    if _finite_number(value):
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


class _Invalid(Exception):
    """A problem with the input file, reported as one '$: ...' error."""


def _no_constant(name):
    raise _Invalid(f"$: {name} is not valid JSON")


def _no_duplicates(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise _Invalid(f"$: duplicate key {json.dumps(key)}")
        seen[key] = value
    return seen


def _read(file):
    try:
        text = pathlib.Path(file).read_bytes().decode("utf-8-sig")
    except OSError as exc:
        raise _Invalid(f"$: cannot read {file}: {exc}") from None
    except UnicodeDecodeError as exc:
        raise _Invalid(f"$: {file} is not UTF-8: {exc}") from None
    try:
        return json.loads(text, parse_constant=_no_constant, object_pairs_hook=_no_duplicates)
    except ValueError as exc:
        raise _Invalid(f"$: {file} is not JSON: {exc}") from None


def _check(argv):
    if len(argv) != 2:
        raise _Invalid("$: usage: schema.py <name> <file>")
    name, file = argv
    try:
        loaded = load(name)
    except (OSError, ValueError) as exc:
        raise _Invalid(f"$: cannot load schema: {exc}") from None
    return validate(_read(file), loaded)


def main(argv):
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        errors = _check(argv)
    except _Invalid as exc:
        errors = [str(exc)]
    except Exception as exc:  # RecursionError on deep input, and anything else
        errors = [f"$: {type(exc).__name__}: {exc}"]
    if errors:
        print(json.dumps({"ok": False, "errors": errors}))
        return 2
    print(json.dumps({"ok": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
