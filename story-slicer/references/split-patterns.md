# Split-pattern catalog

Six patterns the model picks from when slicing an oversized backlog ticket. Each pattern is a recipe for cutting the work into smaller children that still ship vertical user value (frontend + backend + tests together).

The model can — and often should — combine patterns. Common combos:
- **Workflow Steps × Happy path / Unhappy path** (sequence + error handling)
- **Persona × CRUD** (different users get different operations)
- **Spike → Build** (when uncertainty is high)

When the model picks a pattern, it sets `split_pattern` on each child to the label below (e.g., `"Happy path"`, `"Persona"`).

---

## 1. Workflow Steps

**Definition.** Split a sequence of stages into separate children. The parent describes a flow with multiple distinct stages; each child ships one stage end-to-end.

**Use when.** The parent's description or ACs read like a pipeline ("user signs up, validates email, lands on dashboard"). Each stage has a meaningful intermediate state where shipping just-that-stage delivers value.

**Example.**

> **Parent:** "User can sign up with email and confirm their account."
>
> **Children:**
> - **S01 (Workflow Steps):** "User can submit a sign-up form with email and password." — covers the form + validation ACs.
> - **S02 (Workflow Steps):** "User receives a confirmation email and can click through to confirm." — covers the email + confirmation ACs.

**Common mistake.** Splitting along technical seams ("write the API," "wire the form"). That's a horizontal split, not a workflow split. A real workflow stage is observable to a user.

---

## 2. Happy path

**Definition.** A child that covers only the success scenario — what happens when everything goes right. Usually paired with one or more "Unhappy path" siblings.

**Use when.** The parent has both happy and edge-case scenarios mixed together, and shipping the happy path first delivers value while edge cases get iterated on.

**Example.**

> **Parent:** "User can upload a CSV; show errors for size, format, and duplicates."
>
> **Children:**
> - **S01 (Happy path):** "User can upload a valid CSV under 5MB." — covers the success AC.
> - **S02 (Unhappy path):** "Show clear errors for oversize, malformed, and duplicate rows." — covers the three error ACs.

**Common mistake.** Calling something a happy path when it's actually two happy paths smushed together. If the "happy" child still has compound G/W/T clauses, it needs further slicing.

---

## 3. Unhappy path

**Definition.** A child that covers error states, validation failures, and edge cases. Usually a sibling to a Happy path child.

**Use when.** Edge-case behavior is meaningful enough to warrant its own ticket — e.g., the team wants to track UX polish for error states separately from the core feature.

**Example.** See **Happy path** above.

**Common mistake.** Overstuffing this child. If the parent has 6 different error scenarios, the unhappy-path child probably needs to split further (often by **Data Variations** — one child per error class).

---

## 4. Data Variations

**Definition.** Split by the kind of data flowing through the feature. Each child supports one data shape, format, or source.

**Use when.** The parent supports multiple input types ("CSV, vCard, Google Contacts"), or multiple data classes that require different handling.

**Example.**

> **Parent:** "Import contacts from CSV, vCard, and Google."
>
> **Children:**
> - **S01 (Data Variations):** "Import from CSV."
> - **S02 (Data Variations):** "Import from vCard."
> - **S03 (Data Variations):** "Import from Google Contacts."

**Common mistake.** Confusing "data variation" with "data validation rule." A variation is a different input type entirely. A validation rule (e.g., "reject rows over 100 chars") usually belongs in an Unhappy path child.

---

## 5. CRUD

**Definition.** Split by Create / Read / Update / Delete operations. Each child ships one operation end-to-end.

**Use when.** The parent describes "manage <thing>" — i.e., a full CRUD surface for a single entity. Common in admin tools, settings screens, library views.

**Example.**

> **Parent:** "Admin can manage tags: create, edit, delete, and view all tags."
>
> **Children:**
> - **S01 (CRUD - Read):** "Admin can view all tags."
> - **S02 (CRUD - Create):** "Admin can create a tag."
> - **S03 (CRUD - Update):** "Admin can edit an existing tag."
> - **S04 (CRUD - Delete):** "Admin can delete a tag."

**Common mistake.** Forgetting that Read usually has to ship first (you can't update what you can't see). Order matters.

---

## 6. Persona

**Definition.** Split by who's using the feature. Each child ships the experience for one user type.

**Use when.** The parent's Given clauses reference distinct personas (admin vs. end user, owner vs. member, public vs. authenticated). Each persona's experience is meaningfully different.

**Example.**

> **Parent:** "Document approvals: reviewers approve/reject; admins can override."
>
> **Children:**
> - **S01 (Persona):** "Reviewer approves or rejects a document."
> - **S02 (Persona):** "Admin overrides a previous approval/rejection."

**Common mistake.** Treating "logged-out user" as a persona. That's usually an Unhappy path child instead ("redirect to login" is an error state, not a separate user experience).

---

## 7. Spike + Build

**Definition.** When uncertainty is too high to commit to a build, ship a learning ticket first ("Spike") and a build ticket second.

**Use when.** A core question is unanswered ("can our SSO library handle SAML?") and the answer changes the rest of the slice meaningfully. The Spike has a time-boxed deliverable (a memo, a working prototype, a decision) — not production code.

**Example.**

> **Parent:** "Add SSO login support."
>
> **Children:**
> - **S01 (Spike):** "Investigate SAML support in our auth library; decide on approach. Deliverable: 1-page memo with recommendation."
> - **S02 (Build):** "Implement SSO login per S01 recommendation." — depends on S01.

**Common mistake.** Using a Spike to avoid commitment when the team actually knows the answer. If the question can be answered in a 30-minute conversation, skip the Spike.

---

## What's deliberately not in this catalog

- **Frontend / Backend split** — horizontal, breaks vertical-slice principle. The model surfaces this as an Open Question or alternative-slice comment, never as a child.
- **Interface Variations (web / mobile / API)** — usually overlaps with Persona or Data Variations; collapsed into those.
- **Defer Performance** — advanced; v1 leaves this out.
- **Business Rules** — collapsed into Happy/Unhappy + Data Variations.
