# Architecture

## Goals

1. **Comfortable in a chat.** Capturing a task takes one line; reading the list takes one command.
2. **A real workflow.** Developers finish work into *review*; reviewers decide.
3. **Grow without rewrites.** Later: a GitHub integration, a REST API, and the team's own task
   platform. Telegram must be *a front door*, not the foundation.

## Layers

```text
Telegram ──► bot/            thin: parse the update, call a service, render the answer
                │
                ▼
             services/       all business operations; no Telegram, no user-facing text
                │
        ┌───────┴────────┐
        ▼                ▼
     domain/            db/          pure rules (workflow, roles)  ·  SQLAlchemy models
```

| Package | Responsibility | Must not |
|---|---|---|
| `domain/` | Statuses, roles, the workflow table and permission rules. Pure functions. | import anything I/O related |
| `parsing/` | Turning `#area @user !prio muddat:…` text into structured input. | touch the database |
| `services/` | `TaskService`, `WorkspaceService`, `UserService`. Transactions, events, queries. | know about Telegram or contain Uzbek text |
| `bot/` | Handlers, middlewares, keyboards, HTML rendering. | contain business rules |
| `i18n/` | Message catalogs. Services raise `AppError(code)`; the bot translates `err.<code>`. | — |
| `db/` | Schema and session factory. | — |

**The rule that keeps this future-proof:** a REST API or a web app would call `services/`
exactly like the bot does. If you find yourself writing a business rule in `bot/`, move it.

### Request flow

1. `DbSessionMiddleware` opens **one transaction per Telegram update**: commit on success, roll
   back on any error. Handlers do database work first and send messages last, so a failed send
   undoes the change instead of leaving a task nobody saw.
2. `ContextMiddleware` (only for commands/buttons that matched a handler) enforces the chat
   allow-list, upserts the user, creates the membership on first contact (Telegram admins start as
   admins), and builds a `RequestContext`.
3. The handler calls a service. Failures are `AppError`s with a stable code; one error handler
   translates them for the user.

### Why these choices

* **Long polling, not webhooks.** One small group needs no public URL, TLS or ingress. aiogram can
  switch to webhooks later without touching handlers.
* **Handlers are plain functions** registered in `register(router)`. Routers are built per
  dispatcher, so tests can create many dispatchers (module-level routers can only be attached once).
* **Enums are stored as `VARCHAR`**, not native database enums: adding a status is a code change,
  not a migration.
* **Task numbers** come from an atomic `UPDATE … RETURNING` counter on the workspace — gap-free,
  race-free, never reused (deletes are soft).
* **Lists never mention people** (`@name` and `tg://user` links notify). Only deliberate notices do.
* **Callback data is stateless** (≤ 64 bytes): list pagination carries its whole filter.
* **Messages are bounded.** Telegram rejects text over 4096 characters; rows are truncated and the
  digest shrinks its sections until it fits.

## Data model

```text
workspaces ─┬─ memberships ── users
            ├─ areas
            └─ tasks ─┬─ task_assignees ── users
                      ├─ task_comments
                      └─ task_events        ← append-only log
```

* `workspaces.telegram_chat_id` is nullable and unique: a workspace is *not* a Telegram chat, so
  Slack- or web-created workspaces fit later. A group upgrading to a supergroup changes its chat
  id; the `migrate_to_chat_id` service message is handled so the workspace follows.
* `users.telegram_id` is nullable: a user is *our* identity, and Telegram is one way to reach it.
  Never key anything on `@username`; usernames change and may be absent.
* `memberships.specialty` (mobile, frontend, backend, pm, qa, devops, other) describes the *person*
  and drives the assignee picker; it is separate from `areas`, which describe the *product*.
* `tasks.number` is the human id (`#42`), unique per workspace; `tasks.id` is internal.
* `task_events` records every change (`task.created`, `task.status_changed`, …) with the actor and
  a JSON payload.

## Roles and rules (single source: `domain/workflow.py`)

* Moving *out of* review or done requires a reviewer/admin.
* An assignee cannot approve their own task, unless they are an admin (so a one-person team is
  never stuck).
* Changing a task requires being its assignee, reporter, reviewer/admin — or the task having no
  assignee yet.
* Group admins become bot admins on first contact; `ADMIN_USER_IDS` is the guaranteed bootstrap.

## Integration plan

Everything below is designed *for* but intentionally **not built yet**.

### Outbox → webhooks / integrations

`task_events` is already ordered and complete. To publish it:

1. Add `published_at` (or a separate `outbox` table keyed by `task_events.id`).
2. A small worker reads unpublished events in order and delivers them with retries; consumers
   use `(workspace_id, event id)` as an idempotency key.

Events are written in the same transaction as the change, so nothing is published for a rolled
back change and nothing is lost for a committed one.

### GitHub

* `external_refs(task_id, system, external_id, url)` links a task to an issue/PR.
* Inbound: a GitHub webhook (`push`/`pull_request`) containing `fixes #42` moves task 42 to
  *review* (not *done* — the review step is the point) through `TaskService.change_status`, acting
  as a dedicated integration user.
* Outbound: consume the outbox to open/comment/close issues.

### REST API / web dashboard / own task platform

Add an HTTP layer (FastAPI) next to `bot/` that authenticates a user, resolves the workspace and
calls the same services. `users` and `workspaces` already allow non-Telegram identities.

### More languages

Add `i18n/<locale>.py` with the same keys and register it in `CATALOGS`. A test fails if any key
is missing. `workspaces.locale` selects the language per workspace.

## Roadmap

| Phase | Scope |
|---|---|
| **Done (this version)** | Capture (one-liner + reply), areas, priorities, deadlines, assignees, review workflow, buttons, lists/filters/pagination, digest, comments, soft delete, roles, event log, migrations, Docker, CI |
| **Next** | Scheduled daily digest and deadline reminders (a small scheduler task), private reminders to assignees, mapping forum topics to areas, CSV export |
| **Then** | Outbox + webhooks, GitHub integration, REST API, read-only web dashboard |
| **Later** | Own task platform, more locales, optional AI helpers (e.g. "turn this thread into tasks") |

## Known limitations

* The bot only learns about people when they use a command or are replied to; `@username`
  assignment of someone who never interacted fails with a clear message.
* In a private chat the workspace is inferred when the user belongs to exactly one.
* Digest/reminders are on demand (`/digest`), not scheduled yet.
