#!/usr/bin/env python3
"""smell_check.py — validate a backlog ticket and detect splittability smells.

Reads a ticket as JSON (from --input <path> or stdin), validates that every
acceptance criterion is in Given/When/Then form, runs seven splittability
heuristics, and emits a JSON report to stdout.

Exit codes:
  0  always, unless the input itself can't be read or parsed.
  1  unreadable input, malformed JSON, or unexpected error.

The report is the source of truth for the model. The model uses `verdict`
to decide whether to slice, consider, or decline (the "caution" path).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from typing import Any


# ---------- Configuration (tunable thresholds) ----------

MAX_ACS = 5
MAX_DESCRIPTION_WORDS = 200
MAX_DESCRIPTION_HEADERS = 2
MAX_ESTIMATE = 8
PERSONA_DISTINCT_THRESHOLD = 2  # 2+ distinct personas → trigger
CRUD_DISTINCT_THRESHOLD = 3     # 3+ of {create, read, update, delete} → trigger

# Conjunctions that suggest two things glued together
TITLE_CONJUNCTIONS = re.compile(r"\b(?:and|or)\b|[+/&]", re.IGNORECASE)
CLAUSE_CONJUNCTIONS = re.compile(r"\b(?:and|or)\b", re.IGNORECASE)

# Action verb stems we count in titles. Two or more = multi-verb title.
ACTION_VERBS = frozenset({
    "add", "create", "delete", "remove", "update", "edit", "modify", "view",
    "list", "show", "import", "export", "upload", "download", "send",
    "receive", "validate", "approve", "reject", "save", "load", "search",
    "filter", "sort", "share", "submit", "process", "generate", "format",
    "parse", "render", "display", "publish", "schedule", "cancel", "archive",
    "restore", "assign", "unassign", "tag", "untag",
})

# CRUD categories — if 3 of 4 show up across all scenario text, that's a smell.
CRUD_CATEGORIES = {
    "create": {"create", "creates", "creating", "add", "adds", "adding", "new"},
    "read":   {"read", "reads", "reading", "view", "views", "viewing", "list",
               "lists", "listing", "show", "shows", "showing", "see"},
    "update": {"update", "updates", "updating", "edit", "edits", "editing",
               "modify", "modifies", "modifying", "change", "changes", "rename"},
    "delete": {"delete", "deletes", "deleting", "remove", "removes", "removing",
               "archive", "archives", "archiving"},
}

# Severity weights for verdict computation.
HIGH_SMELLS = {"multi_verb_title", "compound_gwt", "too_many_acs", "oversized_estimate"}
MEDIUM_SMELLS = {"multiple_personas", "sprawling_description", "mixed_crud"}


# ---------- Given/When/Then parsing ----------

# Tolerates inline ("Given X, When Y, Then Z"), multi-line, and period-separated forms.
GWT_RE = re.compile(
    r"^\s*given\s+(?P<given>.+?)[\s,.\n]+when\s+(?P<when>.+?)[\s,.\n]+then\s+(?P<then>.+?)\s*\.?\s*$",
    re.IGNORECASE | re.DOTALL,
)


def parse_gwt(text: str) -> dict[str, str] | None:
    """Parse a single AC string into {given, when, then}. Returns None if it doesn't fit."""
    if not isinstance(text, str):
        return None
    m = GWT_RE.match(text.strip())
    if not m:
        return None
    return {
        "given": _norm(m.group("given")),
        "when":  _norm(m.group("when")),
        "then":  _norm(m.group("then")),
    }


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


# ---------- Schema validation ----------

REQUIRED_FIELDS = ("title", "description", "acceptance_criteria")  # `id` is optional — content-hash fallback in build_plan.py


def validate_schema(ticket: Any) -> tuple[bool, list[str], list[dict]]:
    """Return (schema_valid, errors, parsed_acs). parsed_acs may be partial when invalid."""
    errors: list[str] = []
    parsed_acs: list[dict] = []

    if not isinstance(ticket, dict):
        return False, ["ticket must be a JSON object"], []

    for f in REQUIRED_FIELDS:
        if f not in ticket:
            errors.append(f"missing required field: {f}")

    if not isinstance(ticket.get("title", ""), str) or not ticket.get("title", "").strip():
        errors.append("title must be a non-empty string")

    if not isinstance(ticket.get("description", ""), str):
        errors.append("description must be a string")

    acs = ticket.get("acceptance_criteria", [])
    if not isinstance(acs, list) or not acs:
        errors.append("acceptance_criteria must be a non-empty list")
    else:
        for i, ac in enumerate(acs, start=1):
            parsed = parse_gwt(ac) if isinstance(ac, str) else None
            if parsed is None:
                preview = (ac[:60] + "…") if isinstance(ac, str) and len(ac) > 60 else str(ac)
                errors.append(
                    f"AC #{i} is not in Given/When/Then form: {preview!r}"
                )
                parsed_acs.append({"index": i, "raw": ac, "parsed": None})
            else:
                parsed_acs.append({"index": i, "raw": ac, "parsed": parsed})

    estimate = ticket.get("estimate")
    if estimate is not None and not isinstance(estimate, (int, float)):
        errors.append("estimate, when present, must be a number")

    return (not errors), errors, parsed_acs


# ---------- Smell detectors ----------

def smell_multi_verb_title(ticket: dict) -> dict:
    title = (ticket.get("title") or "").strip()
    title_lc = title.lower()

    has_conjunction = bool(TITLE_CONJUNCTIONS.search(title))
    words = re.findall(r"[a-zA-Z]+", title_lc)
    verbs_found = [w for w in words if w in ACTION_VERBS]
    distinct_verbs = sorted(set(verbs_found))

    triggered = has_conjunction or len(distinct_verbs) >= 2

    if triggered:
        if has_conjunction and len(distinct_verbs) >= 2:
            evidence = f"title joins {len(distinct_verbs)} action verbs ({', '.join(distinct_verbs)}) with a conjunction"
        elif has_conjunction:
            evidence = "title contains a conjunction (and / or / + / /)"
        else:
            evidence = f"title contains {len(distinct_verbs)} distinct action verbs: {', '.join(distinct_verbs)}"
    else:
        evidence = "title is single-verb / single-outcome"

    return {
        "name": "multi_verb_title",
        "triggered": triggered,
        "severity": "high",
        "evidence": evidence,
    }


def smell_compound_gwt(parsed_acs: list[dict]) -> dict:
    offenders = []
    for entry in parsed_acs:
        parsed = entry.get("parsed")
        if not parsed:
            continue
        for clause_name in ("when", "then"):
            clause = parsed[clause_name]
            if CLAUSE_CONJUNCTIONS.search(clause):
                offenders.append((entry["index"], clause_name, clause))

    triggered = len(offenders) > 0
    if triggered:
        # Show up to 2 examples to keep the report readable.
        examples = "; ".join(
            f"AC #{i} {clause_name!r}: {clause!r}"
            for i, clause_name, clause in offenders[:2]
        )
        more = f" (+{len(offenders) - 2} more)" if len(offenders) > 2 else ""
        evidence = f"{len(offenders)} compound clause(s) found — {examples}{more}"
    else:
        evidence = "no 'and' / 'or' inside When or Then clauses"

    return {
        "name": "compound_gwt",
        "triggered": triggered,
        "severity": "high",
        "evidence": evidence,
    }


def smell_too_many_acs(parsed_acs: list[dict]) -> dict:
    n = len(parsed_acs)
    triggered = n > MAX_ACS
    evidence = (
        f"{n} acceptance criteria (threshold: {MAX_ACS})"
        if triggered
        else f"{n} acceptance criteria — within threshold of {MAX_ACS}"
    )
    return {
        "name": "too_many_acs",
        "triggered": triggered,
        "severity": "high",
        "evidence": evidence,
    }


def _persona_key(given: str) -> str:
    """Reduce a Given clause to a stable persona key (the head noun).

    'a logged-in user'                 -> 'user'
    'a user on the login screen'       -> 'user'
    'an admin'                         -> 'admin'
    'a reviewer with admin privileges' -> 'reviewer'
    'the project owner'                -> 'owner'

    Strategy: strip determiner, cut at the first whitespace-bounded preposition
    or conjunction (so adjectives stay attached but contextual phrases drop),
    then take the last word — typically the head noun.
    """
    g = given.lower().strip()
    g = re.sub(r"^(?:a|an|the)\s+", "", g)
    # Whitespace-bounded so we don't break hyphenated words like 'logged-in'.
    # Also cut at participle phrases ('admin viewing a document') by treating
    # any whitespace-bounded -ing word as a boundary.
    g = re.split(
        r"\s+(?:on|in|of|for|at|from|with|who|that|and)\s+|\s+\w+ing\s+|,",
        g, maxsplit=1,
    )[0].strip()
    parts = g.split()
    return parts[-1] if parts else g


def smell_multiple_personas(parsed_acs: list[dict]) -> dict:
    keys: list[str] = []
    for entry in parsed_acs:
        parsed = entry.get("parsed")
        if not parsed:
            continue
        keys.append(_persona_key(parsed["given"]))
    distinct = sorted({k for k in keys if k})
    triggered = len(distinct) >= PERSONA_DISTINCT_THRESHOLD
    if triggered:
        evidence = f"{len(distinct)} distinct personas in Given clauses: {', '.join(distinct)}"
    else:
        evidence = (
            f"single persona ({distinct[0]})" if distinct
            else "no parseable personas"
        )
    return {
        "name": "multiple_personas",
        "triggered": triggered,
        "severity": "medium",
        "evidence": evidence,
    }


def smell_sprawling_description(ticket: dict) -> dict:
    desc = ticket.get("description") or ""
    words = len(desc.split())
    headers = len(re.findall(r"(?m)^#{1,6}\s", desc))
    triggered = words > MAX_DESCRIPTION_WORDS or headers > MAX_DESCRIPTION_HEADERS
    if triggered:
        reasons = []
        if words > MAX_DESCRIPTION_WORDS:
            reasons.append(f"{words} words (>{MAX_DESCRIPTION_WORDS})")
        if headers > MAX_DESCRIPTION_HEADERS:
            reasons.append(f"{headers} markdown headers (>{MAX_DESCRIPTION_HEADERS})")
        evidence = "; ".join(reasons)
    else:
        evidence = f"{words} words, {headers} headers — compact"
    return {
        "name": "sprawling_description",
        "triggered": triggered,
        "severity": "medium",
        "evidence": evidence,
    }


def smell_mixed_crud(ticket: dict, parsed_acs: list[dict]) -> dict:
    text_blobs = [ticket.get("title", ""), ticket.get("description", "")]
    for entry in parsed_acs:
        text_blobs.append(entry.get("raw", ""))
    haystack = " ".join(b for b in text_blobs if isinstance(b, str)).lower()
    tokens = set(re.findall(r"[a-zA-Z]+", haystack))
    categories_present = sorted(
        cat for cat, lex in CRUD_CATEGORIES.items() if tokens & lex
    )
    triggered = len(categories_present) >= CRUD_DISTINCT_THRESHOLD
    if triggered:
        evidence = f"{len(categories_present)} CRUD operations present: {', '.join(categories_present)}"
    elif categories_present:
        evidence = f"only {len(categories_present)} CRUD operation(s) present: {', '.join(categories_present)}"
    else:
        evidence = "no clear CRUD operations detected"
    return {
        "name": "mixed_crud",
        "triggered": triggered,
        "severity": "medium",
        "evidence": evidence,
    }


def smell_oversized_estimate(ticket: dict) -> dict:
    est = ticket.get("estimate")
    if est is None:
        return {
            "name": "oversized_estimate",
            "triggered": False,
            "severity": "high",
            "evidence": "no estimate provided",
        }
    triggered = est > MAX_ESTIMATE
    evidence = (
        f"estimate {est} > threshold {MAX_ESTIMATE}"
        if triggered
        else f"estimate {est} ≤ threshold {MAX_ESTIMATE}"
    )
    return {
        "name": "oversized_estimate",
        "triggered": triggered,
        "severity": "high",
        "evidence": evidence,
    }


# ---------- Verdict ----------

def compute_verdict(smells: list[dict]) -> str:
    triggered = [s for s in smells if s["triggered"]]
    high = sum(1 for s in triggered if s["name"] in HIGH_SMELLS)
    medium = sum(1 for s in triggered if s["name"] in MEDIUM_SMELLS)

    if high >= 2 or (high >= 1 and medium >= 2):
        return "slice"
    if high >= 1 or medium >= 2:
        return "consider"
    return "no-slice"


# ---------- Main ----------

def analyze(ticket: dict) -> dict:
    schema_valid, errors, parsed_acs = validate_schema(ticket)

    # If schema fails on AC parsing, we still run the smells we can; many of them
    # rely on parsed ACs and will simply find nothing. The model should treat
    # schema_valid=False as a halt condition, but we don't punish it with an empty report.
    smells = [
        smell_multi_verb_title(ticket),
        smell_compound_gwt(parsed_acs),
        smell_too_many_acs(parsed_acs),
        smell_multiple_personas(parsed_acs),
        smell_sprawling_description(ticket),
        smell_mixed_crud(ticket, parsed_acs),
        smell_oversized_estimate(ticket),
    ]

    verdict = compute_verdict(smells) if schema_valid else "halt-fix-schema"

    # Stable content hash so the model can derive a placeholder ID when needed.
    payload_for_hash = json.dumps(
        {"title": ticket.get("title", ""), "acs": [e["raw"] for e in parsed_acs]},
        sort_keys=True, ensure_ascii=False,
    )
    content_hash = hashlib.sha1(payload_for_hash.encode("utf-8")).hexdigest()[:8]

    return {
        "schema_valid": schema_valid,
        "errors": errors,
        "parent_id": ticket.get("id"),
        "content_hash": content_hash,
        "smells": smells,
        "verdict": verdict,
        "parsed_acs": parsed_acs,
    }


def _read_input(path: str | None) -> dict:
    if path and path != "-":
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.load(sys.stdin)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", "-i", default=None,
                    help="path to ticket JSON (use '-' or omit for stdin)")
    args = ap.parse_args()

    try:
        ticket = _read_input(args.input)
    except FileNotFoundError:
        print(json.dumps({"error": f"input file not found: {args.input}"}), file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"input is not valid JSON: {e}"}), file=sys.stderr)
        return 1

    report = analyze(ticket)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
