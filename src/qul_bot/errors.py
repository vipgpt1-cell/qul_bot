"""Expected, user-facing failures.

Every `AppError` carries a stable `code`. The bot layer translates it through the
`err.<code>` i18n key, so services and domain code never contain user-visible text.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for failures that should be reported to the user, not logged as bugs."""

    def __init__(self, code: str, **params: object) -> None:
        super().__init__(code)
        self.code = code
        self.params = params

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.code!r}, {self.params!r})"


class InputError(AppError):
    """The user's command text could not be understood."""


class NotFoundError(AppError):
    """A referenced task, user, area or workspace does not exist."""


class PermissionDenied(AppError):
    """The user is not allowed to do this."""


class WorkflowError(AppError):
    """The requested status change breaks a workflow rule."""
