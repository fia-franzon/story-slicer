# story-slicer eval — methodology

This document specifies the evaluation we ran to compare the **story-slicer skill** against an **unscaffolded Claude baseline**. The goal is to support the README's claims about the skill's behavior with reproducible, auditable evidence — not impressive-sounding numbers.

> **In one sentence:** for each parent ticket in our test set, we produced two slicing outputs — one from unscaffolded Claude, one from the scaffolded skill — and scored both against a fixed rubric using an LLM judge that didn't know which output came from which.

---

## 1. Research question

> When a backlog ticket needs slicing, does the scaffolding in the story-slicer skill produce **measurably better** child tickets than an unscaffolded LLM call?

"Better" is operationalized by the five-question rubric in §4.

## 2. Test-case design

### 2.1 Categories

Every test case has a ground-truth label indicating what the skill *should* do with it:

| Label | What the skill should do | Target count |
|---|---|---|
| `SLICE` | Detect multiple smells, produce ≥2 vertical-slice children | 8 |
| `CONSIDER` | Detect 1 high or ≥2 medium smells, slice or surface the option | 4 |
| `NO_SLICE` | Decline (caution path) — the ticket is fine as-is | 3 |
| `HALT` | Halt because parent ACs aren't in Given/When/Then form | 2 |
| **Total** | | **17** |

The non-slice categories matter as much as `SLICE`. The risk of an over-eager skill is real: if a model is rewarded only for slicing, it will slice tickets that don't need it. The `NO_SLICE` and `HALT` cases test whether the skill respects the caution path.

### 2.2 Domain coverage

To avoid overfitting to one product area, test cases span at least eight domains. At least one case per domain:

- E-commerce / checkout
- User authentication / SSO / 2FA
- Internal admin tooling
- Data import / export / migration
- Email and push notifications
- Reporting / dashboards / analytics
- Mobile-specific features
- API integration / webhooks
- Onboarding / activation
- Document / file management

### 2.3 Authoring rules (the "blind enough" compromise)

Ideally the test-case author is different from the skill author. We are the same person, which weakens the eval. To compensate:

1. **Source from outside the skill's rubric.** Each parent ticket is drafted from a public PM template, a real Jira/Linear/GitHub issue (anonymized), or a generic backlog example — *not* by working backwards from the seven smells.
2. **Record the source.** Every test case includes a `_source` field naming where the ticket came from (template name, anonymized URL, or "generic").
3. **No post-hoc tuning.** After the first-pass authoring, test cases are not adjusted to make the skill look better. If a case is mislabeled or unclear in retrospect, it's removed entirely (and the removal is logged), not edited.
4. **Predeclare expectations.** Before running the skill, each test case carries an `_expected` block: predicted verdict, predicted smells, predicted approximate child count. The script compares actual to predicted; mismatches are surfaced, not hidden.

### 2.4 Test-case schema

Each test case is a single JSON file in `test-cases/<case-id>.json` shaped like:

```json
{
  "id": "ECOM-001",
  "title": "Build, design, and launch a complete checkout experience...",
  "description": "...",
  "acceptance_criteria": ["Given ... When ... Then ...", "..."],
  "labels": ["..."],
  "estimate": 13,

  "_ground_truth": {
    "label": "SLICE",
    "domain": "ecommerce",
    "expected_verdict": "slice",
    "expected_smells": ["multi_verb_title", "compound_gwt", "too_many_acs", "..."],
    "expected_children_range": [5, 8],
    "notes": "Multi-persona, conjunction-heavy ACs across 11 criteria."
  },

  "_source": "Generic Stripe-style checkout PRD; anonymized."
}
```

The `_ground_truth` and `_source` blocks are stripped before the ticket is shown to the slicer.

## 3. The two pipelines under test

### 3.1 Baseline: unscaffolded Claude

The baseline runs the same model with no scripts, no rubric, no schema enforcement, and no reference to the skill. The prompt is the same for every case:

> Here is a backlog ticket. Decide whether it should be broken into smaller stories. If yes, produce 2–8 child stories, each with a title and acceptance criteria in Given/When/Then form, plus a brief rationale. If no, explain why.
>
> [parent ticket follows]

That's it. No coverage matrix, no split-pattern catalog, no smell detector, no open questions, no alternative slices. This represents the realistic "ask a chatbot to help me slice this story" baseline.

### 3.2 Skill: scaffolded pipeline

The skill runs the full flow as documented in `story-slicer/SKILL.md`:

1. `smell_check.py` on the parent → smell report + verdict.
2. If verdict is `slice` or `consider`, the agent picks split patterns from the catalog and drafts children.
3. `build_plan.py` validates every child, computes the coverage matrix, fails on uncovered parent ACs.
4. The agent records open questions and alternative slices.

Both pipelines see the parent ticket with the `_ground_truth` and `_source` blocks stripped.

## 4. Rubric

Each pipeline's output is scored on five binary questions. A "yes" is worth 1 point; "no" is 0. Per question, the judge also records 1–2 sentences of reasoning.

| # | Question | What "yes" looks like |
|---|---|---|
| R1 | **Detection accuracy.** Did the output correctly decide whether the ticket needs slicing? | Output matches the ground-truth label (`SLICE` / `CONSIDER` ⇒ produces children; `NO_SLICE` / `HALT` ⇒ declines or asks to fix ACs). |
| R2 | **Vertical slicing.** Are the resulting children vertical slices, each delivering user-facing value end-to-end? | No child is purely FE, BE, infra, or "wire up the API." Each could conceivably be merged and demoed independently. |
| R3 | **Coverage of parent ACs.** Is every parent AC covered by at least one child? | Every Given/When/Then in the parent maps to at least one child AC. No silent drops. |
| R4 | **Testable G/W/T per child.** Do all child ACs parse as Given/When/Then? | Every child has structured ACs a QA engineer could turn into test cases without further interpretation. |
| R5 | **Uncertainty handling.** Did the slicer surface what it couldn't decide, vs. fabricating confident answers? | Explicit open questions or flagged assumptions appear in the output when the parent has gaps (missing carrier, unspecified service contract, etc.). |

R1, R3, R4 are checkable automatically against the test-case ground truth. R2 and R5 are judgment calls — applied by the LLM judge with explicit reasoning, so a human can audit.

**Score.** Each output gets a score of 0–5. The headline number is the **mean score across all test cases**, separately for baseline and skill. We also report **win rate** (per case, does the skill score strictly higher than baseline?) and **per-criterion accuracy** (how often each pipeline scores ≥1 on each Rx).

## 5. Judging protocol

### 5.1 Judge model

The judge is Claude (Sonnet), invoked separately from the slicing pipelines. The judge has no access to the skill's source code, smell rubric, or split-pattern catalog. It is given only:

- the parent ticket (with `_ground_truth` and `_source` stripped),
- the rubric (§4),
- one of the two slicing outputs (it doesn't know which).

### 5.2 Blinding

For each test case, the judge sees two judging passes, in randomized order. The judge does not know that two pipelines exist. From its perspective, each judging task is a fresh, independent grading. Outputs are tagged in the harness as `output_A` and `output_B` per case; the A/B → baseline/skill mapping is recorded separately and only joined at aggregation time.

This isn't a full double-blind — the same person designed the cases and the rubric — but it does remove the judge's ability to systematically favor either pipeline based on stylistic cues that say "this was made by the skill."

### 5.3 Judge output format

For each (test-case, output) pair, the judge produces:

```json
{
  "case_id": "ECOM-001",
  "output_tag": "A",
  "scores": {
    "R1": {"answer": "yes", "reasoning": "..."},
    "R2": {"answer": "yes", "reasoning": "..."},
    "R3": {"answer": "no",  "reasoning": "AC #11 (analytics) doesn't appear in any child."},
    "R4": {"answer": "yes", "reasoning": "..."},
    "R5": {"answer": "no",  "reasoning": "No open questions; assumes inventory service exists."}
  },
  "total": 3
}
```

Reasoning is mandatory on every question, including "yes" answers, so that a reviewer can spot-check.

## 6. Reproducibility

- All test cases, outputs, and judgments are committed to `eval/` as JSON files.
- The harness scripts (`harness/run_smell_check_eval.py`, `harness/run_judge.py`, `harness/aggregate.py`) are deterministic except for the LLM calls — which are non-deterministic by nature. Each run records the model and prompts used.
- The aggregated results are written to `results/REPORT.md` and `results/raw.json`.
- The skill being evaluated is pinned: the contents of `story-slicer/` at the commit hash recorded in `results/raw.json`.

To rerun:
```bash
cd eval
python3 harness/run_smell_check_eval.py   # automated smell-check accuracy
python3 harness/run_pipelines.py          # produces baseline + skill outputs per case
python3 harness/run_judge.py              # applies the rubric
python3 harness/aggregate.py              # builds REPORT.md
```

## 7. Threats to validity

Honest disclosure of where this eval falls short, so reviewers can weight the conclusions accordingly.

1. **The test-case author is the skill author.** Even with the "source from outside the rubric" rule and the `_source` field, some bias is unavoidable. Mitigation: every test-case file is committed unchanged after first-pass authoring; modifications are tracked via git.
2. **The judge is the same model family as the slicer.** Claude judging Claude's output has known biases (preferring more verbose output, agreeing with confident assertions). Mitigation: the judge's reasoning is recorded per question; a human reviewer can spot-check the calls where reasoning seems thin.
3. **The judge is not human.** A real grooming meeting would value things the LLM judge can't easily assess — team-fit, dependency risk, political nuance. The rubric is deliberately narrow to what an LLM can grade reliably.
4. **Single shot for both pipelines.** Both baseline and skill run once per case. Variance across runs is real (especially for the baseline). Mitigation: 17 cases is enough that single-shot noise should average out; results are reported with min/max alongside the mean.
5. **Domain skew.** Cases lean enterprise / B2B SaaS. A consumer app, gaming, or internal IT-ops backlog might behave differently.
6. **Baseline isn't optimized.** A more sophisticated baseline (chain-of-thought, few-shot examples, a custom system prompt) might close the gap. The chosen baseline represents "the average PM asking Claude for help without scaffolding," which is the realistic comparison; it's not the strongest possible LLM-only approach.
7. **No statistical significance testing.** With n=17 and binary outcomes, a confidence interval on a 30-point gap doesn't add much; we report raw counts and let the reader draw conclusions. If a future eval has more cases, add bootstrapped CIs.

## 8. Pre-registered hypotheses

What we predict the eval will show, written before any runs are scored. These are the claims the eval is designed to test.

| Hypothesis | Predicted outcome |
|---|---|
| H1 | Skill scores ≥ baseline on **R3 (coverage)** in every `SLICE` case. The hard fail in `build_plan.py` makes this mechanical. |
| H2 | Skill scores ≥ baseline on **R4 (testable ACs)** in every case, since the skill validates G/W/T format. |
| H3 | Skill scores higher than baseline on **R5 (uncertainty handling)** in most `SLICE` cases. Open Questions is a deliberate output channel; baseline has no equivalent. |
| H4 | Both pipelines are roughly even on **R2 (vertical slicing)** in most cases — the smarter baseline runs will produce vertical slices anyway; the skill's improvement is mostly when the parent ticket strongly tempts a horizontal split (multi-platform, multi-service tickets). |
| H5 | Skill performs much better on **`NO_SLICE` cases (R1)** because its caution path is explicit. Baseline tends to slice anyway because "the user asked for slicing." |
| H6 | Skill performs much better on **`HALT` cases** because schema validation is mechanical. Baseline tends to invent G/W/T for free-form ACs. |

After scoring, we report each hypothesis as confirmed / partially confirmed / refuted, with the supporting numbers.

---

## Status

| Phase | Status |
|---|---|
| Methodology defined (this doc) | ✓ |
| Test cases authored | _in progress_ |
| Eval harness built | _todo_ |
| Baseline outputs generated | _todo_ |
| Skill outputs generated | _todo_ |
| Judgments completed | _todo_ |
| Aggregated report written | _todo_ |
| README updated with real numbers | _todo_ |

Per-phase progress is tracked in `results/STATUS.md` as runs complete.
