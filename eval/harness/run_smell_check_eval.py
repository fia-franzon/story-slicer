#!/usr/bin/env python3
"""run_smell_check_eval.py — run smell_check.py on every test case and compare
to the predicted ground truth.

Outputs:
  results/smell_check_results.json   — full per-case detector output + comparison
  results/smell_check_summary.md     — readable table summary
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parent.parent
TEST_CASES_DIR = EVAL_ROOT / "test-cases"
RESULTS_DIR = EVAL_ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Import smell_check from the skill
SKILL_SCRIPTS = Path("/sessions/wonderful-gracious-gauss/mnt/.claude/skills/story-slicer/scripts")
sys.path.insert(0, str(SKILL_SCRIPTS))
from smell_check import analyze  # noqa: E402


def strip_eval_fields(ticket: dict) -> dict:
    """Remove _ground_truth and _source so the detector sees what the skill would see."""
    return {k: v for k, v in ticket.items() if not k.startswith("_")}


def main() -> None:
    case_files = sorted(TEST_CASES_DIR.glob("*.json"))
    if not case_files:
        print("No test cases found.")
        return

    results = []
    for f in case_files:
        with f.open() as fh:
            case = json.load(fh)

        ticket = strip_eval_fields(case)
        report = analyze(ticket)

        gt = case["_ground_truth"]
        expected_verdict = gt["expected_verdict"]
        actual_verdict = report["verdict"]
        verdict_match = expected_verdict == actual_verdict

        expected_smells = set(gt.get("expected_smells", []))
        actual_smells = {s["name"] for s in report["smells"] if s["triggered"]}
        smell_extra = sorted(actual_smells - expected_smells)
        smell_missed = sorted(expected_smells - actual_smells)

        results.append({
            "case_id": case["id"],
            "label": gt["label"],
            "domain": gt["domain"],
            "expected_verdict": expected_verdict,
            "actual_verdict": actual_verdict,
            "verdict_match": verdict_match,
            "expected_smells": sorted(expected_smells),
            "actual_smells": sorted(actual_smells),
            "smells_unexpected": smell_extra,
            "smells_missed": smell_missed,
            "smell_evidence": {s["name"]: s["evidence"] for s in report["smells"] if s["triggered"]},
        })

    # Aggregate accuracy by label
    by_label: dict[str, dict] = {}
    for r in results:
        bl = by_label.setdefault(r["label"], {"total": 0, "match": 0, "cases": []})
        bl["total"] += 1
        if r["verdict_match"]:
            bl["match"] += 1
        bl["cases"].append(r["case_id"])

    overall_total = len(results)
    overall_match = sum(1 for r in results if r["verdict_match"])

    summary = {
        "overall": {"total": overall_total, "match": overall_match, "accuracy": overall_match / overall_total},
        "by_label": {
            label: {
                "total": d["total"],
                "match": d["match"],
                "accuracy": d["match"] / d["total"],
            }
            for label, d in by_label.items()
        },
        "results": results,
    }

    out_json = RESULTS_DIR / "smell_check_results.json"
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")

    # Markdown summary
    md = []
    md.append("# Smell-check eval — results\n")
    md.append(f"**Overall verdict-match accuracy:** {overall_match}/{overall_total} = {100*overall_match/overall_total:.1f}%\n")
    md.append("\n## Accuracy by ground-truth label\n")
    md.append("\n| Label | Total | Match | Accuracy |")
    md.append("|---|---|---|---|")
    for label in ("SLICE", "CONSIDER", "NO_SLICE", "HALT"):
        if label in by_label:
            d = by_label[label]
            md.append(f"| {label} | {d['total']} | {d['match']} | {100*d['match']/d['total']:.1f}% |")

    md.append("\n## Per-case results\n")
    md.append("\n| Case | Label | Domain | Predicted | Actual | Match | Notes |")
    md.append("|---|---|---|---|---|---|---|")
    for r in results:
        notes = []
        if r["smells_unexpected"]:
            notes.append(f"+{', '.join(r['smells_unexpected'])}")
        if r["smells_missed"]:
            notes.append(f"−{', '.join(r['smells_missed'])}")
        notes_str = "; ".join(notes) if notes else "—"
        match = "✓" if r["verdict_match"] else "✗"
        md.append(f"| {r['case_id']} | {r['label']} | {r['domain']} | `{r['expected_verdict']}` | `{r['actual_verdict']}` | {match} | {notes_str} |")

    md.append("\n## Mismatch analysis\n")
    mismatches = [r for r in results if not r["verdict_match"]]
    if not mismatches:
        md.append("No mismatches.")
    else:
        for r in mismatches:
            md.append(f"\n### {r['case_id']}")
            md.append(f"- Predicted: `{r['expected_verdict']}`")
            md.append(f"- Actual: `{r['actual_verdict']}`")
            md.append("- Triggered smells (with evidence):")
            for name, ev in r["smell_evidence"].items():
                md.append(f"  - **{name}**: {ev}")

    (RESULTS_DIR / "smell_check_summary.md").write_text("\n".join(md) + "\n")

    print(f"Wrote {out_json}")
    print(f"Wrote {RESULTS_DIR / 'smell_check_summary.md'}")
    print(f"\nOverall: {overall_match}/{overall_total} verdict matches")


if __name__ == "__main__":
    main()
