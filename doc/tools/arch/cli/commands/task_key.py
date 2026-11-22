"""task-key command: derive a task key from a number or the registry."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from arch.cli.commands.base import Command
from arch.cli.commands.registry import register
from arch.cli.errors import error_envelope
from arch.cli.output import print_envelope
from arch.identity import normalize_task_identity
from arch.task_registry import RegistryError, load_registry, next_task_key


@register
class TaskKeyCommand(Command):
    """Derive a task key from a number or the canonical registry."""

    name = "task-key"

    def setup_parser(self, subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument(
            "--source", required=True,
            help="jira, ui (user input), or another source name",
        )
        subparser.add_argument(
            "--number", help="exactly four decimal digits",
        )
        subparser.add_argument(
            "--next", action="store_true",
            help="derive the next free number for the source from the registry",
        )
        subparser.add_argument(
            "--prefix", help="required for non-Jira, non-UI sources",
        )
        subparser.add_argument(
            "--json", action="store_true", help="JSON envelope output",
        )

    def execute(
        self, args: argparse.Namespace, project_config: Any, store: Any
    ) -> int:
        if bool(args.next) == bool(args.number):
            envelope = error_envelope(
                code="ARGS",
                message="provide exactly one of --number or --next",
                field="task_key",
                suggestion="use --number NNNN for an assigned number or --next for the registry",
                exit_code=2,
            )
            print_envelope(envelope, json_mode=getattr(args, "json", False), stream=sys.stderr)
            return 2
        try:
            if args.next:
                result = next_task_key(
                    load_registry(project_config), args.source, args.prefix
                )
            else:
                result = normalize_task_identity(
                    args.source, args.number, args.prefix
                )
        except (ValueError, RegistryError) as exc:
            envelope = error_envelope(
                code="ARGS",
                message=str(exc),
                field="task_key",
                suggestion="use --number NNNN from the tracker or --next for source ui",
                exit_code=2,
            )
            print_envelope(envelope, json_mode=getattr(args, "json", False), stream=sys.stderr)
            return 2
        print_envelope(
            self._ok(result), json_mode=True
        )
        return 0

    @staticmethod
    def _ok(data: Any) -> Any:
        from arch.cli.errors import ok_envelope
        return ok_envelope(data)