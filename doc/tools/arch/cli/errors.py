"""Error types, exit codes and envelope construction for the arch CLI.

Follows Agent-Friendly CLI Design from data/cli-skills-encyclopedia:
- Semantic exit codes (not just 0/1) as agent control flow
- Actionable errors: code, message, field, suggestion, exit_code
- Single envelope: {ok, code, data, errors, hints}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Semantic exit codes (agent control flow)
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_ARGS = 2
EXIT_CONFLICT = 5
EXIT_AUTH = 10
EXIT_NOT_FOUND = 20
EXIT_TEMP = 75


@dataclass(frozen=True)
class CliError:
    """A single structured error for agent consumption."""

    code: str
    message: str
    field: str | None = None
    suggestion: str | None = None
    exit_code: int = EXIT_ERROR

    def to_dict(self) -> dict[str, str]:
        entry: dict[str, str] = {
            "code": self.code,
            "message": self.message,
            "exit_code": str(self.exit_code),
        }
        if self.field:
            entry["field"] = self.field
        if self.suggestion:
            entry["suggestion"] = self.suggestion
        return entry


@dataclass(frozen=True)
class CliEnvelope:
    """Single JSON envelope for all command output.

    ok: whether the command succeeded
    code: semantic exit code
    data: command-specific payload (optional)
    errors: list of structured errors (optional)
    hints: actionable fix hints (optional)
    """

    ok: bool
    code: int
    data: Any = None
    errors: list[CliError] | None = None
    hints: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        envelope: dict[str, Any] = {"ok": self.ok, "code": self.code}
        if self.data is not None:
            envelope["data"] = self.data
        if self.errors:
            envelope["errors"] = [e.to_dict() for e in self.errors]
        if self.hints:
            envelope["hints"] = self.hints
        return envelope


def ok_envelope(data: Any = None) -> CliEnvelope:
    return CliEnvelope(ok=True, code=EXIT_OK, data=data)


def error_envelope(
    code: str,
    message: str,
    *,
    field: str | None = None,
    suggestion: str | None = None,
    exit_code: int = EXIT_ERROR,
    data: Any = None,
) -> CliEnvelope:
    return CliEnvelope(
        ok=False,
        code=exit_code,
        data=data,
        errors=[
            CliError(
                code=code,
                message=message,
                field=field,
                suggestion=suggestion,
                exit_code=exit_code,
            )
        ],
    )


def multi_error_envelope(
    errors: list[CliError], data: Any = None
) -> CliEnvelope:
    exit_code = max((e.exit_code for e in errors), default=EXIT_ERROR)
    return CliEnvelope(ok=False, code=exit_code, data=data, errors=errors)