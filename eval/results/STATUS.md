# Eval progress

| Phase | Status | Notes |
|---|---|---|
| Methodology defined | ✓ | See `METHODOLOGY.md` |
| 17 test cases authored | ✓ | 8 SLICE / 4 CONSIDER / 3 NO_SLICE / 2 HALT across 10 domains |
| Eval harness — smell_check | ✓ | `harness/run_smell_check_eval.py` |
| Smell-check verdict accuracy measured | ✓ | 14/17 overall; see `smell_check_summary.md` |
| Detector defect documented | ✓ | Persona extractor head-noun heuristic misfires on trailing prepositional phrases |
| Baseline outputs generated | — | Pending |
| Skill outputs generated | — | Pending |
| LLM-as-judge rubric applied | — | Pending |
| Aggregated scores per criterion | — | Pending |
| Hypothesis check (H1–H6) | — | Pending |
| README updated with final numbers | partial | Smell-check results landed; baseline comparison pending |

## Known issues uncovered by the eval

1. **Persona extractor false positives.** `_persona_key()` in `smell_check.py` grabs the wrong noun when the Given clause has a trailing prepositional phrase (`"a user with text in the search bar"` → `"bar"`) or possessive (`"a user without download permission"` → `"permission"`). Causes false `multiple_personas` triggers on small tickets. **Status:** documented, not yet patched.
2. **Verdict math over-escalates small tickets with one compound clause.** A single AC with a compound Then can trigger `compound_gwt` (high severity), which alone is enough to escalate the verdict from `no-slice` to `consider` or `slice`. The math could weight differently — e.g., require ≥3 compound clauses before `compound_gwt` counts as high. **Status:** documented; design discussion needed.
3. **Multi-verb title detection counts verb-like nouns.** Titles like "Add CSV export" trip `multi_verb_title` because `export` is in the action-verb list. The current logic doesn't distinguish noun-uses from verb-uses. **Status:** documented; would need POS-tagging or a tighter heuristic.
