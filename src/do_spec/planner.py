import re
from .core import Fault


def open_queue(tickets):
    """Closed spec members satisfy dependencies and are excluded from execution."""
    ids = [t['id'] for t in tickets]
    if len(set(ids)) != len(ids) or len(ids) > 100:
        raise Fault('TICKET_COUNT_INVALID')
    if any(t.get('state') not in {'open', 'closed'} for t in tickets):
        raise Fault('TRACKER_OUTPUT_INVALID', 'unknown issue state')
    closed = {t['id'] for t in tickets if t['state'] == 'closed'}
    queued = [{**t, 'original_blocked_by': t['blocked_by'],
               'closed_blockers': [b for b in t['blocked_by'] if b in closed],
               'blocked_by': [b for b in t['blocked_by'] if b not in closed]}
              for t in tickets if t['state'] == 'open']
    excluded = [{**t, 'reason': 'ALREADY_CLOSED'} for t in tickets if t['state'] == 'closed']
    return (order(queued) if queued else []), excluded


def order(tickets, limit=100):
    if not tickets or len(tickets) > limit:
        raise Fault("TICKET_COUNT_INVALID")
    ids = [t["id"] for t in tickets]
    if len(set(ids)) != len(ids):
        raise Fault("DUPLICATE_TICKET")
    for t in tickets:
        if any(b not in ids for b in t.get("blocked_by", [])):
            raise Fault("UNRESOLVED_BLOCKER", t["id"])
    done, result = set(), []
    while len(result) != len(tickets):
        ready = [t for t in tickets if t["id"] not in done and set(t.get("blocked_by", [])) <= done]
        if not ready:
            raise Fault("DEPENDENCY_CYCLE")
        t = min(ready, key=lambda x: (x.get("order", ids.index(x["id"])), ids.index(x["id"]), x["id"]))
        result.append(t)
        done.add(t["id"])
    return result


def parse_ticket(identifier, body, parent, mapping=None):
    mapping = mapping or {"parent": "Parent", "blocked_by": "Blocked by", "acceptance": "Acceptance criteria"}
    sections = {}
    for match in re.finditer(r"^## ([^\r\n]+)\r?\n(.*?)(?=^## |\Z)", body, re.M | re.S):
        if match[1] in sections:
            raise Fault("AMBIGUOUS_RELATION", match[1])
        sections[match[1]] = match[2].strip()
    def section(key):
        if mapping[key] not in sections:
            raise Fault("ARTIFACT_CONTRACT_MISSING", mapping[key])
        return sections[mapping[key]]
    if section("parent") != f"#{parent}":
        raise Fault("TRACKER_CONTEXT_MISMATCH", identifier)
    raw = section("blocked_by")
    if raw.lower() == "none":
        blockers = []
    else:
        if not re.fullmatch(r"(?:\s*[-*]?\s*#\d+\s*[,]?)+", raw):
            raise Fault("AMBIGUOUS_RELATION", "blockers must be explicit same-repository issue numbers")
        blockers = re.findall(r"#(\d+)", raw)
        if len(set(blockers)) != len(blockers):
            raise Fault("DUPLICATE_RELATION")
    acceptance = section("acceptance")
    if not acceptance:
        raise Fault("ACCEPTANCE_MISSING")
    return {"id": str(identifier), "title": body.splitlines()[0].lstrip("# "), "body": body,
            "acceptance": acceptance, "blocked_by": blockers, "relation_source": "body_parent"}
