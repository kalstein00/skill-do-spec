"""CLI-only tracker operations. Live profiles fail closed until certified.

The synthetic protocol tests operation semantics independently from a particular
tea release. It is explicitly not a claim about any installed tea argv contract.
"""
import json
from pathlib import Path
import re
import time
import uuid
from urllib.parse import urlsplit, urlunsplit
from .core import Fault, digest, read, write
from .process import run, clean_env


def base_url(value):
    u = urlsplit(value)
    if u.scheme != "https" or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise Fault("TRACKER_CONTEXT_MISMATCH", "expected HTTPS instance base URL")
    return urlunsplit((u.scheme, u.netloc.lower(), u.path.rstrip("/"), "", ""))


def key(profile, number):
    return f'{profile["kind"]}|{base_url(profile["base_url"])}|{profile["repository"]}|{number}'


class Tracker:
    kind = None
    transport = None

    def __init__(self, profile, logs):
        self.profile = profile
        self.logs = Path(logs)
        self.logs.mkdir(parents=True, exist_ok=True)
        if profile["kind"] != self.kind or profile["transport"] != self.transport:
            raise Fault("TRACKER_CONTEXT_MISMATCH")
        base_url(profile["base_url"])
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", profile["repository"]):
            raise Fault("TRACKER_CONTEXT_MISMATCH", "repository")
        if not profile.get("synthetic_contract"):
            raise Fault("TRACKER_CLI_UNSUPPORTED", "live CLI/server/auth/redirect contract not certified")
        self.count = 0

    def call(self, operation, number=None, page=None, body=None):
        self.count += 1
        argv = self.argv(operation, number, page)
        log = self.logs / f"{uuid.uuid4().hex}-{operation}"
        result = run(argv, self.logs, log, self.profile.get("timeout", 30), payload=json.dumps(body, ensure_ascii=False).encode() if body is not None else None, env=clean_env())
        if result["outcome"] != "EXITED":
            raise Fault("TRACKER_CLI_TIMEOUT", operation, 14 if body is not None else 3)
        if result["exit_code"]:
            raise Fault("TRACKER_UNAVAILABLE", f'{operation}, exit={result["exit_code"]}')
        try:
            data = json.loads(Path(str(log) + ".stdout.log").read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as e:
            raise Fault("TRACKER_OUTPUT_INVALID", operation) from e
        if not isinstance(data, dict) or data.get("context") != self.context():
            raise Fault("TRACKER_CONTEXT_MISMATCH", operation)
        return data

    def context(self):
        return {k: self.profile[k] for k in ["kind", "base_url", "repository", "account"]}

    def issue(self, number):
        data = self.call("read", number).get("issue")
        if not isinstance(data, dict) or not {"number", "id", "body", "state", "url"} <= set(data) or data["number"] != number or not isinstance(data["body"], str):
            raise Fault("TRACKER_OUTPUT_INVALID", "issue schema")
        expected = f'{self.profile["base_url"].rstrip("/")}/{self.profile["repository"]}/issues/{number}'
        if data["url"] != expected:
            raise Fault("CROSS_TRACKER_REFERENCE")
        if data['state'] not in {'open', 'closed'}:
            raise Fault('TRACKER_OUTPUT_INVALID', 'issue state')
        return {**data, "key": key(self.profile, number)}

    def pages(self, operation, number=None):
        page, records, seen = 1, [], set()
        while True:
            if page in seen or len(seen) >= 1000:
                raise Fault("DISCOVERY_INCOMPLETE")
            seen.add(page)
            data = self.call(operation, number, page)
            if set(data) != {"context", "items", "next_page"} or not isinstance(data["items"], list):
                raise Fault("TRACKER_OUTPUT_INVALID", operation)
            records.extend(data["items"])
            page = data["next_page"]
            if page is None:
                return records
            if not isinstance(page, int) or page <= 0:
                raise Fault("DISCOVERY_INCOMPLETE")

    def list_issues(self):
        return [x for x in self.pages("list") if not x.get("pull_request")]

    def comments(self, number):
        comments = self.pages("comments", number)
        if any(not isinstance(c, dict) or not {"id", "body"} <= set(c) for c in comments):
            raise Fault("TRACKER_OUTPUT_INVALID", "comments")
        return comments

    def ensure_comment(self, number, body, operation_key, approved=False):
        if not approved:
            raise Fault("REMOTE_WRITE_NOT_APPROVED", code=14)
        marker = "<!-- do-spec:" + digest([key(self.profile, number), operation_key]) + " -->"
        pending = self.logs / (digest(marker) + ".intent.json")
        matches = [c for c in self.comments(number) if marker in c["body"]]
        if len(matches) == 1:
            write(pending, {"state": "CONFIRMED", "id": matches[0]["id"]})
            return matches[0]
        if len(matches) > 1 or pending.exists():
            raise Fault("REPORT_PENDING", "uncertain POST requires reconciliation; no blind resend", 14)
        write(pending, {"state": "POST_INTENT", "marker": marker})
        try:
            self.call("comment", number, body={"body": body + "\n" + marker})
        except Fault as e:
            raise Fault("REPORT_PENDING", e.reason, 14) from e
        return self.ensure_comment(number, body, operation_key, approved=True)

    def ensure_closed(self, number, approved=False, push_receipt=None):
        if not approved or not push_receipt or push_receipt.get("ticket_key") != key(self.profile, number):
            raise Fault("PUSH_RECEIPT_REQUIRED", code=14)
        if self.issue(number)["state"] == "closed":
            return
        self.call("close", number, body={"state": "closed"})
        if self.issue(number)["state"] != "closed":
            raise Fault("REPORT_PENDING", code=14)


class GitHubGhAdapter(Tracker):
    kind, transport = "github", "gh"

    def argv(self, operation, number, page):
        return [*self.profile["argv"], "--provider", "github", "--hostname", self.profile["base_url"], "--repo", self.profile["repository"], "--account", self.profile["account"], "--operation", operation, "--number", str(number or 0), "--page", str(page or 1)]


class ForgejoTeaAdapter(Tracker):
    kind, transport = "forgejo", "tea"

    def argv(self, operation, number, page):
        return [*self.profile["argv"], "--provider", "forgejo", "--instance", self.profile["base_url"], "--repo", self.profile["repository"], "--login", self.profile["account"], "--operation", operation, "--number", str(number or 0), "--page", str(page or 1)]


class LocalIssueTracker:
    """Mutable local issue states, separate from immutable Markdown requirements."""
    def __init__(self, profile):
        self.path = Path(profile['state_file']).resolve()

    def issue(self, number):
        try:
            issue = read(self.path)['issues'][str(number)]
            if issue['state'] not in {'open', 'closed'} or issue['number'] != number:
                raise ValueError('invalid state/identity')
            return {**issue, 'key': f'local|{self.path}|{number}'}
        except (OSError, ValueError, KeyError, TypeError) as e:
            raise Fault('TRACKER_OUTPUT_INVALID', 'local issue state unavailable') from e


def connect(profile, logs):
    if profile['kind'] == 'local':
        return LocalIssueTracker(profile)
    cls = {'github': GitHubGhAdapter, 'forgejo': ForgejoTeaAdapter}.get(profile['kind'])
    if not cls:
        raise Fault('TRACKER_CLI_UNSUPPORTED')
    return cls(profile, logs)


def observe(profile, number, logs):
    issue = connect(profile, logs).issue(int(number))
    return {'key': issue['key'], 'number': issue['number'], 'state': issue['state'], 'observed_at': time.time()}
