# story-slicer

A Claude skill that takes one oversized backlog ticket and produces N smaller children that ship vertical user value, preserve every parent acceptance criterion (proven by a coverage matrix), and surface what the model couldn't decide as Open Questions for engineering instead of papering them over.

> Slice a too-big story without losing any acceptance criteria — and prove it.

---

## Why the project pivot

My original project failed because it was improperly scoped; despite being a PM, I let creep get the best of me and failed to define a concise enough happy path. I'm going to follow core PDLC principles: clear PRD, AC, and milestones.

**Organization**: The project folder got cluttered with references of what the tool could become rather than what it needs to be in V1. Furthermore, visiblity into what the AI was producing started to get foggy. Instead of breaking out versions into new documents, I'll be careful to figure out a way to balance keeping records (perhaps new folder structures?) and introducing clutter which ultimately confused the agent.

**Development**: Lastly, when moving to development, I'm going to keep a jira board of tickets and tackle them one at a time. I noticed that without more granular requirements of what each session had to build there was some struggle to understand what was being made. (i.e. instead of "build this piece x", prompt "build this piece x. this piece x is done when y. Test for y".

**Testing**: I developed on my personal laptop, and I found the output to not really be applicable to all organizations. My story slicer can actually be used pretty easily by anyone, but this project wasn't as universally applicable, which made testing on my work computer challenging. 

Anyways, a great project overall! Appreciate the sessions jamming and the learning. 

---

## 1. Context, user, and problem

**Who the user is.** Product managers, engineering leads, and agile coaches running backlog grooming or sprint refinement. The skill is built around Jira but the schema is portable to Linear, Asana, GitHub Issues, or any tracker with title / description / acceptance-criteria fields.

**The workflow we're improving.** When a ticket arrives in grooming labeled *"this is too big,"* the team has to break it down. The good version of that breakdown:

- preserves every acceptance criterion the team already agreed to,
- produces children that each ship vertical user value (so they can land independently),
- carries forward the test plan so QA isn't re-deriving it from scratch on every child,
- and surfaces unresolved questions *before* engineering starts coding.

Today this happens in a thirty-minute meeting with a whiteboard and Post-its, run by whoever's most patient or most senior in the room. Output quality is uneven, the slicing rubric is implicit, and *"did we miss anything?"* gets answered by vibes.

**Why it matters.**

- Oversized stories miss the sprint they're committed to and bleed into the next one — the most-cited reason in retros I've sat in on.
- Without Given/When/Then discipline on ACs, frontend, backend, and QA each interpret requirements differently. The bugs surface at integration, after the work is "done."
- Slicing is mentally expensive work that PMs procrastinate on, which is why groomings run long.
- INVEST principles (Independent, Negotiable, Valuable, Estimable, Small, Testable) are well-known but rarely operationalized. Teams discuss them; they don't *enforce* them.
- **AI without scaffolding makes this worse, not better.** Unscaffolded LLM slicing produces plausible-looking children that quietly drop ACs, split horizontally (FE-only, BE-only), or hide uncertainty behind confident prose. Those mistakes are harder to catch than a bad whiteboard session because the output *looks* right. This is the failure mode the skill is built to prevent.

---

## 2. Solution and design

**What I built.** A skill that turns one too-big parent ticket into:

1. A **smell report** that names *why* the ticket needs slicing — with cited evidence per smell, not just a verdict.
2. **N validated child tickets** in Given/When/Then form with deterministic IDs (`<parent>-S01`, `S02`, …).
3. A **coverage matrix** that proves no parent AC was dropped — every parent scenario maps to at least one child, or the build fails.
4. **Open Questions** queued as parent-ticket comments so each gets its own discussion thread before engineering starts.
5. **Alternative slices** the agent considered but rejected, surfaced as discussion fodder rather than hidden inside chain-of-thought.

**How it works.** The agent handles writing and judgment. Two Python scripts do the deterministic work — schema validation, smell detection, coverage math, ID generation — because LLMs are unreliable at exactly those things.

```
parent ticket
     │
     ▼
smell_check.py ──► JSON report: schema validity, 7 smells, verdict (slice|consider|no-slice|halt)
     │
     ▼
agent picks split patterns from references/split-patterns.md
agent drafts 2–8 child tickets, each with a `covers: [n, m]` list
     │
     ▼
build_plan.py ──► validates every child, assigns IDs, builds coverage matrix,
                   FAILS if any parent AC is uncovered
     │
     ▼
slice-plan.md + children/*.md  (plus queued parent comments)
     │
     ▼
agent presents plan → user approves → agent posts comments + creates children
```

**Key design choices.**

| Decision | Why |
|---|---|
| **Agent writes prose; scripts enforce invariants.** | The "agent + tools" pattern. The model is great at synthesis; it's unreliable at deterministic checks like "did every AC find a home?" The scripts make those checks un-fudgeable. |
| **Given/When/Then is mandatory.** | Vague ACs make slicing impossible (you can't preserve what you can't test). If the parent has free-form ACs, the skill halts and says so — it doesn't try to translate them itself. |
| **Vertical slicing only.** | Horizontal splits (FE-only, BE-only) look parallelizable but never ship user value on their own. The skill surfaces them as comments for the team to discuss; it never drafts them as children. |
| **Hard fail on uncovered parent ACs.** | The highest-stakes question in slicing is "did we drop anything?" `build_plan.py` exits non-zero if any parent AC index is missing from every child's `covers` list. |
| **Deterministic IDs (parent + content hash).** | Reruns are idempotent — important so retries don't duplicate Jira issues. |
| **Open Questions are first-class outputs.** | Without a sanctioned channel for "I don't know," the model fabricates plausible answers ("we'll use the existing inventory service") that derail teams after grooming. The skill makes uncertainty visible. |
| **Caution path on no-slice.** | If the smell report says the ticket doesn't need splitting, the skill declines politely and names the smells it checked. It does not invent reasons to slice anyway. |

**The seven splittability smells.**

| Smell | Severity | Triggers when… |
|---|---|---|
| `multi_verb_title` | high | Title joins ≥2 action verbs with `and` / `or` / `+` / `/` |
| `compound_gwt` | high | A When or Then clause contains `and` / `or` |
| `too_many_acs` | high | More than 5 acceptance criteria |
| `oversized_estimate` | high | Story-points estimate exceeds team threshold (default 8) |
| `multiple_personas` | medium | ≥2 distinct personas in the Given clauses |
| `sprawling_description` | medium | >200 words or >2 Markdown headers in the description |
| `mixed_crud` | medium | ≥3 of Create / Read / Update / Delete operations present |

Verdict math: ≥2 high (or 1 high + ≥2 medium) → `slice`. 1 high or ≥2 medium → `consider`. None → `no-slice`.

**The six split-pattern catalog** (from `references/split-patterns.md`): Workflow Steps, Happy path, Unhappy path, Data Variations, CRUD, Persona, plus Spike + Build for high-uncertainty cases. The agent picks one or combines several; the chosen pattern is recorded on each child as `split_pattern`.

---

## 3. Evaluation and results

### 3.1 What I evaluated

> Does the scaffolding in the story-slicer skill produce **measurably better** outputs than an unscaffolded LLM call on the same backlog ticket?

Full methodology, threats to validity, and pre-registered hypotheses live in [`eval/METHODOLOGY.md`](eval/METHODOLOGY.md). The short version follows.

### 3.2 Baseline

**Unscaffolded Claude** — same model, no scripts, no rubric, no schema enforcement. The prompt is the same for every case:

> *Here is a backlog ticket. Decide whether it should be broken into smaller stories. If yes, produce 2–8 child stories, each with a title and acceptance criteria in Given/When/Then form, plus a brief rationale. If no, explain why.*

This represents the realistic "PM asks a chatbot to help me slice this" baseline.

### 3.3 Test-case design

17 parent tickets across 4 ground-truth categories and 10 domains. Authored from public PM templates and anonymized real backlog examples, not by working backwards from the skill's smell rubric. Each case carries a pre-declared `_expected` block (predicted verdict, predicted smells, expected child count) and a `_source` field tracing where it came from.

| Category | Count | What the skill should do |
|---|---|---|
| `SLICE` | 8 | Detect multiple smells, produce vertical-slice children |
| `CONSIDER` | 4 | Detect 1 high or ≥2 medium smells; slice or surface the option |
| `NO_SLICE` | 3 | Decline (caution path) — ticket is fine as-is |
| `HALT` | 2 | Halt because ACs aren't in Given/When/Then form |

**Domains covered:** authentication, data import, notifications, reporting, mobile, API integration, onboarding, document collaboration, admin tooling, search.

Test-case files live in [`eval/test-cases/`](eval/test-cases/).

### 3.4 Rubric

Each pipeline's output (baseline and skill) is scored on five binary questions. Reasoning is recorded per question so a human can spot-check.

| # | Question | What "yes" looks like |
|---|---|---|
| R1 | **Detection accuracy.** Did the output correctly decide whether the ticket needs slicing? | Output matches the ground-truth label. |
| R2 | **Vertical slicing.** Are the children vertical slices, each delivering user-facing value end-to-end? | No FE-only, BE-only, or "wire up the API" children. Each could be merged and demoed independently. |
| R3 | **Coverage.** Is every parent AC covered by at least one child? | Every Given/When/Then maps to at least one child AC. No silent drops. |
| R4 | **Testable G/W/T per child.** Do all child ACs parse as Given/When/Then? | Every child has structured ACs a QA engineer could turn into test cases without further interpretation. |
| R5 | **Uncertainty handling.** Did the output surface what it couldn't decide, vs. fabricating confident answers? | Explicit open questions or flagged assumptions when the parent has gaps. |

R1, R3, R4 are checkable automatically. R2 and R5 are LLM-judge calls applied to both outputs blinded (the judge doesn't know which output came from which pipeline).

### 3.5 Results so far — smell-check verdict accuracy

The first measurement: how often does the skill's `smell_check.py` arrive at the ground-truth verdict label? This is the auto-graded portion of R1.

**Overall: 14 / 17 = 82.4%**

| Ground-truth label | n | Match | Accuracy |
|---|---|---|---|
| SLICE | 8 | 8 | **100%** |
| HALT | 2 | 2 | **100%** |
| CONSIDER | 4 | 3 | 75% |
| NO_SLICE | 3 | 1 | **33%** |

Full per-case table in [`eval/results/smell_check_summary.md`](eval/results/smell_check_summary.md).

### 3.6 What the results show

**Strengths.** The skill is *very* reliable on the cases that genuinely need slicing or halting:

- **8 / 8 on SLICE cases** — the seven smells catch every multi-verb / multi-persona / sprawling parent in the test set.
- **2 / 2 on HALT cases** — the G/W/T parser cleanly rejects free-form ACs and produces actionable error messages.

These two categories are the high-stakes cases. Missing a SLICE costs an over-large story in the sprint; missing a HALT costs a slicer trying to operate on vague requirements. The skill handles both correctly on every case in the set.

**The headline weakness: over-eagerness on small tickets.** The skill mislabeled **2 of 3 NO_SLICE cases** (33% accuracy). Two distinct causes:

1. **The persona extractor has a bug** — `_persona_key()` in `smell_check.py` runs a head-noun heuristic that grabs the wrong noun when the Given clause has a trailing prepositional phrase or possessive. *"Given a user with text in the search bar"* → extracts `"bar"` as a persona. *"Given a user without download permission"* → extracts `"permission"`. This causes false `multiple_personas` triggers on small tickets. Documented as an open defect; not yet fixed.
2. **Compound `Then` clauses appear in legitimately-small tickets.** A single AC that says *"the file downloads and respects column ordering and uses the current filter"* triggers `compound_gwt` — fairly. The compound clause is real. But on a single-AC, single-persona ticket, that one smell shouldn't escalate the whole thing to `slice`. The verdict math could weight differently.

**The borderline case (CONSIDER, 3/4).** One CONSIDER case (REPORT-002) got escalated to SLICE because its title contains two action verbs (*"Add CSV export"* → `add` + `export`). Author judgment was CONSIDER; detector says SLICE. The disagreement is itself informative — it surfaces a tension between "the rubric is well-defined" and "human PMs would call this a small story."

### 3.7 What's still in progress

The baseline-vs-skill rubric comparison is still pending. To run it I need to:

1. Produce the unscaffolded-Claude baseline output for each of the 12 sliceable cases (SLICE + CONSIDER).
2. Produce the scaffolded-skill output for the same 12 cases.
3. Apply the 5-question rubric to all 24 outputs, blinded.
4. Aggregate per-criterion scores and report.

Once that phase completes, this section will update with:

- Per-criterion comparison (skill vs. baseline on each of R1–R5)
- Win rate (per case, did the skill score strictly higher?)
- Hypothesis check (each of H1–H6 from the methodology confirmed / partial / refuted)

Tracking: see [`eval/results/STATUS.md`](eval/results/STATUS.md).

### 3.8 Threats to validity

Honest disclosure of where this eval falls short, so a reviewer can weight the conclusions accordingly. Full list in [`METHODOLOGY.md`](eval/METHODOLOGY.md) §7.

- **The test-case author is the skill author.** Even with the *source-from-outside-the-rubric* rule and the `_source` field, some bias is unavoidable.
- **Single LLM judge from the same model family** as the slicer. Mitigated by recording reasoning per rubric question for human spot-check.
- **Single shot for both pipelines.** Variance across runs is real, especially for the baseline. n=17 is the floor.
- **Cases skew B2B SaaS.** A consumer app or internal IT-ops backlog might behave differently.
- **Baseline isn't optimized** — represents "average PM asking Claude" rather than the strongest possible unscaffolded approach.

---

## 4. Artifact snapshot

### Sample input (illustrative test case)

```yaml
id: AUTH-001
title: Add SSO, 2FA, password reset, and account lockout to login
acceptance_criteria:
  - Given a user on the login page, When they click 'Sign in with Google' or
    'Sign in with Microsoft' or 'Sign in with Okta', Then they are redirected
    to the IdP and on return they are logged in and a session_started audit
    event is written.
  - Given a user with 2FA enabled, When they enter a valid password, Then
    they are prompted for a TOTP code and on success they are logged in, or
    on failure they see an error and can retry up to 5 times.
  - … (5 more ACs)
labels: [eval, auth]
```

### Sample output: smell report

```
Verdict: slice
Smells triggered: 5 of 7
  ✓ multi_verb_title (high)     — title contains a conjunction
  ✓ compound_gwt (high)         — 12 compound clauses across 7 ACs
  ✓ too_many_acs (high)         — 7 acceptance criteria (threshold: 5)
  ✓ multiple_personas (medium)  — 3 distinct personas: user, SSO user, admin
  ✓ sprawling_description (med) — 168 words (under threshold, but headers exceed)
  · oversized_estimate          — no estimate provided
  · mixed_crud                  — under threshold
```

### Sample output: coverage matrix (from the demo run on a real Jira project)

| # | Parent scenario (abridged) | S01 | S02 | S03 | S04 | S05 | S06 | S07 |
|---|---|---|---|---|---|---|---|---|
| 1 | Cart updates real-time + persists | ✓ | | | | | | |
| 2 | Checkout collects addresses + shipping | | ✓ | | | | | |
| 3 | Sales tax recalculated via TaxJar | | ✓ | | | | | |
| 4 | Discount codes validated and applied | | ✓ | | | | | |
| 5 | Payment accepts cards, wallets, saved methods | | | ✓ | ✓ | | | |
| 6 | On success: write order, decrement inventory, email | | | ✓ | | | | |
| 7 | On payment failure: friendly error, retry | | | | | ✓ | | |
| 8 | Admin can issue refund | | | | | | ✓ | |
| 9 | Abandoned-cart emails at 1h and 24h | | | | | | | ✓ |
| 10 | Responsive + WCAG 2.1 AA | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| 11 | Analytics events to Segment | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| — | _Split pattern_ | Workflow | Workflow | Happy path | Data Var. | Unhappy | Persona | Workflow |

### Sample output: child ticket

```markdown
# SCRUM-57-S03: Build card payment happy path with order confirmation

- Parent: SCRUM-57
- Split pattern: Happy path
- Covers parent ACs: 5, 6, 10, 11
- Estimate: 8

## Description
The success path through payment, deliberately scoped to cards only so we can
ship a working end-to-end purchase fast. Stripe Elements collects card details,
the order is written to the orders DB, inventory decrements, SendGrid sends
a confirmation email with order summary, and the shopper lands on a thank-you
page with order number. Wallet methods live in S04. Failure handling in S05.

## Acceptance criteria
- Given a shopper who has entered valid card details via Stripe Elements,
  When the payment succeeds, Then the order is written to the orders database,
  inventory is decremented, a SendGrid confirmation email is sent with order
  summary and tracking link, and the user lands on a thank-you page with the
  order number.
- Given a shopper on the payment screen, When they navigate the card form via
  keyboard or screen reader, Then the form meets WCAG 2.1 AA contrast and
  label requirements with inline validation.
- Given a shopper completing a card payment, When the order is placed, Then
  Segment receives payment_method_selected and order_placed events using the
  standard ecommerce schema.
```

### Sample output: queued Open Questions

The skill posts each as its own comment on the parent so each gets a dedicated thread:

> **Stripe Customer setup for saved methods.** AC #5 mentions saved payment methods for logged-in members. That implies a Stripe Customer object per member. Is that infrastructure already live, or does S04 need to include the Stripe Customer integration?

> **Inventory source of truth.** AC #6 says inventory is decremented; AC #8 says it's restocked on refund. What's the source of truth — the orders DB, a separate inventory service, or the warehouse system?

> **Shipping carrier and rate source.** AC #2 requires shipping cost based on zip and weight, but the carrier (USPS / UPS / FedEx) and rate source aren't named. Spike candidate?

> *(2 more)*

### Demo Jira workspace

A real end-to-end run lives in a Jira project: parent [SCRUM-57](https://fiafranzon.atlassian.net/browse/SCRUM-57) with seven child Stories ([SCRUM-58](https://fiafranzon.atlassian.net/browse/SCRUM-58) through [SCRUM-64](https://fiafranzon.atlassian.net/browse/SCRUM-64)) linked via *is implemented by*, plus the slicer's comment on the parent showing the smell report, coverage matrix, and queued Open Questions.

### Screenshots / video

<img width="633" height="765" alt="image" src="https://github.com/user-attachments/assets/93248519-aa4e-42bb-b4fa-5aefab22391f" />

<img width="640" height="232" alt="image" src="https://github.com/user-attachments/assets/9b90394f-ac8f-4fad-bda9-97e2eed755f3" />

<img width="570" height="178" alt="image" src="https://github.com/user-attachments/assets/64b7df71-ebf3-42ef-af35-2667103ec2a6" />

<img width="573" height="460" alt="image" src="https://github.com/user-attachments/assets/d00557d2-509a-4fc2-8207-23dec6dcfd97" />


---

## Repo contents

```
story-slicer/
├── README.md                            ← this file
├── story-slicer/                        ← the skill itself
│   ├── SKILL.md                         ← entry point: triggers, inputs, step-by-step
│   ├── scripts/
│   │   ├── smell_check.py               ← validates G/W/T schema, runs 7 heuristics
│   │   └── build_plan.py                ← validates children, assigns IDs, computes coverage
│   └── references/
│       ├── split-patterns.md            ← 6-pattern catalog
│       └── ticket-schema.json           ← JSON schema for parent and child tickets
└── eval/                                ← evaluation set + harness + results
    ├── METHODOLOGY.md                   ← full eval design, threats to validity, hypotheses
    ├── test-cases/                      ← 17 parent tickets w/ ground-truth labels
    ├── harness/
    │   ├── generate_test_cases.py
    │   └── run_smell_check_eval.py
    └── results/
        ├── smell_check_summary.md       ← verdict-accuracy table
        └── smell_check_results.json     ← raw output for the aggregate script
```

## Quick start (CLI)

```bash
# Detect smells on a parent ticket
python3 story-slicer/scripts/smell_check.py --input parent.json

# Build the full slice plan from a working doc (parent + child drafts)
python3 story-slicer/scripts/build_plan.py --input working.json --out slice-output/
```

## Reproducing the eval

```bash
cd eval
python3 harness/generate_test_cases.py        # regenerates eval/test-cases/
python3 harness/run_smell_check_eval.py       # produces results/smell_check_summary.md
# (baseline + skill output generation and judging — in progress)
```

## Installing as a Claude skill

```bash
mkdir -p ~/.claude/skills
cp -r story-slicer ~/.claude/skills/
```

For a plugin-based setup, drop the inner `story-slicer/` into your plugin's `skills/` directory.

## License

Add a license file at the repo root before publishing.
