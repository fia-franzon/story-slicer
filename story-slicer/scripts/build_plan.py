#!/usr/bin/env python3
"""build_plan.py — validate child ticket drafts, assign IDs, compute coverage, render artifacts.

Input is a single JSON document with the shape:

  {
    "parent":   { ...parent ticket conforming to schema... },
    "children": [
      {
        "title": "...",
        "description": "...",
        "acceptance_criteria": ["Given ... When ... Then ..."],
        "covers": [1, 3],               # 1-based indices into parent.acceptance_criteria
        "split_pattern": "Happy path",  # one of the patterns from references/split-patterns.md
        "labels":   [...],              # optional; inherited if absent
        "estimate": 3                   # optional
      },
      ...
    ],
    "open_questions":      ["...", "..."],   # optional
    "alternative_slices":  [...]             # optional
  }

The script validates everything, assigns deterministic IDs, builds the coverage
matrix, and writes:

  <out>/slice-plan.md
  <out>/children/<ID>.md (one per child)

Hard errors (non-zero exit):
  - parent fails schema validation,
  - any child fails schema validation,
  - any parent AC index is uncovered,
  - any child references an out-of-range AC index.

The model should never paper over these — every error names a specific fix.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

# Import sibling module
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from smell_check import analyze, parse_gwt, validate_schema  # noqa: E402


REQUIRED_CHILD_FIELDS = ("title", "description", "acceptance_criteria", "covers")


def validate_child(child: Any, idx: int, n_parent_acs: int) -> list[str]:
    """Return a list of error strings for this child (empty if it's clean)."""
    errors: list[str] = []
    label = f"child #{idx}"
    if not isinstance(child, dict):
        return [f"{label} must be a JSON object"]

    for f in REQUIRED_CHILD_FIELDS:
        if f not in child:
            errors.append(f"{label} missing required field: {f}")

    title = child.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append(f"{label} title must be a non-empty string")

    desc = child.get("description")
    if not isinstance(desc, str):
        errors.append(f"{label} description must be a string")

    acs = child.get("acceptance_criteria", [])
    if not isinstance(acs, list) or not acs:
        errors.append(f"{label} acceptance_criteria must be a non-empty list")
    else:
        for j, ac in enumerate(acs, start=1):
            if not isinstance(ac, str) or parse_gwt(ac) is None:
                preview = (ac[:60] + "…") if isinstance(ac, str) and len(ac) > 60 else repr(ac)
                errors.append(f"{label} AC #{j} is not in Given/When/Then form: {preview}")

    covers = child.get("covers", [])
    if not isinstance(covers, list) or not covers:
        errors.append(f"{label} covers must be a non-empty list of parent AC indices")
    else:
        for c in covers:
            if not isinstance(c, int) or c < 1 or c > n_parent_acs:
                errors.append(
                    f"{label} covers index {c!r} is out of range (parent has {n_parent_acs} ACs, 1-indexed)"
                )

    estimate = child.get("estimate")
    if estimate is not None and not isinstance(estimate, (int, float)):
        errors.append(f"{label} estimate, when present, must be a number")

    return errors


def assign_ids(parent_id: str | None, content_hash: str, n: int) -> list[str]:
    prefix = parent_id if parent_id else f"SLICE-{content_hash}"
    return [f"{prefix}-S{i:02d}" for i in range(1, n + 1)]


def build_coverage_matrix(parent_acs: list[dict], children: list[dict], child_ids: list[str]) -> list[list[bool]]:
    """rows = parent ACs, cols = children. cell True if child covers that parent AC."""
    matrix: list[list[bool]] = []
    for entry in parent_acs:
        i = entry["index"]
        row = [i in child.get("covers", []) for child in children]
        matrix.append(row)
    return matrix


def find_uncovered(parent_acs: list[dict], matrix: list[list[bool]]) -> list[int]:
    return [parent_acs[r]["index"] for r, row in enumerate(matrix) if not any(row)]


# ---------- Markdown rendering ----------

def _md_escape_table_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def render_coverage_matrix(parent_acs: list[dict], children: list[dict], child_ids: list[str], matrix: list[list[bool]]) -> str:
    short_ids = [cid.rsplit("-", 1)[-1] for cid in child_ids]  # "S01", "S02", ...
    header = "| # | Parent scenario (G/W/T) | " + " | ".join(short_ids) + " |"
    sep = "|---|" + "---|" * (1 + len(short_ids))

    lines = [header, sep]
    for r, entry in enumerate(parent_acs):
        i = entry["index"]
        scenario = _md_escape_table_cell(entry["raw"])
        row_marks = ["✓" if matrix[r][c] else "" for c in range(len(children))]
        lines.append(f"| {i} | {scenario} | " + " | ".join(row_marks) + " |")

    # Footer row: which split pattern each child uses (so the reasoning is visible)
    pattern_cells = [_md_escape_table_cell(child.get("split_pattern", "—")) for child in children]
    lines.append("| — | _split pattern_ | " + " | ".join(pattern_cells) + " |")
    return "\n".join(lines)


def render_smell_report(report: dict) -> str:
    rows = ["| Smell | Triggered | Severity | Evidence |", "|---|---|---|---|"]
    for s in report["smells"]:
        rows.append(
            f"| {s['name']} | {'✓' if s['triggered'] else '·'} | {s['severity']} | {_md_escape_table_cell(s['evidence'])} |"
        )
    return "\n".join(rows)


def render_child_md(child: dict, child_id: str, parent: dict) -> str:
    labels = child.get("labels") or parent.get("labels") or []
    parent_id = parent.get("id") or "—"
    estimate = child.get("estimate")
    estimate_str = f"{estimate}" if estimate is not None else "—"
    pattern = child.get("split_pattern", "—")
    covers = ", ".join(str(c) for c in child.get("covers", []))

    lines = [
        f"# {child_id}: {child['title']}",
        "",
        f"- **Parent:** {parent_id}",
        f"- **Split pattern:** {pattern}",
        f"- **Covers parent ACs:** {covers}",
        f"- **Estimate:** {estimate_str}",
        f"- **Labels:** {', '.join(labels) if labels else '—'}",
        "",
        "## Description",
        "",
        child["description"].strip(),
        "",
        "## Acceptance criteria",
        "",
    ]
    for ac in child["acceptance_criteria"]:
        lines.append(f"- {ac}")
    lines.append("")
    return "\n".join(lines)


def render_plan(parent: dict, children: list[dict], child_ids: list[str], parent_acs: list[dict],
                matrix: list[list[bool]], report: dict, open_questions: list[str],
                alternative_slices: list[dict]) -> str:
    parent_id = parent.get("id") or f"SLICE-{report['content_hash']}"
    triggered = [s for s in report["smells"] if s["triggered"]]

    parts: list[str] = []
    parts.append(f"# Slice plan for {parent_id}: {parent.get('title', '').strip()}")
    parts.append("")
    parts.append(f"- **Verdict:** `{report['verdict']}`")
    parts.append(f"- **Children:** {len(children)} ({', '.join(child_ids)})")
    parts.append(f"- **Smells triggered:** {len(triggered)} of {len(report['smells'])}")
    parts.append("")
    parts.append("## Smell report")
    parts.append("")
    parts.append(render_smell_report(report))
    parts.append("")
    parts.append("## Coverage matrix")
    parts.append("")
    parts.append("Rows are the parent's Given/When/Then scenarios. A check means the child carries that scenario forward (so it doubles as the test plan).")
    parts.append("")
    parts.append(render_coverage_matrix(parent_acs, children, child_ids, matrix))
    parts.append("")
    parts.append("## Children")
    parts.append("")
    for child, cid in zip(children, child_ids):
        parts.append(f"### {cid}: {child['title']}")
        parts.append("")
        parts.append(f"- **Split pattern:** {child.get('split_pattern', '—')}")
        parts.append(f"- **Covers parent ACs:** {', '.join(str(c) for c in child.get('covers', []))}")
        if child.get("estimate") is not None:
            parts.append(f"- **Estimate:** {child['estimate']}")
        parts.append("")
        parts.append(child["description"].strip())
        parts.append("")
        parts.append("**Acceptance criteria**")
        parts.append("")
        for ac in child["acceptance_criteria"]:
            parts.append(f"- {ac}")
        parts.append("")

    if open_questions:
        parts.append("## Open questions for engineering")
        parts.append("")
        parts.append("Each item below should be posted as its own comment on the parent ticket so it gets its own discussion thread.")
        parts.append("")
        for q in open_questions:
            parts.append(f"- {q.strip()}")
        parts.append("")

    if alternative_slices:
        parts.append("## Alternative slices considered (not acted on)")
        parts.append("")
        parts.append("These are sketches the model thought about but did not commit to as children. Surface them as separate comments on the parent ticket — discussion fodder, not actions.")
        parts.append("")
        for alt in alternative_slices:
            parts.append(f"### {alt.get('label', 'Alternative')}")
            parts.append("")
            if alt.get("rationale"):
                parts.append(f"_Why considered, why not chosen:_ {alt['rationale']}")
                parts.append("")
            for sketch in alt.get("sketch", []) or []:
                parts.append(f"- {sketch}")
            parts.append("")

    parts.append("## Comments to post on parent")
    parts.append("")
    parts.append("If an Atlassian MCP is connected, the agent posts these directly. Otherwise, copy-paste them into the parent ticket manually.")
    parts.append("")
    parts.append("**Summary comment.**")
    parts.append("")
    parts.append(f"Sliced this into {len(children)} children: {', '.join(child_ids)}.")
    parts.append("")
    if triggered:
        top = sorted(triggered, key=lambda s: 0 if s['severity'] == 'high' else 1)[:3]
        parts.append("Top smells that triggered:")
        for s in top:
            parts.append(f"- **{s['name']}** ({s['severity']}): {s['evidence']}")
        parts.append("")
    parts.append("Coverage matrix (rows: parent scenarios; columns: children):")
    parts.append("")
    parts.append(render_coverage_matrix(parent_acs, children, child_ids, matrix))
    parts.append("")
    if open_questions:
        parts.append("**Open question comments (one per question, posted separately):**")
        parts.append("")
        for q in open_questions:
            parts.append(f"> {q.strip()}")
        parts.append("")
    if alternative_slices:
        parts.append("**Alternative-slice comments (one per alternative, posted separately):**")
        parts.append("")
        for alt in alternative_slices:
            parts.append(f"> _{alt.get('label', 'Alternative')}_ — {alt.get('rationale', '')}")
            for sketch in alt.get("sketch", []) or []:
                parts.append(f"> - {sketch}")
            parts.append("")

    return "\n".join(parts).rstrip() + "\n"


# ---------- Main ----------

def build(input_path: str, out_dir: str) -> dict:
    with open(input_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    if not isinstance(doc, dict) or "parent" not in doc or "children" not in doc:
        raise SystemExit("input must be a JSON object with 'parent' and 'children' keys")

    parent = doc["parent"]
    children = doc["children"]
    open_questions = doc.get("open_questions", []) or []
    alternative_slices = doc.get("alternative_slices", []) or []

    if not isinstance(children, list) or not children:
        raise SystemExit("'children' must be a non-empty list")

    # Run smell + parse on parent. analyze() does the schema validation work.
    report = analyze(parent)
    if not report["schema_valid"]:
        msg = "parent ticket failed schema validation:\n  - " + "\n  - ".join(report["errors"])
        raise SystemExit(msg)

    # Only keep ACs that parsed (schema_valid=True implies all parsed)
    parent_acs = [e for e in report["parsed_acs"] if e.get("parsed") is not None]

    # Validate every child.
    child_errors: list[str] = []
    for i, child in enumerate(children, start=1):
        child_errors.extend(validate_child(child, i, len(parent_acs)))
    if child_errors:
        msg = "child ticket(s) failed validation:\n  - " + "\n  - ".join(child_errors)
        raise SystemExit(msg)

    # Assign IDs deterministically.
    child_ids = assign_ids(parent.get("id"), report["content_hash"], len(children))

    # Build coverage matrix.
    matrix = build_coverage_matrix(parent_acs, children, child_ids)
    uncovered = find_uncovered(parent_acs, matrix)
    if uncovered:
        msg = ("the slice is invalid: parent AC(s) not covered by any child: "
               f"{uncovered}. Add these indices to a child's 'covers' list, or write a new child for them.")
        raise SystemExit(msg)

    # Write artifacts.
    os.makedirs(out_dir, exist_ok=True)
    children_dir = os.path.join(out_dir, "children")
    os.makedirs(children_dir, exist_ok=True)

    plan_md = render_plan(parent, children, child_ids, parent_acs, matrix, report,
                          open_questions, alternative_slices)
    with open(os.path.join(out_dir, "slice-plan.md"), "w", encoding="utf-8") as f:
        f.write(plan_md)

    for child, cid in zip(children, child_ids):
        with open(os.path.join(children_dir, f"{cid}.md"), "w", encoding="utf-8") as f:
            f.write(render_child_md(child, cid, parent))

    return {
        "ok": True,
        "parent_id": parent.get("id") or f"SLICE-{report['content_hash']}",
        "child_ids": child_ids,
        "verdict": report["verdict"],
        "uncovered": uncovered,
        "smells_triggered": [s["name"] for s in report["smells"] if s["triggered"]],
        "out_dir": out_dir,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", "-i", required=True, help="path to working JSON (parent + children)")
    ap.add_argument("--out", "-o", required=True, help="output directory for slice-plan.md and children/")
    args = ap.parse_args()

    try:
        result = build(args.input, args.out)
    except FileNotFoundError as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(json.dumps({"ok": False, "error": f"input is not valid JSON: {e}"}), file=sys.stderr)
        return 1
    except SystemExit as e:
        # Re-raise if it's a non-string (default exit), otherwise format as error.
        msg = str(e) if e.code is not None and not isinstance(e.code, int) else "unknown error"
        print(json.dumps({"ok": False, "error": msg}), file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
