# Conventions for working in this repo

Run before every commit: `make check` (ruff, `mypy --strict`, pytest). Tests also run on PostgreSQL
in CI; locally use `make test-pg`.

* **Layering** (see `docs/ARCHITECTURE.md`): business rules live in `domain/` and `services/`;
  `bot/` only parses updates, calls services and renders. Services never contain user-facing text:
  they raise `AppError(code, **params)` and the bot shows `err.<code>` from `i18n/uz.py`.
* **Every user-visible string** goes in `i18n/uz.py`. `tests/test_i18n.py` fails on missing,
  unused or invalid-HTML messages. New command → add it to `bot/commands.py` and to
  `RESERVED_SLUGS` in `domain/areas.py` (a test enforces both).
* **Handlers** are plain async functions, registered in the module's `register(router)`; never
  create module-level routers.
* **User text is escaped** with `formatting.esc` before it enters HTML. Lists must not mention
  people; only deliberate notices use `mention()`.
* **Telegram limits:** 4096 chars per message, 64 bytes of callback data. Keep rows bounded.
* **Schema changes** need an Alembic migration (`make migration m="…"`, review it, keep it free of
  application imports). `tests/test_migrations.py` fails when models and migrations drift.
* **Timestamps** are timezone-aware UTC (`UTCDateTime`). "Today" is computed in the workspace
  timezone (`RequestContext.today`).
* Never key anything on `@username`; use user ids.
