"""Rendering of tasks, lists and digests as Telegram HTML.

All user-supplied text goes through `esc`. Lists never use `@mention`/`tg://` links, so
reading a list pings nobody; only deliberate notices (assignment, review) mention people.
"""

from __future__ import annotations

import html
from collections.abc import Iterable, Sequence
from datetime import date

from qul_bot.db.models import Task, TaskComment, User
from qul_bot.domain.enums import ACTIVE_STATUSES, Priority, TaskStatus
from qul_bot.i18n import Translator
from qul_bot.services.tasks import Digest, StatusChange, TaskPage

STATUS_EMOJI: dict[TaskStatus, str] = {
    TaskStatus.TODO: "⚪",
    TaskStatus.DOING: "🔵",
    TaskStatus.REVIEW: "👀",
    TaskStatus.BLOCKED: "⛔",
    TaskStatus.DONE: "✅",
    TaskStatus.CANCELLED: "🚫",
}
PRIORITY_EMOJI: dict[Priority, str] = {
    Priority.URGENT: "🔴",
    Priority.HIGH: "🟠",
    Priority.NORMAL: "🟡",
    Priority.LOW: "🟢",
}

LINE_TITLE_LIMIT = 60
DESCRIPTION_LIMIT = 700
COMMENT_LIMIT = 200


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def truncate(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def user_name(user: User) -> str:
    return esc(user.display_name)


def names(users: Iterable[User]) -> str:
    return ", ".join(user_name(u) for u in users)


def short_names(users: Sequence[User], limit: int = 2, width: int = 18) -> str:
    """Compact assignee list for list rows: `Ali, Vali +3`. Keeps every row bounded."""
    shown = ", ".join(esc(truncate(u.display_name, width)) for u in users[:limit])
    extra = len(users) - limit
    return f"{shown} +{extra}" if extra > 0 else shown


def mention(user: User) -> str:
    """A real Telegram mention: notifies the person. Use deliberately."""
    if user.telegram_id is None:
        return user_name(user)
    return f'<a href="tg://user?id={user.telegram_id}">{user_name(user)}</a>'


def mentions(users: Iterable[User]) -> str:
    return ", ".join(mention(u) for u in users)


def format_date(value: date, today: date) -> str:
    return value.strftime("%d.%m") if value.year == today.year else value.strftime("%d.%m.%Y")


def is_overdue(task: Task, today: date) -> bool:
    return task.due_date is not None and task.due_date < today and task.status in ACTIVE_STATUSES


def source_link(chat_id: int | None, message_id: int | None) -> str | None:
    """Deep link to the message a task came from (supergroups only; basic groups have none)."""
    if chat_id is None or message_id is None or chat_id > -1_000_000_000_000:
        return None
    return f"https://t.me/c/{-chat_id - 1_000_000_000_000}/{message_id}"


def status_label(t: Translator, status: TaskStatus) -> str:
    return f"{STATUS_EMOJI[status]} {t(f'status.{status.value}')}"


def priority_label(t: Translator, priority: Priority) -> str:
    return f"{PRIORITY_EMOJI[priority]} {t(f'priority.{priority.value}')}"


# ---- single task ----------------------------------------------------------------------


def render_card(
    t: Translator,
    task: Task,
    today: date,
    comments: Sequence[TaskComment] = (),
    header: str | None = None,
) -> str:
    lines: list[str] = []
    if header:
        lines += [header, ""]
    lines.append(f"<b>#{task.number}</b> · {status_label(t, task.status)}")
    lines.append(f"<b>{esc(task.title)}</b>")
    if task.description:
        lines += ["", esc(truncate(task.description, DESCRIPTION_LIMIT))]
    lines.append("")
    lines.append(t("card.priority", value=priority_label(t, task.priority)))
    if task.area:
        area = task.area
        label = (
            f"#{esc(area.slug)}"
            if area.name == area.slug
            else f"{esc(area.name)} (#{esc(area.slug)})"
        )
        lines.append(t("card.area", label=label))
    if task.due_date:
        due = task.due_date.strftime("%d.%m.%Y")
        suffix = t("card.overdue") if is_overdue(task, today) else ""
        lines.append(t("card.due", date=due, overdue=suffix))
    assignees = names(task.assignees) if task.assignees else t("card.unassigned")
    lines.append(t("card.assignees", users=assignees))
    lines.append(t("card.reporter", user=user_name(task.reporter)))
    if link := source_link(task.source_chat_id, task.source_message_id):
        lines.append(t("card.source", url=link))
    if comments:
        lines += ["", t("card.comments")]
        lines += [
            f"• <b>{user_name(c.author)}:</b> {esc(truncate(c.body, COMMENT_LIMIT))}"
            for c in comments
        ]
    return "\n".join(lines)


def render_task_line(t: Translator, task: Task, today: date) -> str:
    """One compact list row. `/t42` is tappable in Telegram and opens the task."""
    title = esc(truncate(task.title, LINE_TITLE_LIMIT))
    head = f"/t{task.number} {PRIORITY_EMOJI[task.priority]} {title}"
    meta: list[str] = []
    if task.assignees:
        meta.append(short_names(task.assignees))
    if task.area:
        meta.append(f"#{esc(task.area.slug)}")
    if task.due_date:
        warn = " ⚠️" if is_overdue(task, today) else ""
        meta.append(f"📅 {format_date(task.due_date, today)}{warn}")
    return f"{head} — {' · '.join(meta)}" if meta else head


# ---- lists ----------------------------------------------------------------------------


def render_task_list(t: Translator, page: TaskPage, title: str, today: date) -> str:
    if page.total == 0:
        return f"{title}\n\n{t('list.empty')}"
    lines = [title, t("list.total", count=page.total), ""]
    current: TaskStatus | None = None
    for task in page.items:
        if task.status is not current:
            if current is not None:
                lines.append("")
            current = task.status
            lines.append(f"<b>{status_label(t, current)}</b>")
        lines.append(render_task_line(t, task, today))
    return "\n".join(lines)


def _section(
    t: Translator, title_key: str, tasks: Sequence[Task], today: date, limit: int
) -> list[str]:
    if not tasks:
        return []
    lines = [f"<b>{t(title_key)}</b> ({len(tasks)})"]
    lines += [render_task_line(t, task, today) for task in tasks[:limit]]
    if len(tasks) > limit:
        lines.append(t("digest.more", count=len(tasks) - limit))
    lines.append("")
    return lines


#: Telegram rejects messages over 4096 characters; stay clear of the limit.
MESSAGE_BUDGET = 3900


def render_digest(t: Translator, digest: Digest, today: date, limit: int) -> str:
    """The digest, showing fewer tasks per section until it fits into one message."""
    header = t("digest.title", date=today.strftime("%d.%m.%Y"))
    if digest.is_empty:
        return f"{header}\n\n{t('digest.all_clear')}"
    sections = (
        ("digest.overdue", digest.overdue),
        ("digest.due_today", digest.due_today),
        ("digest.in_review", digest.in_review),
        ("digest.blocked", digest.blocked),
        ("digest.unassigned", digest.unassigned),
    )
    text = header
    for per_section in dict.fromkeys((limit, 5, 3, 1)):
        lines = [header, ""]
        for key, tasks in sections:
            lines += _section(t, key, tasks, today, per_section)
        text = "\n".join(lines).rstrip()
        if len(text) <= MESSAGE_BUDGET:
            break
    return text


# ---- status change notices ------------------------------------------------------------


def render_status_change(
    t: Translator,
    change: StatusChange,
    actor: User,
    *,
    reason: str | None = None,
    reviewers: Sequence[User] = (),
) -> str:
    """The chat notice after a status change, pinging whoever needs to act next."""
    task = change.task
    key = f"changed.{task.status.value}"
    if change.previous is TaskStatus.REVIEW and task.status is TaskStatus.DOING:
        key = "changed.rejected"
    lines = [
        t(key, number=task.number, title=esc(truncate(task.title, 100)), actor=user_name(actor))
    ]
    if reason:
        lines.append(t("changed.reason", reason=esc(truncate(reason, 300))))
    if change.auto_assigned:
        lines.append(t("notify.auto_assigned", user=user_name(actor)))

    if task.status is TaskStatus.REVIEW:
        pending = [u for u in reviewers if u.id != actor.id]
        if pending:
            lines.append(t("notify.reviewers", users=mentions(pending)))
    elif key == "changed.rejected" or task.status is TaskStatus.DONE:
        others = [u for u in task.assignees if u.id != actor.id]
        if others:
            lines.append(t("notify.assignees", users=mentions(others)))
    return "\n".join(lines)
