# story-slicer

Slices an oversized backlog ticket into smaller children that:

- preserve every parent acceptance criterion (proven by a coverage matrix),
- pass schema validation (Given/When/Then for every AC),
- ship vertical slices of user value (frontend + backend together),
- and surface what the model couldn't decide as Open Questions for engineering instead of guessing.

This repo packages the skill so it can be dropped into a Claude Code or Cowork plugin marketplace, or read directly by a Claude agent.

## Why the project pivot

My original project failed because it was improperly scoped; despite being a PM, I let creep get the best of me and failed to define a concise enough happy path. I'm going to follow core PDLC principles: clear PRD, AC, and milestones.

**Organization**: The project folder got cluttered with references of what the tool could become rather than what it needs to be in V1. Furthermore, visiblity into what the AI was producing started to get foggy. Instead of breaking out versions into new documents, I'll be careful to figure out a way to balance keeping records (perhaps new folder structures?) and introducing clutter which ultimately confused the agent.

**Development**: Lastly, when moving to development, I'm going to keep a jira board of tickets and tackle them one at a time. I noticed that without more granular requirements of what each session had to build there was some struggle to understand what was being made. (i.e. instead of "build this piece x", prompt "build this piece x. this piece x is done when y. Test for y".

**Testing**: I developed on my personal laptop, and I found the output to not really be applicable to all organizations. My story slicer can actually be used pretty easily by anyone, but this project wasn't as universally applicable, which made testing on my work computer challenging. 

Anyways, a great project overall! Appreciate the sessions jamming and the learning. 

## What's inside

```
story-slicer/
├── README.md               ← this file
└── story-slicer/           ← the skill itself
    ├── SKILL.md            ← entry point: triggers, inputs, step-by-step instructions
    ├── scripts/
    │   ├── smell_check.py  ← validates G/W/T schema and runs 7 splittability heuristics
    │   └── build_plan.py   ← validates child drafts, assigns IDs, computes coverage matrix
    └── references/
        ├── split-patterns.md   ← the 6-pattern catalog (Workflow Steps, Happy/Unhappy path,
        │                          Data Variations, CRUD, Persona, Spike + Build)
        └── ticket-schema.json  ← JSON schema for parent and child tickets
```

## How the skill works

The agent does the writing and judgment. The two Python scripts do the deterministic work — detecting smells, parsing Given/When/Then, generating collision-free IDs, and computing coverage math — so the slice is auditable.

A typical run:

1. **Acquire the parent ticket** from a Jira-style MCP or a local JSON/Markdown file.
2. **Run `scripts/smell_check.py`** to validate the schema and detect splittability smells. Verdict is `slice`, `consider`, or `no-slice`.
3. **Pick split patterns** from `references/split-patterns.md` and draft 2–5 vertical-slice children. Each child must list which parent ACs it covers.
4. **Run `scripts/build_plan.py`** to validate every child, assign deterministic IDs (`<parent>-S01`, `S02`, …), compute the coverage matrix, and fail loudly if any parent AC has no home.
5. **Present the plan, comments, and child drafts** to the user; wait for approval before posting comments or creating child tickets.

See `story-slicer/SKILL.md` for the full instructions the agent follows.

## Quick start (CLI)

The scripts are usable standalone — drop a parent ticket JSON in and run:

```bash
python3 story-slicer/scripts/smell_check.py --input parent.json
```

Sample output (truncated):

```json
{
  "schema_valid": true,
  "verdict": "slice",
  "smells": [
    {"name": "multi_verb_title", "triggered": true, "severity": "high", "evidence": "..."},
    {"name": "compound_gwt",     "triggered": true, "severity": "high", "evidence": "..."},
    ...
  ]
}
```

Then build the plan:

```bash
python3 story-slicer/scripts/build_plan.py --input working.json --out slice-output/
```

Where `working.json` is the parent plus your child drafts. The script writes `slice-output/slice-plan.md` (full report with coverage matrix and queued parent comments) and one Markdown file per child in `slice-output/children/`.

## Input format

Parent tickets conform to the schema in `story-slicer/references/ticket-schema.json`. The required fields are `title`, `description`, and `acceptance_criteria` (each AC must parse as `Given … When … Then …`). Optional fields: `id`, `labels`, `estimate`, `parent_id`.

Inline (`Given X, When Y, Then Z`) and multi-line forms are both accepted.

## The seven splittability smells

| Smell | Severity | Trigger |
|---|---|---|
| `multi_verb_title` | high | Title joins multiple action verbs with `and` / `or` / `+` / `/` |
| `compound_gwt` | high | A When or Then clause contains `and` / `or` |
| `too_many_acs` | high | More than 5 acceptance criteria |
| `oversized_estimate` | high | Story-points estimate exceeds the team threshold (default 8) |
| `multiple_personas` | medium | 2+ distinct personas in the Given clauses |
| `sprawling_description` | medium | More than 200 words or 2 Markdown headers in the description |
| `mixed_crud` | medium | 3+ of Create / Read / Update / Delete operations present |

Verdict math: ≥2 high (or 1 high + ≥2 medium) → `slice`. 1 high or ≥2 medium → `consider`. None → `no-slice` (caution path: the skill declines and names what it checked).

## Vertical slicing only

The skill never drafts a horizontal (frontend / backend, service-A / service-B) split as a child. Each child must ship user-facing value end-to-end. Horizontal alternatives are surfaced as parent-ticket comments for discussion, not acted on.

## Hard validation rules

`build_plan.py` exits non-zero on any of:

- the parent fails schema validation (an AC isn't in G/W/T form),
- a child fails schema validation,
- any parent AC index is uncovered by every child,
- a child references an out-of-range parent AC index.

The model must fix the drafts and re-run — these errors are never papered over.

## Installing as a Claude Code / Cowork skill

Copy the inner `story-slicer/` directory into your skills folder. The skill is auto-discovered by its `SKILL.md` front-matter description.

For Claude Code:

```bash
mkdir -p ~/.claude/skills
cp -r story-slicer ~/.claude/skills/
```

For a plugin-based setup, drop the inner `story-slicer/` into your plugin's `skills/` directory.

## License

Add a license file at the repo root before publishing.
