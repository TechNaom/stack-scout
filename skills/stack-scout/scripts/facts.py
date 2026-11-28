"""Facts about GitHub repositories, checked against GitHub, never from memory.

  python facts.py verify owner/repo [owner/repo ...]
      With a token: one GraphQL request per 20 repositories. Without one: REST only, and the facts REST cannot
      give are marked to verify. Prints {"ok", "checked", "missing", "unchecked", "partial", "mode"}; exit 3
      (partial) when GitHub rate-limits the run: what was checked is kept, the rest is listed as unchecked.
  python facts.py to-verify SUBJECT FIELD "REASON" --source https://...
      Records one fact the run could not check yet (value null, with the reason).

Bad arguments print {"ok": false, "error": ...} and exit 2.
"""
import re
import sys

import common

BATCH = 20
NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
NO_LICENCE = "no licence GitHub can identify"
BOTS_ONLY = "only bot activity in the last 100 commits"
NO_COMMITS = "no commits on the default branch"
NEEDS_SIGN_IN = "needs a GitHub sign-in: run gh auth login"
REST_NOTE = "No GitHub sign-in: REST only. latest_release and primary_language are marked to verify."

REPO_FIELDS = """url stargazerCount isArchived licenseInfo { spdxId } latestRelease { publishedAt }
    primaryLanguage { name }
    defaultBranchRef { target { ... on Commit { history(first: 100) {
      nodes { committedDate author { name user { login } } } } } } }"""


def is_bot(login, name) -> bool:
    """A login ending in [bot], or a login or name on the rules' bot list (lower case, [bot] removed)."""
    if login and login.endswith("[bot]"):
        return True
    bots = set(common.load_rules()["bot_logins"])
    return any(v and v.lower().replace("[bot]", "").strip() in bots for v in (login, name))


def _check_name(arg: str) -> str:
    owner_repo = arg.split("/")
    if not NAME.match(arg) or any(part in (".", "..") for part in owner_repo):
        raise common.CoreError(f"not owner/repo: {arg}")
    return arg


def _date(stamp):
    return stamp[:10] if stamp else None


def _licence(spdx):
    """(value, to_verify): NOASSERTION or no licence is not a guess, it is a question."""
    return (spdx, None) if spdx and spdx != "NOASSERTION" else (None, NO_LICENCE)


def _last_activity(commits):
    """(date, to_verify) of the newest commit by a person; commits are (date, login, name)."""
    if not commits:
        return None, NO_COMMITS
    human = [d for d, login, name in commits if d and not is_bot(login, name)]
    return (_date(max(human)), None) if human else (None, BOTS_ONLY)


def _facts(name, values: dict, to_verify: dict) -> list:
    subject, source = f"github:{name}", f"https://github.com/{name}"
    return [common.fact(subject, field, value, source, to_verify=to_verify.get(field))
            for field, value in values.items()]


def _graphql_batch(names, token):
    """One request for up to 20 repositories. Returns (facts, checked, missing, unchecked, points)."""
    aliases = "\n".join(f'  r{i}: repository(owner: "{n.split("/")[0]}", name: "{n.split("/")[1]}") {{ {REPO_FIELDS} }}'
                        for i, n in enumerate(names))
    query = f"query {{\n  rateLimit {{ cost remaining resetAt }}\n{aliases}\n}}"
    status, body = common.http_json("POST", f"{common.github_api()}/graphql", body={"query": query}, token=token)
    body = body if isinstance(body, dict) else {}
    errors = body.get("errors") or []
    if any(e.get("type") == "RATE_LIMITED" for e in errors):  # GitHub can say this with HTTP 200
        raise common.RateLimited(status, None, "GraphQL rate limited")
    data = body.get("data")
    if status != 200 or not isinstance(data, dict):
        kinds = sorted({str(e.get("type")) for e in errors}) or [f"HTTP {status}"]
        raise common.CoreError(f"GitHub GraphQL request failed: {', '.join(kinds)}")
    not_found = {e["path"][0] for e in errors if e.get("type") == "NOT_FOUND" and e.get("path")}
    facts, checked, missing, unchecked = [], [], [], []
    for i, name in enumerate(names):
        node = data.get(f"r{i}")
        if node is None:
            if f"r{i}" not in not_found:  # hidden (FORBIDDEN, SAML) or failed: not a fact either way
                unchecked.append(name)
                continue
            facts += _facts(name, {"exists": False}, {})
            missing.append(name)
            continue
        lic, lic_q = _licence((node.get("licenseInfo") or {}).get("spdxId"))
        history = (((node.get("defaultBranchRef") or {}).get("target") or {}).get("history") or {}).get("nodes") or []
        commits = [(c.get("committedDate"), ((c.get("author") or {}).get("user") or {}).get("login"),
                    (c.get("author") or {}).get("name")) for c in history]
        active, active_q = _last_activity(commits)
        facts += _facts(name, {
            "exists": True, "stars": node.get("stargazerCount"), "archived": node.get("isArchived"),
            "licence": lic, "latest_release": _date((node.get("latestRelease") or {}).get("publishedAt")),
            "primary_language": (node.get("primaryLanguage") or {}).get("name"), "last_activity": active,
        }, {"licence": lic_q, "last_activity": active_q})
        checked.append(name)
    return facts, checked, missing, unchecked, int((data.get("rateLimit") or {}).get("cost") or 0)


def _rest_one(name):
    """REST for one repository, no token. Returns (facts, found)."""
    api = common.github_api()
    status, repo = common.http_json("GET", f"{api}/repos/{name}")
    if status == 404:
        return _facts(name, {"exists": False}, {}), False
    if not isinstance(repo, dict):
        raise common.CoreError(f"GitHub sent no repository data for {name}")
    try:
        status, items = common.http_json("GET", f"{api}/repos/{name}/commits?per_page=100")
    except RuntimeError as exc:
        if "HTTP 409" not in str(exc):  # 409: an empty repository has no commits
            raise
        items = []
    items = items if isinstance(items, list) else []
    commits = [(((c.get("commit") or {}).get("author") or {}).get("date"), (c.get("author") or {}).get("login"),
                ((c.get("commit") or {}).get("author") or {}).get("name")) for c in (items or [])]
    lic, lic_q = _licence((repo.get("license") or {}).get("spdx_id"))
    active, active_q = _last_activity(commits)
    return _facts(name, {
        "exists": True, "stars": repo.get("stargazers_count"), "archived": repo.get("archived"), "licence": lic,
        "last_activity": active, "latest_release": None, "primary_language": None,
    }, {"licence": lic_q, "last_activity": active_q, "latest_release": NEEDS_SIGN_IN,
        "primary_language": NEEDS_SIGN_IN}), True


def verify(repos: list) -> dict:
    """Check each repository, save the facts, and say what was checked, missing or left unchecked."""
    repos = list(dict.fromkeys(_check_name(r) for r in repos))
    token = common.get_token()
    out = {"ok": True, "checked": [], "missing": [], "unchecked": [], "partial": False,
           "mode": "graphql" if token else "rest"}
    facts, points, done = [], 0, 0
    try:  # whatever happens, the facts already gathered are saved
        if token:
            for start in range(0, len(repos), BATCH):
                batch = repos[start:start + BATCH]
                got, checked, missing, unchecked, cost = _graphql_batch(batch, token)
                facts += got
                out["checked"] += checked
                out["missing"] += missing
                out["unchecked"] += unchecked
                points += cost
                done = start + len(batch)
        else:
            for name in repos:
                got, found = _rest_one(name)
                facts += got
                out["checked" if found else "missing"].append(name)
                done += 1
    except common.RateLimited:
        out["unchecked"] += repos[done:]
    finally:
        if facts:
            common.add_facts(facts)
        out["partial"] = bool(out["unchecked"])
        common.meter(script_calls=0, github_points=points, partial=True if out["partial"] else None)
    if not token:
        out["note"] = REST_NOTE
    return out


def _to_verify(args):
    if len(args) != 5 or args[3] != "--source":
        raise common.CoreError('usage: facts.py to-verify SUBJECT FIELD "REASON" --source https://...')
    subject, field, reason, _, source = args
    if not source.startswith("https://"):
        raise common.CoreError("--source must start with https://")
    if not reason.strip():
        raise common.CoreError("the reason must not be empty")
    common.add_facts([common.fact(subject, field, None, source, to_verify=reason)])
    return {"ok": True, "subject": subject, "field": field}


def main(argv) -> int:
    common.utf8_stdout()
    try:
        common.meter(script_calls=1)
        if argv[:1] == ["verify"] and len(argv) > 1:
            out = verify(argv[1:])
        elif argv[:1] == ["to-verify"]:
            out = _to_verify(argv[1:])
        else:
            raise common.CoreError("usage: facts.py verify owner/repo [...] | to-verify ...")
    except (common.CoreError, RuntimeError, OSError) as exc:
        common.emit({"ok": False, "error": str(exc)})
        return common.EXIT_BLOCKED
    common.emit(out)
    return common.EXIT_RATE_LIMITED if out.get("partial") else common.EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
