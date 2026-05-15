---
name: story-slicer
description: Splits an oversized backlog ticket into structurally sound child tickets. Preserves every acceptance criterion via a verifiable coverage matrix, generates collision-free IDs, and validates each child against the team's ticket schema. Use when a draft ticket shows splittability smells (multiple verbs in title, conjunction-heavy ACs, multiple personas, sprawling description) or when grooming feedback is "this is too big."
---

# story-slicer

Slice a too-big backlog ticket into smaller children that:
- preserve every parent acceptance criterion (proven by a coverage matrix),
- pass schema validation (Given/When/Then for every AC),
- ship vertical slices of user value (frontend + backend together),
- and surface what the model couldn't decide as Open Questions for engineering instead of guessing.

The model orchestrates and writes prose. Two Python scripts in `scripts/` do the deterministic work: detecting splittability smells, validating G/W/T schema, generating IDs, and computing coverage math.

## When to use

- A backlog ticket draft is showing splittability smells (multi-verb title, "and"-heavy When/Then clauses, more than 5 ACs, multiple personas in Given clauses, sprawling description, mixed CRUD operations, story-point estimate over the team threshold).
- Grooming feedback is "this is too big" and the parent ACs have been reviewed and approved but the work hasn't been broken down.
- The user wants ready-to-paste child tickets plus a defensible artifact that proves no AC got dropped.

Either of two input paths work:
1. **Jira-native:** an Atlassian MCP is connected. Fetch the parent ticket by key (e.g., `PROJ-1234`).
2. **File-fed:** a parent ticket file (JSON or Markdown with frontmatter) is provided. Use this when no MCP is available, or for offline / test use.

## When NOT to use

- The parent ticket is well-scoped and small. The smell report will say so; respect it and produce a brief "no slicing recommended" comment instead of force-slicing.
- The parent ACs haven't been reviewed yet. This skill assumes ACs are stable. Run AC review with the pod first.
- The input is an epic (a container of stories). This skill slices a single story into smaller stories. Slicing epics into stories is a different problem (see future `epic-auditor`).
- The input is a pull request. Splittability heuristics are reusable for code-level splits, but the domain logic differs (see future `pr-slicer`).

## Inputs

A parent ticket conforming to `references/ticket-schema.json`. Fields:

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | e.g., `PROJ-1234`. If absent, the script generates a content-hash placeholder. |
| `title` | string | yes | One-line summary. |
| `description` | string | yes | Free-form context. |
| `acceptance_criteria` | list[string] | yes | Each item must parse as Given / When / Then. |
| `labels` | list[string] | no | Inherited by children. |
| `estimate` | number | no | Story points or similar. Triggers the oversized-estimate smell. |
| `parent_id` | string | no | Epic key, if any. Children inherit this. |

If the agent receives a pasted ticket in chat, write it to a tempfile and pass the path to the scripts.

## Step-by-step instructions

### 1. Acquire the parent ticket

- If an Atlassian MCP is connected: fetch by key. Map fields into the schema above. Save to a tempfile.
- Otherwise: read the file path the user provided, or stage pasted text to a tempfile.

### 2. Run the smell check

```
python scripts/smell_check.py --input <parent.json>
```

The script returns a JSON report with:
- `schema_valid` — boolean. If false, halt and tell the user which ACs aren't in G/W/T form.
- `smells` — list of seven heuristics with `triggered` / `evidence` / `severity`.
- `verdict` — one of `slice` (≥2 high-severity smells), `consider` (1 high or several mediums), `no-slice` (none triggered).
- `parsed_acs` — list of `{given, when, then}` objects for the model to reference by index.

### 3. Decide the path

- `slice` or `consider` → continue to step 4.
- `no-slice` → produce a short "no slicing recommended" message that names the smells checked, explains the verdict, and stops. This is the **caution** path. Do not invent reasons to slice anyway.

### 4. Pick split patterns

Read `references/split-patterns.md` and pick one or more patterns that fit the parent ticket. Common combinations:
- Workflow Steps × Happy/Unhappy
- Persona × CRUD
- Spike + Build (when a high-uncertainty smell is dominant)

**Default to vertical slices.** Each child must ship user-facing value end-to-end (frontend, backend, tests). Do **not** slice along frontend/backend, service boundaries, or other horizontal lines, even if a child looks "more parallelizable" that way. If a horizontal split looks tempting, capture it as an Open Question for engineering (step 7) and surface alternative-slice sketches as parent comments — but do not draft children that way.

### 5. Draft N children

For each child:
- Inherit `labels` and `parent_id` from the parent.
- Write a one-verb, one-outcome `title`.
- Write a `description` that explains the slice, references the patterns chosen, and notes which parent ACs it carries.
- Write `acceptance_criteria` as a list of G/W/T scenarios, each carrying or refining one or more parent scenarios.
- Set `covers` to the list of parent AC indices (1-based) this child carries — e.g., `[1, 3]`. **This is required.** `build_plan.py` uses it to compute the coverage matrix and to fail the slice if any parent AC has no home.
- Set `split_pattern` to the pattern label used for this child (one of: Workflow Steps, Happy path, Unhappy path, Data Variations, CRUD, Persona, Spike, Build).
- Estimate in story points (a fraction of the parent's estimate).
- Leave `id` blank — `build_plan.py` assigns IDs deterministically.

Aim for 2–5 children. Fewer than 2 means the parent didn't actually need slicing (revisit step 3). More than 5 usually means you're slicing horizontally or splitting too thin; revisit your pattern choice.

### 6. Validate and assemble the plan

Write the parent, the child drafts, and any open questions / alternative slices to a single working JSON file:

```json
{
  "parent": { ...parent ticket... },
  "children": [
    { "title": "...", "description": "...", "acceptance_criteria": ["Given ... When ... Then ..."],
      "covers": [1], "split_pattern": "Happy path", "labels": [...], "estimate": 3 }
  ],
  "open_questions":     ["...", "..."],
  "alternative_slices": [{ "label": "...", "rationale": "...", "sketch": ["..."] }]
}
```

Then run:

```
python scripts/build_plan.py --input <working.json> --out <out_dir>
```

The script will:
- validate every child against the schema (G/W/T format, required fields),
- assign deterministic IDs (`<parent_id>-S01`, `S02`, … or `SLICE-<hash>-S01` if no parent ID),
- compute the coverage matrix (parent scenarios × children),
- flag any parent AC not covered by at least one child (this is a hard error — the slice fails),
- write `slice-plan.md` and `children/<ID>.md` files to `<out_dir>`.

If validation fails, the script prints actionable errors. Fix the drafts (usually: a child's G/W/T is malformed, or a parent AC is uncovered) and re-run. Do not paper over errors.

### 7. Compose comments for the parent ticket

Produce three comment payloads:

**Summary comment** — one comment with: a one-line "sliced into N children", the IDs and titles, the coverage matrix as a table, and the top 3 smells that triggered.

**Open questions for engineering** — one comment per question. Phrase each as "Given X, When Y — what's the expected Then?" or "Should slice S0X depend on / share infrastructure with…?". Each question gets its own comment so it can be discussed and resolved in its own thread. `@mention` the tech lead if you know their handle.

**Alternative slices considered** — one comment per alternative the model thought about but didn't act on. The most common one: "Considered a frontend/backend split here; chose vertical slices to preserve user-value framing. Rough sketch of the alternative children: [titles + one-line G/W/T each]. Should we reconsider?" These are discussion prompts, not actions.

If no Atlassian MCP is connected, skip posting and instead include a "Comments to post on parent" section at the top of `slice-plan.md` containing all three payloads as Markdown. The user posts manually.

### 8. Present the plan and wait for approval

Show the user:
- the slice-plan summary in chat (children + matrix + smells resolved),
- the comments that will be posted to the parent,
- two approval checkboxes: **post comments to parent** and **create children in Jira**.

The user can approve one without the other (e.g., "post comments but hold the children until we discuss the FE/BE alternative"). Do **not** push to Jira until both are explicitly approved.

### 9. Push to Jira (on approval)

- Post each comment via the Atlassian MCP, in the order: summary → open questions → alternatives.
- Create each child as a Jira issue, linking `parent_id` to the parent.
- After children land, post a closing comment: "Created children: [links]."
- Save the final `slice-plan.md` and `children/` files to the user's outputs folder.

## Expected output

In the output directory:
```
slice-plan.md          # combined plan: summary, smell report, coverage matrix, comments
children/
  PROJ-1234-S01.md     # one file per child, schema-valid
  PROJ-1234-S02.md
  ...
```

Optionally, in the parent Jira ticket: 1 summary comment, N open-question comments, M alternative-slice comments, 1 closeout comment.

## Limitations and checks

- **Vertical slicing only.** The skill never drafts a horizontal split as a child, even on request. It surfaces the option as a comment.
- **G/W/T format is mandatory.** If the parent has free-form ACs, the skill stops and asks for them to be rephrased before slicing.
- **Idempotent reruns.** IDs are derived deterministically from the parent ID (or content hash). Running the skill twice on the same input produces the same IDs — important for not duplicating Jira issues on a retry.
- **Caution path.** When the smell report says "no slice needed," the skill declines politely and names the smells it checked. It does not invent reasons to slice anyway.
- **Hard error on uncovered ACs.** If any parent G/W/T scenario isn't covered by at least one child, `build_plan.py` fails. The slice is invalid until every parent scenario has a home.
- **Open questions are first-class.** Surface uncertainty as questions; do not paper over it with confident-sounding prose.

## References

- `references/split-patterns.md` — the six split-pattern catalog with definitions and examples.
- `references/ticket-schema.json` — JSON schema for parent and child tickets.
- `tests/` — three demo tickets covering normal, edge, and caution cases.
