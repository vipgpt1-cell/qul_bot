# Qul Bot

A Telegram group task tracker for IT teams. Turn a chat message into a task, follow it through
**todo → doing → review → done**, and let developers see their own work with `/my`.

* **Fast capture** – `/task Fix login crash #mobile @username !high muddat:friday`, or reply to
  any message with `/task`.
* **A real review step** – developers finish into *review*; only a reviewer or admin approves.
* **Calm in the group** – lists ping nobody; the bot edits cards in place and only mentions
  people when they must act.
* **Built to grow** – every change is logged as an event, business logic is independent of
  Telegram, and the schema is ready for your own task platform and a GitHub integration.

The bot speaks **Uzbek** (see [`docs/GUIDE_UZ.md`](docs/GUIDE_UZ.md) for the team guide).
Code and developer docs are in English.

## Quick start

### 1. Create the bot

1. Talk to [@BotFather](https://t.me/BotFather): `/newbot`, and keep the **token**.
2. Leave **privacy mode enabled** (the default). The bot then only receives commands and replies
   to it — it never reads ordinary chatter. Replying to a message with `/task` works in this mode.
3. Add the bot to your team group. Making it a group **admin** is recommended (no special rights
   needed): Telegram then lets it recognise the group's admins.

### 2. Configure

```bash
cp .env.example .env
```

Send `/chatid` in the group (it works before anything is configured) — the bot answers with the
**chat id** and **your user id**. Put them into `.env`:

| Variable | Meaning |
|---|---|
| `BOT_TOKEN` | Token from BotFather. Required. |
| `ALLOWED_CHAT_IDS` | Groups the bot serves (comma-separated). Other groups are ignored. |
| `ADMIN_USER_IDS` | Telegram user ids that are always admins. Guarantees you can bootstrap. |
| `DATABASE_URL` | `sqlite+aiosqlite:///./qul_bot.db` (default) or `postgresql+asyncpg://…` |
| `DEFAULT_TIMEZONE` | Timezone of new workspaces. Default `Asia/Tashkent`. |
| `DEFAULT_LOCALE` | `uz` (the only catalog today). |
| `LOG_LEVEL` | `INFO` by default. |

`postgres://…` / `postgresql://…` URLs from hosting providers are accepted and converted.

### 3. Run

**Docker (PostgreSQL included):**

```bash
docker compose up -d --build
```

**Docker with a hosted database (e.g. [Neon](https://neon.tech)):** put Neon's connection string
into `.env` as `DATABASE_URL` and run only the bot:

```bash
docker compose -f docker-compose.neon.yml up -d --build
```

Use Neon's *direct* connection (the host without `-pooler`). `sslmode=require` and
`channel_binding=require` in the string are converted automatically. Neon's free compute suspends
when idle; the bot reconnects on its own, so the first command after a quiet period can take
a second longer. The bot itself still needs an always-on machine to run on.

**Locally (SQLite, no services):**

```bash
make install          # creates .venv, installs the project with dev tools
.venv/bin/alembic upgrade head
make run
```

### 4. Set up the team (once, in the group)

```text
/addarea mobile Mobil ilova      # areas: your teams or product parts
/addarea backend
/role @username reviewer         # who approves finished work
/team                            # check roles
```

Group admins start as bot admins. Everybody else starts as a member, and becomes known to the bot
the first time they use a command.

## How it works

### Creating tasks

```text
/task Fix login crash on iOS #mobile @alisher !high muddat:friday
```

| Token | Meaning |
|---|---|
| `#mobile` | area (create with `/addarea`) |
| `@alisher` | assignee, repeatable (must have used the bot once, or reply to them) |
| `!high` | priority: `urgent`, `high`, `normal`, `low` — or `shoshilinch`, `yuqori`, `o'rta`, `past` |
| `muddat:…` | deadline: `bugun`, `ertaga`, `juma`, `25.10`, `25.10.2026`, `3d`, `2w` (`due:` works too) |

Everything else is the title; extra lines become the description. **Reply** to any message with
`/task` to turn it into a task — the card is posted under that message and links back to it.

### The workflow

```text
 todo ──► doing ──► review ──► done
   │        │          │         │
   └─► blocked   ◄─ rejected     └─► reopen (todo)
```

| Command | Effect | Who |
|---|---|---|
| `/doing 12` | start (assigns you if nobody is) | assignee, reporter, anyone if unassigned |
| `/done 12` | developers → **review**; a reviewer's `/done` on a task in review → **done** | see below |
| `/ready 12` | → review | assignee, reporter, anyone if unassigned |
| `/approve 12` | review → done | reviewer or admin, **not the assignee** (admins may) |
| `/reject 12 reason` | review → doing, with a comment | reviewer or admin |
| `/block 12 reason` | → blocked | assignee, reporter, reviewer, admin |
| `/reopen 12` | done/cancelled → todo | reviewer/admin (done); anyone involved (cancelled) |
| `/cancel 12 reason` | → cancelled | assignee, reporter, reviewer, admin (out of review: reviewer/admin) |

Every task card also has buttons for these actions, plus **🙋 Me** and **🚦 Priority**.
Mentions happen only when someone must act: reviewers are pinged when work enters review, assignees
when it is approved or sent back.

### Finding things

| Command | Shows |
|---|---|
| `/my` | tasks assigned to you (works in a private chat with the bot too) |
| `/list [filters]` | open tasks, e.g. `/list mobile !high review`, `/list @alisher`, `/list all` |
| `/review` | tasks waiting for review |
| `/mobile` | any area name works as a shortcut |
| `/digest` | overdue, due today, in review, blocked, unassigned |
| `/info 12` or `/t12` | one task with comments (`/t12` is tappable in lists) |

### Editing

`/edit 12 New title #backend !urgent muddat:ertaga` · `/assign 12 @user` (or reply to a person,
or just `/assign 12` for yourself) · `/unassign 12 @user` · `/comment 12 text` ·
`/delete 12` (asks first; admin or author) · `/restore 12` (admin).

Use `#-` or `muddat:-` in `/edit` to clear the area or the deadline.

### Roles

| Role | Can |
|---|---|
| **member** | create tasks, work on their own, comment |
| **reviewer** | also approve/reject work and reopen done tasks (not their own) |
| **admin** | everything, including `/addarea`, `/delarea`, `/role`, `/restore` |

## Development

```bash
make install
make check        # ruff, mypy --strict, pytest
make test-pg TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/qul_test
```

The suite (≈280 tests) runs on SQLite by default and on PostgreSQL in CI. It includes
end-to-end tests that drive the real dispatcher against a fake Telegram API
(`tests/fake_telegram.py`), and a test proving migrations match the models.

Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) before changing the structure, and
[`CLAUDE.md`](CLAUDE.md) for the conventions in short.

### Migrations

```bash
make migration m="add something"      # autogenerate; review the file!
make migrate
```

Generate against PostgreSQL with `alembic -x batch=0 revision --autogenerate …`.

## License

Private project. All rights reserved.
