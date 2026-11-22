"""task-key command: derive a task key from a four-digit number and source."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from arch.cli.commands.base import Command
from arch.cli.errors import error_envelope
from arch.cli.output import print_envelope
from arch.identity import normalize_task_identity


class TaskKeyCommand(Command):
    """Derive a task key from a four-digit number and source."""

    name = "task-key"

    def setup_parser(self, subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument(
            "--source", required=True,
            help="jira, ui (user input), or another source name",
        )
        subparser.add_argument(
            "--number", required=True, help="exactly four decimal digits",
        )
        subparser.add_argument(
            "--prefix", help="required for non-Jira, non-UI sources",
        )
        subparser.add_argument(
            "--json", action="store_true", help="JSON envelope output",
        )

    def execute(
        self, args: argparse.Namespace, root: Path, store: Any
    ) -> int:
        try:
            result = normalize_task_identity(
                args.source, args.number, args.prefix
            )
        except ValueError as exc:
            envelope = error_envelope(
                code="ARGS",
                message=str(exc),
                field="task_key",
                suggestion="use format: 1234 (Jira), UI-1234 (UI), or PREFIX-1234 (other)",
                exit_code=2,
            )
            print_envelope(envelope, json_mode=getattr(args, "json", False), stream=sys.stderr)
            return 2
        print_envelope(
            self._ok(result), json_mode=getattr(args, "json", False)
        )
        return 0

    @staticmethod
    def _ok(data: Any) -> Any:
        from arch.cli.errors import ok_envelope
        return ok_envelope(data)