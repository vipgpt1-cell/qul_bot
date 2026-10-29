"""Status changes shared by commands (`/approve 12`) and card buttons."""

from __future__ import annotations

from qul_bot.bot.commands import DONE_COMMAND, STATUS_COMMANDS
from qul_bot.bot.formatting import render_status_change
from qul_bot.db.models import Task, User
from qul_bot.domain.enums import TaskStatus
from qul_bot.domain.workflow import approve_target, done_target
from qul_bot.i18n import Translator
from qul_bot.services.tasks import StatusChange, TaskService


async def target_for(service: TaskService, task: Task, command: str) -> TaskStatus:
    """The status a command leads to *for this task right now* (QA step aware)."""
    qa_active = await service.qa_active(task.workspace_id)
    if command == DONE_COMMAND:
        return done_target(task.status, qa_active)
    if command == "approve":
        return approve_target(task.status, qa_active)
    return STATUS_COMMANDS[command]


async def notice_for(
    service: TaskService,
    t: Translator,
    change: StatusChange,
    actor: User,
    reason: str | None = None,
) -> str:
    workspace_id = change.task.workspace_id
    return render_status_change(
        t,
        change,
        actor,
        reason=reason,
        reviewers=await service.workspaces.reviewers(workspace_id),
        testers=await service.workspaces.testers(workspace_id),
    )
