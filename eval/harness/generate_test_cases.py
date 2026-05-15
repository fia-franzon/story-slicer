#!/usr/bin/env python3
"""Generate the 17 evaluation test cases as JSON files in eval/test-cases/.

Authored against the methodology in eval/METHODOLOGY.md. Each case carries
a `_ground_truth` block (the answer key) and a `_source` block (where the
ticket was drawn from, to support the blind-authoring rule).

Re-running this script overwrites the test cases. Don't run it after the
eval has begun — modifications should be tracked in git from that point on.
"""

import json
import os
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "test-cases"


CASES = [
    # ────────────────────────────────────────────────────────────────────
    # SLICE — 8 cases. Multi-smell parents that clearly need breaking up.
    # ────────────────────────────────────────────────────────────────────

    {
        "id": "AUTH-001",
        "title": "Add SSO, 2FA, password reset, and account lockout to login",
        "description": (
            "We need to harden the login experience. Support SSO via Google, Microsoft, "
            "and Okta; add TOTP-based 2FA with backup codes; add a password-reset flow "
            "via email magic link; add account lockout after 5 failed attempts with "
            "admin unlock; and add a 'Remember me' option that keeps the session alive "
            "for 30 days. Should work for end users, SSO-only enterprise users, and "
            "support admins who help locked-out users. Security team wants audit logs "
            "for every auth event. Marketing wants 'Sign in with Apple' if we can fit it. "
            "The login screen is also getting a design refresh — let's update the visuals "
            "while we're in there. Accessibility: legal flagged WCAG AA on the new screens."
        ),
        "acceptance_criteria": [
            "Given a user on the login page, When they click 'Sign in with Google' or 'Sign in with Microsoft' or 'Sign in with Okta', Then they are redirected to the IdP and on return they are logged in and a session_started audit event is written.",
            "Given a user with 2FA enabled, When they enter a valid password, Then they are prompted for a TOTP code and on success they are logged in, or on failure they see an error and can retry up to 5 times.",
            "Given a user who forgot their password, When they request a reset, Then they receive a magic-link email valid for 1 hour, and clicking it lets them set a new password and invalidates all existing sessions.",
            "Given a user who fails password entry 5 times in a row, When the 5th attempt fails, Then the account is locked for 15 minutes and an admin notification is sent, and the user sees a 'contact support' message.",
            "Given a support admin viewing a locked account, When they click 'Unlock', Then the account is unlocked, the unlock event is written to the audit log, and the user receives an unlock notification email.",
            "Given a user generating 2FA backup codes, When they confirm setup, Then 10 single-use backup codes are displayed once and stored hashed, and the user can use any code in place of a TOTP during 2FA.",
            "Given any user successfully logging in, When 'Remember me' is checked, Then the session persists for 30 days across browser restarts, and a remember_me_session_created audit event is written.",
        ],
        "labels": ["eval", "auth"],
        "_ground_truth": {
            "label": "SLICE",
            "domain": "auth",
            "expected_verdict": "slice",
            "expected_smells": ["multi_verb_title", "compound_gwt", "too_many_acs", "multiple_personas", "sprawling_description"],
            "expected_children_range": [4, 7],
            "notes": "Multi-verb title, conjunction-heavy When/Then clauses, three personas (user, SSO user, admin), 7 ACs. Mixed CRUD via reset/unlock/create.",
        },
        "_source": "Composed from Atlassian, Stripe, and GitHub auth backlog patterns; not derived from skill rubric.",
    },

    {
        "id": "IMPORT-001",
        "title": "Build contact import wizard supporting CSV, vCard, Google, and LinkedIn",
        "description": (
            "Sales has been complaining for a year that they can't bulk-import contacts. "
            "Build an import wizard that accepts CSV, vCard, Google Contacts (OAuth), and "
            "LinkedIn export files. Wizard should let the user map source columns to our "
            "contact fields, preview the first 50 rows before committing, detect duplicates "
            "against existing contacts, let the user choose merge or skip per duplicate, "
            "validate phone and email formats, surface errors inline, and let the user undo "
            "the last import within 24 hours. Also write a per-import audit log so we can "
            "trace where contacts came from. CSV is the priority; vCard and Google are second; "
            "LinkedIn is optional. The wizard runs in a modal on the contacts page."
        ),
        "acceptance_criteria": [
            "Given a user on the contacts page, When they click 'Import' and upload a CSV file under 10MB, Then the wizard parses the file and presents a column-mapping step with our contact fields and intelligent defaults.",
            "Given a user at the column-mapping step, When they map source columns and click 'Preview', Then the first 50 mapped rows are shown with inline validation errors highlighted for invalid emails, invalid phone formats, and missing required fields.",
            "Given a user previewing an import, When the system detects duplicates against existing contacts by email or phone, Then duplicates are listed and the user can choose merge, skip, or create-new per row or in bulk.",
            "Given a user importing from vCard, When they upload a .vcf file, Then the wizard parses it and skips the column-mapping step since vCard fields are standardized.",
            "Given a user importing from Google Contacts, When they authorize via OAuth, Then their contacts are fetched and presented for column mapping like CSV.",
            "Given a user importing from LinkedIn, When they upload a LinkedIn export ZIP, Then the contacts CSV inside is auto-extracted and proceeds through the same mapping flow as CSV.",
            "Given a user who completes an import, When the import finishes, Then a confirmation shows the counts (created, merged, skipped, errored), an audit log entry is written with the source and counts, and an 'Undo' link is shown for 24 hours.",
            "Given a user who clicks 'Undo' within 24 hours of an import, When they confirm, Then all contacts created by that import are removed and any merged contacts are restored to their pre-merge state.",
        ],
        "labels": ["eval", "data-import"],
        "_ground_truth": {
            "label": "SLICE",
            "domain": "data-import",
            "expected_verdict": "slice",
            "expected_smells": ["multi_verb_title", "compound_gwt", "too_many_acs", "sprawling_description", "mixed_crud"],
            "expected_children_range": [4, 6],
            "notes": "Classic Data Variations split candidate (CSV / vCard / Google / LinkedIn).",
        },
        "_source": "Composite of Pipedrive, Intercom, and HubSpot import-wizard backlog templates.",
    },

    {
        "id": "NOTIF-001",
        "title": "Build notification preferences with per-event opt-in across channels",
        "description": (
            "End users want fine-grained control. Build a preferences screen where users "
            "pick per-event delivery (email, push, in-app, SMS) and set quiet hours. Admins "
            "need an override that forces critical notifications (security alerts, billing "
            "failures) regardless of preferences. Default new users to a sensible preset. "
            "Push needs APNs and FCM; SMS is via Twilio; email is via SendGrid. The notification "
            "service already exists — we're just adding the preferences layer plus the routing "
            "logic to respect them. Should also expose preferences via API for the mobile apps."
        ),
        "acceptance_criteria": [
            "Given a user on the preferences screen, When they toggle a channel for an event type, Then the preference is saved and a confirmation toast is shown.",
            "Given a user with email disabled for an event, When that event fires, Then no email is sent but the in-app notification still appears if in-app is enabled.",
            "Given a user with quiet hours set, When an event fires inside those hours, Then push and SMS are suppressed and queued for delivery at the end of quiet hours.",
            "Given an admin who marks a notification type as critical, When that notification fires, Then it bypasses user preferences and quiet hours and is delivered via all enabled channels.",
            "Given a new user signing up, When their account is created, Then default preferences are populated using the platform preset.",
            "Given the mobile app, When it fetches a user's preferences via the API, Then it receives the current preferences and can update them via PUT.",
        ],
        "labels": ["eval", "notifications"],
        "_ground_truth": {
            "label": "SLICE",
            "domain": "notifications",
            "expected_verdict": "slice",
            "expected_smells": ["compound_gwt", "too_many_acs", "multiple_personas", "sprawling_description"],
            "expected_children_range": [3, 5],
            "notes": "Two personas (user, admin), API surface + UI, four channels. Persona × workflow split candidate.",
        },
        "_source": "Generic SaaS notifications-preferences PRD; commonly seen in Linear, Asana, Slack templates.",
    },

    {
        "id": "REPORT-001",
        "title": "Build sales dashboard with KPIs, charts, filters, exports, and scheduled emails",
        "description": (
            "Sales leadership wants a dashboard. Build a real-time dashboard with KPIs at "
            "the top (revenue, deals won, pipeline, win rate), four primary charts "
            "(revenue trend, pipeline funnel, win/loss reasons, rep leaderboard), filters "
            "for date range, team, owner, and product. Users can export the current view "
            "to CSV or PDF. Sales managers can schedule the dashboard to be emailed weekly "
            "or monthly to a list of recipients. Role-based access: reps see only their own "
            "data, managers see their team, executives see all. Should be performant — "
            "queries against the warehouse, with a 5-minute cache layer."
        ),
        "acceptance_criteria": [
            "Given a sales rep viewing the dashboard, When the page loads, Then the four KPIs and four charts render with their data scoped to the rep's own deals.",
            "Given a sales manager, When they view the dashboard, Then they see aggregated data for their team and can drill down to individual reps.",
            "Given an executive, When they view the dashboard, Then they see company-wide data with no filtering restrictions.",
            "Given any user, When they change the date range, team, owner, or product filters, Then all KPIs and charts update within 2 seconds using the cache layer.",
            "Given a user viewing the dashboard, When they click 'Export CSV' or 'Export PDF', Then the current filtered view is exported and downloaded.",
            "Given a sales manager, When they configure a scheduled email, Then they pick frequency (weekly / monthly), recipients, and the schedule is saved.",
            "Given a scheduled email reaches its send time, When the scheduler runs, Then a PDF snapshot of the dashboard with the manager's filters is generated and emailed to the recipient list.",
        ],
        "labels": ["eval", "reporting"],
        "_ground_truth": {
            "label": "SLICE",
            "domain": "reporting",
            "expected_verdict": "slice",
            "expected_smells": ["multi_verb_title", "compound_gwt", "too_many_acs", "multiple_personas", "sprawling_description"],
            "expected_children_range": [4, 6],
            "notes": "Persona-based split very natural (rep / manager / exec), plus separate slices for export and scheduled email.",
        },
        "_source": "Drawn from Looker, Mode, and Salesforce dashboard PRDs; standard B2B sales-reporting pattern.",
    },

    {
        "id": "MOBILE-001",
        "title": "Add offline mode to the mobile app with sync, conflict resolution, and retry",
        "description": (
            "Field users in low-connectivity environments need the app to work offline. "
            "Build offline mode: cache the user's data on login, let them perform reads "
            "and create/edit/delete actions offline, queue mutations until reconnection, "
            "sync queued mutations on reconnect with conflict resolution, retry failed "
            "syncs with exponential backoff, show offline state in the UI (banner + per-screen "
            "icons), and support background sync via iOS BackgroundTasks and Android WorkManager. "
            "Conflict resolution: last-write-wins for most fields, manual resolution UI for "
            "structured documents. iOS and Android both."
        ),
        "acceptance_criteria": [
            "Given a logged-in user on the mobile app, When they go offline, Then a persistent banner appears, per-screen icons indicate offline state, and the app continues to function for cached data.",
            "Given a user offline, When they create, edit, or delete a record, Then the change is applied locally and queued for sync.",
            "Given a user reconnects, When the sync queue runs, Then queued mutations are sent to the server in order, with exponential backoff on failure (1s, 2s, 4s, 8s, max 5 retries).",
            "Given a sync conflict on a simple field, When the queued mutation arrives, Then last-write-wins is applied and the user sees a non-blocking toast summarizing the resolution.",
            "Given a sync conflict on a structured document, When the queued mutation arrives, Then both versions are presented in a conflict-resolution UI and the user picks which to keep or merges manually.",
            "Given the app is backgrounded, When OS allows background work, Then iOS BackgroundTasks and Android WorkManager flush the sync queue without requiring the user to open the app.",
        ],
        "labels": ["eval", "mobile"],
        "_ground_truth": {
            "label": "SLICE",
            "domain": "mobile",
            "expected_verdict": "slice",
            "expected_smells": ["multi_verb_title", "compound_gwt", "too_many_acs", "sprawling_description", "mixed_crud"],
            "expected_children_range": [4, 6],
            "notes": "Workflow Steps + Happy/Unhappy split very natural. Watch for horizontal platform-split temptation (iOS / Android).",
        },
        "_source": "Field-services mobile-app pattern; representative of typical offline-mode PRDs.",
    },

    {
        "id": "API-001",
        "title": "Build public REST API for tasks with full CRUD, search, webhooks, and OAuth",
        "description": (
            "We're opening up tasks via a public API. Endpoints for list/create/read/update/"
            "delete on tasks, plus search with filters and pagination, bulk operations (bulk "
            "complete, bulk delete, bulk reassign), webhooks for task.created / task.updated / "
            "task.completed / task.deleted events, OAuth 2.0 client-credentials flow, API key "
            "management UI (create / revoke / rotate), rate limiting (1000 req/min per key), "
            "and a docs site generated from the OpenAPI spec. Developer audience plus admin "
            "audience for managing keys. Stripe-style API design."
        ),
        "acceptance_criteria": [
            "Given a developer with a valid API key, When they GET /tasks with optional filters, Then they receive a paginated list of tasks scoped to their workspace.",
            "Given a developer with a valid API key, When they POST /tasks with a valid payload, Then a task is created, the response includes the new task, and a task.created webhook fires to subscribed endpoints.",
            "Given a developer, When they PATCH /tasks/:id or DELETE /tasks/:id, Then the task is updated or soft-deleted, and the corresponding webhook fires.",
            "Given a developer making bulk operations, When they POST /tasks/bulk with an action and a list of task IDs, Then the action is applied to all listed tasks and a single webhook batch event fires.",
            "Given a workspace admin, When they create an API key, Then a key is generated with a 'kxx_' prefix, the user sees the key once for copying, and the key is stored hashed.",
            "Given a workspace admin, When they revoke or rotate an API key, Then subsequent requests with the revoked key receive 401, and rotated keys invalidate the previous value.",
            "Given a developer exceeding 1000 requests per minute per key, When the threshold is hit, Then subsequent requests receive 429 with Retry-After headers until the window resets.",
            "Given a developer subscribing to webhooks, When an event fires, Then a POST is delivered to the subscriber URL with HMAC-signed payload, and failures are retried with exponential backoff up to 24 hours.",
        ],
        "labels": ["eval", "api"],
        "_ground_truth": {
            "label": "SLICE",
            "domain": "api",
            "expected_verdict": "slice",
            "expected_smells": ["multi_verb_title", "compound_gwt", "too_many_acs", "multiple_personas", "sprawling_description", "mixed_crud"],
            "expected_children_range": [5, 8],
            "notes": "Strong CRUD + Persona signals. Natural slices: CRUD endpoints, webhooks, OAuth/keys, rate limiting, docs.",
        },
        "_source": "Inspired by Stripe, Linear, GitHub public API PRD patterns.",
    },

    {
        "id": "ONBOARD-001",
        "title": "Build onboarding flow with signup, verification, profile, team invite, and tour",
        "description": (
            "Activation is poor. Build a guided onboarding flow that runs from signup to "
            "first valuable action. Steps: email signup with password, email verification, "
            "profile setup (name + role + photo), team invitation (skip if solo), sample data "
            "seed for empty workspace, welcome tour highlighting the 5 main features, and a "
            "first-task suggestion based on the user's stated role. Should be skippable per "
            "step. Should resume from the last completed step if the user drops off. Analytics "
            "on every step so we can measure funnel."
        ),
        "acceptance_criteria": [
            "Given a new visitor on the landing page, When they submit the signup form with email and password, Then an account is created, a verification email is sent, and they land on the email-verification screen.",
            "Given a user on the verification screen, When they click the email link, Then their email is verified and they proceed to profile setup.",
            "Given a user on profile setup, When they enter name, role, and upload a photo, Then their profile is saved and they proceed to team invitation, or can click 'Skip' to bypass.",
            "Given a user on team invitation, When they enter up to 5 emails and click invite, Then invitation emails are sent and the user proceeds to the sample-data seed step.",
            "Given a user with an empty workspace, When the sample-data step runs, Then 3 example tasks and 1 example project are created for them automatically.",
            "Given a user finishing sample-data, When they reach the welcome tour, Then a 5-step coachmark tour runs over the main UI, and the user can dismiss at any time.",
            "Given a user completing the tour, When the first-task suggestion shows, Then it suggests an action tailored to their stated role and links to that action.",
            "Given a user who drops off mid-onboarding, When they next sign in, Then they resume from the last incomplete step.",
            "Given any onboarding step, When the user completes or skips it, Then a Segment event fires (onboarding_step_completed or onboarding_step_skipped) with the step name and timestamp.",
        ],
        "labels": ["eval", "onboarding"],
        "_ground_truth": {
            "label": "SLICE",
            "domain": "onboarding",
            "expected_verdict": "slice",
            "expected_smells": ["multi_verb_title", "compound_gwt", "too_many_acs", "sprawling_description"],
            "expected_children_range": [4, 6],
            "notes": "Canonical Workflow Steps case. Each step is a candidate child.",
        },
        "_source": "Common SaaS onboarding template; appears in Notion, Linear, Figma onboarding PRDs.",
    },

    {
        "id": "DOC-001",
        "title": "Add real-time collaboration, version history, comments, sharing, and export to docs",
        "description": (
            "Make our docs collaborative like Notion or Google Docs. Real-time multi-cursor "
            "editing with presence indicators, version history with named snapshots and "
            "rollback, inline comments and suggestions/redlines that authors can accept or "
            "reject, granular sharing permissions (view / comment / edit) at the document "
            "and folder level, link sharing with optional expiration and password, exports "
            "to PDF and Word, and a full audit log for compliance. Editors, viewers, and "
            "admins all use this surface. Operational transformation via the existing CRDT "
            "library."
        ),
        "acceptance_criteria": [
            "Given two users editing the same document, When user A types, Then user B sees the change within 200ms with user A's cursor and presence indicator visible.",
            "Given a user editing a document, When they create a named snapshot, Then the snapshot is saved with timestamp and author, and appears in the version history panel.",
            "Given a user viewing history, When they click 'Restore' on a snapshot, Then the document content reverts to that snapshot and a new history entry is recorded.",
            "Given a viewer-permissioned user, When they read a document, Then they cannot type or modify content but can view all comments.",
            "Given a comment-permissioned user, When they highlight text and add a comment, Then the comment appears in the side panel for all collaborators and they can reply.",
            "Given an editor reviewing suggestions, When they click 'Accept' or 'Reject' on a redline, Then the change is applied or discarded and the suggestion is removed.",
            "Given a document owner, When they create a share link, Then they can set view/comment/edit permission, optional expiry date, and optional password, and the link is generated.",
            "Given a user, When they request a PDF or Word export, Then the document is exported preserving formatting and downloads to their device.",
            "Given any document action (edit, share, export, delete), When the action completes, Then it is written to the audit log with user, timestamp, and action details.",
        ],
        "labels": ["eval", "document"],
        "_ground_truth": {
            "label": "SLICE",
            "domain": "document",
            "expected_verdict": "slice",
            "expected_smells": ["multi_verb_title", "compound_gwt", "too_many_acs", "multiple_personas", "sprawling_description", "mixed_crud"],
            "expected_children_range": [5, 7],
            "notes": "All six listed smells present. Natural slices: real-time editing, version history, comments, sharing, exports, audit log.",
        },
        "_source": "Notion/Google Docs collaboration features as documented publicly.",
    },

    # ────────────────────────────────────────────────────────────────────
    # CONSIDER — 4 cases. Borderline: 1 high or ≥2 medium smells.
    # The skill might slice them or surface the option; either is OK.
    # ────────────────────────────────────────────────────────────────────

    {
        "id": "AUTH-002",
        "title": "Add Google SSO login",
        "description": (
            "Add Google as a sign-in option. The user clicks 'Sign in with Google', is "
            "redirected to Google's OAuth screen, grants access, and lands back in the app "
            "logged in. If they have an existing account with the same email, we merge — "
            "the Google identity gets linked. If not, we create a new account with the data "
            "from Google's profile (name, email, photo). Need to handle the edge case where "
            "a Google account has been deleted (rare, but possible if a user was offboarded "
            "from their old company): we should surface a clear error and let them sign in "
            "via password instead. Audit-log every SSO event for security."
        ),
        "acceptance_criteria": [
            "Given a user on the login page, When they click 'Sign in with Google', Then they are redirected to Google's OAuth consent screen.",
            "Given a user returning from Google with a successful auth, When their email matches an existing account, Then the Google identity is linked, they are logged in, and an sso_login_success audit event is written.",
            "Given a user returning from Google with a successful auth, When no account exists for that email, Then a new account is created with name, email, and photo populated from Google, they are logged in, and an account_created audit event is written.",
            "Given a user with a deleted Google account attempting to sign in, When Google returns an error, Then the user sees a friendly message explaining the situation and is offered password-based login as an alternative.",
        ],
        "labels": ["eval", "auth"],
        "_ground_truth": {
            "label": "CONSIDER",
            "domain": "auth",
            "expected_verdict": "consider",
            "expected_smells": ["compound_gwt", "sprawling_description"],
            "expected_children_range": [1, 3],
            "notes": "Single verb, single persona, but the description sprawls and Then-clauses are compound. Skill should slice into 2-3 thin slices or recommend keeping as one and tightening the ACs.",
        },
        "_source": "Standard SSO-integration ticket; appears in nearly every B2B SaaS backlog.",
    },

    {
        "id": "REPORT-002",
        "title": "Add CSV export to the existing sales report",
        "description": (
            "We have a sales report with filters and pagination. Sales ops wants to download "
            "the currently-filtered view as a CSV. Should respect all active filters, include "
            "the same column ordering as the report, and use the same row formatting (currency, "
            "dates). Export should include all rows that match the filter, not just the "
            "current page. Performance: up to 50,000 rows should export in under 10 seconds."
        ),
        "acceptance_criteria": [
            "Given a user viewing the sales report with filters applied, When they click 'Export CSV', Then a CSV is generated containing all rows matching the filters and using the report's column ordering and currency/date formatting, and the file downloads with a name including the filter date range.",
        ],
        "labels": ["eval", "reporting"],
        "_ground_truth": {
            "label": "CONSIDER",
            "domain": "reporting",
            "expected_verdict": "consider",
            "expected_smells": ["compound_gwt"],
            "expected_children_range": [1, 2],
            "notes": "Single AC but the Then is compound (multiple obligations). Skill should either accept as a small story or split the Then into separate slices.",
        },
        "_source": "Generic export-feature pattern; reasonably common product request.",
    },

    {
        "id": "ADMIN-001",
        "title": "Add bulk role change to user management",
        "description": (
            "Admins managing large workspaces want to change roles in bulk instead of clicking "
            "into each user. From the user list, they should be able to select multiple users, "
            "pick a target role from a dropdown, confirm the action, and have all selected "
            "users updated. Show a confirmation dialog summarizing how many users will be "
            "affected. Log each role change in the audit log."
        ),
        "acceptance_criteria": [
            "Given an admin on the user list, When they select multiple users via checkboxes and choose a new role from the bulk-action menu and confirm in the dialog, Then all selected users have their role updated and the action is written to the audit log per user.",
            "Given an admin canceling the confirmation dialog, When they click cancel, Then no changes are made.",
        ],
        "labels": ["eval", "admin"],
        "_ground_truth": {
            "label": "CONSIDER",
            "domain": "admin",
            "expected_verdict": "consider",
            "expected_smells": ["compound_gwt"],
            "expected_children_range": [1, 2],
            "notes": "Compound When clause (select + choose + confirm) and compound Then. Borderline: could be one story with tighter ACs, or split happy/unhappy.",
        },
        "_source": "Common workspace-admin feature; appears in Asana, Linear, GitHub admin UIs.",
    },

    {
        "id": "NOTIF-002",
        "title": "Send a one-time announcement email to all active users",
        "description": (
            "Marketing wants to send a feature-launch announcement to all active users. "
            "Build a one-time email send: subject line, HTML body (with template variables), "
            "recipient segmentation (active in last 30 days, by plan tier, by region), "
            "scheduled send time, opt-out link respected (don't send to users who unsubscribed "
            "from product announcements). Track opens and clicks. No A/B testing in this story; "
            "that's a follow-up."
        ),
        "acceptance_criteria": [
            "Given a marketer in the announcement composer, When they enter subject, HTML body, select segments, and set a scheduled send time, Then the announcement is queued and will dispatch at the scheduled time.",
            "Given the scheduled send time arrives, When the dispatcher runs, Then emails are sent only to users matching the selected segments and who have not unsubscribed from announcements.",
            "Given a user opens an announcement email or clicks a link, When the event is captured, Then it is recorded for the campaign's open and click counts visible to the marketer.",
        ],
        "labels": ["eval", "notifications"],
        "_ground_truth": {
            "label": "CONSIDER",
            "domain": "notifications",
            "expected_verdict": "consider",
            "expected_smells": ["compound_gwt", "sprawling_description"],
            "expected_children_range": [1, 3],
            "notes": "Description sprawls (segmentation, opt-out, tracking) but ACs are reasonably tight. Could be one story or split into compose+send / track.",
        },
        "_source": "Standard email-marketing send feature; common in Customer.io, Braze, Mailchimp products.",
    },

    # ────────────────────────────────────────────────────────────────────
    # NO_SLICE — 3 cases. Well-scoped tickets that should not be sliced.
    # The skill should decline (caution path).
    # ────────────────────────────────────────────────────────────────────

    {
        "id": "SEARCH-001",
        "title": "Add a clear-search button to the search bar",
        "description": (
            "The search bar in the top navigation has no way to clear input without "
            "selecting all and deleting. Add a small X icon on the right side of the input "
            "that clears the field and re-runs the empty search (showing all results)."
        ),
        "acceptance_criteria": [
            "Given a user with text in the search bar, When they click the X icon, Then the input is cleared and the search results refresh to show the unfiltered list.",
            "Given an empty search bar, When the user has not typed anything, Then the X icon is hidden.",
        ],
        "labels": ["eval", "search"],
        "_ground_truth": {
            "label": "NO_SLICE",
            "domain": "search",
            "expected_verdict": "no-slice",
            "expected_smells": [],
            "expected_children_range": [0, 0],
            "notes": "Small, single-purpose, well-scoped. No smells should trigger. Skill must decline.",
        },
        "_source": "Trivial polish ticket; representative of small-story sprint filler.",
    },

    {
        "id": "DOC-002",
        "title": "Download a single document as PDF",
        "description": (
            "Users want a quick way to grab a document as a PDF without going through the "
            "share menu. Add a 'Download PDF' option to the per-document menu (...). Export "
            "preserves the document's formatting using the existing PDF renderer."
        ),
        "acceptance_criteria": [
            "Given a user with a document open, When they click 'Download PDF' from the document menu, Then the document is rendered to PDF and downloads with the filename matching the document title.",
            "Given a user without download permission on a document, When they view the document menu, Then the Download PDF option is hidden.",
        ],
        "labels": ["eval", "document"],
        "_ground_truth": {
            "label": "NO_SLICE",
            "domain": "document",
            "expected_verdict": "no-slice",
            "expected_smells": [],
            "expected_children_range": [0, 0],
            "notes": "Single verb, single persona, clean ACs, no smells. Skill must decline.",
        },
        "_source": "Standard 'add export' minor feature; common across document SaaS.",
    },

    {
        "id": "ADMIN-002",
        "title": "Show active user count on the admin dashboard",
        "description": (
            "Admins want at-a-glance visibility into how many users are active. Add a stat "
            "card to the admin dashboard showing the count of users who have signed in within "
            "the last 30 days. Refresh every 5 minutes via the existing dashboard refresh job."
        ),
        "acceptance_criteria": [
            "Given an admin viewing the admin dashboard, When the page loads, Then the active-users stat card displays the count of users who have signed in within the last 30 days.",
        ],
        "labels": ["eval", "admin"],
        "_ground_truth": {
            "label": "NO_SLICE",
            "domain": "admin",
            "expected_verdict": "no-slice",
            "expected_smells": [],
            "expected_children_range": [0, 0],
            "notes": "Trivial. Single AC, single persona, no compound clauses.",
        },
        "_source": "Generic dashboard stat-card ticket.",
    },

    # ────────────────────────────────────────────────────────────────────
    # HALT — 2 cases. Free-form ACs; the skill should halt and ask for G/W/T.
    # ────────────────────────────────────────────────────────────────────

    {
        "id": "MOBILE-002",
        "title": "Improve mobile app launch time",
        "description": (
            "The app's cold-start time is too slow. We need to bring it under 2 seconds on "
            "the iPhone 13 baseline device. Strategies likely include lazy-loading non-essential "
            "modules, removing the synchronous init for the analytics SDK, deferring auth-token "
            "refresh until first network call, and adding a native splash screen to mask init time."
        ),
        "acceptance_criteria": [
            "App launches in under 2 seconds on iPhone 13 from cold start.",
            "Native splash screen displays during cold start.",
            "Analytics SDK initialization does not block the main thread.",
            "Auth token refresh does not run during launch unless needed for the first network request.",
        ],
        "labels": ["eval", "mobile"],
        "_ground_truth": {
            "label": "HALT",
            "domain": "mobile",
            "expected_verdict": "halt-fix-schema",
            "expected_smells": [],
            "expected_children_range": [0, 0],
            "notes": "ACs are free-form imperative statements, not Given/When/Then. Skill must halt and ask for AC review.",
        },
        "_source": "Common perf-optimization ticket; ACs deliberately not converted to G/W/T form (realistic).",
    },

    {
        "id": "API-002",
        "title": "Refactor authentication middleware to use RS256 tokens",
        "description": (
            "Migrate the auth middleware from HS256 to RS256 JWTs. Tokens should be signed "
            "with our private key and verified with the public key. Existing HS256 tokens "
            "remain valid until their natural expiry (one week max). Expired or invalid tokens "
            "return 401. The middleware applies to all /api/v2/* routes."
        ),
        "acceptance_criteria": [
            "Tokens issued by the auth service are signed using RS256 with the new private key.",
            "Verification uses the public key published at /.well-known/jwks.json.",
            "Expired tokens return HTTP 401.",
            "Invalid signatures return HTTP 401.",
            "HS256 tokens issued before the migration continue to verify until their exp claim.",
        ],
        "labels": ["eval", "api"],
        "_ground_truth": {
            "label": "HALT",
            "domain": "api",
            "expected_verdict": "halt-fix-schema",
            "expected_smells": [],
            "expected_children_range": [0, 0],
            "notes": "Technical requirements, not user-facing Given/When/Then. Skill must halt.",
        },
        "_source": "Real-world infra refactor ticket; ACs in 'shall' / 'should' form rather than G/W/T (common in security backlogs).",
    },
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for case in CASES:
        path = OUT_DIR / f"{case['id']}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(case, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"wrote {path.name}")
    print(f"\nTotal: {len(CASES)} test cases.")
    # Print category counts
    from collections import Counter
    labels = Counter(c["_ground_truth"]["label"] for c in CASES)
    domains = Counter(c["_ground_truth"]["domain"] for c in CASES)
    print(f"By label: {dict(labels)}")
    print(f"By domain: {dict(domains)}")


if __name__ == "__main__":
    main()
