"""Application entry point for the arch CLI.

Thin orchestration layer: parses arguments, dispatches to the registered
command, and returns the exit code. Knows nothing about command internals
(other than the Command interface) — follows Dependency Inversion Principle.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from arch.cli.commands.base import Command
from arch.cli.commands.registry import registry
from arch.cli.errors import CliError, error_envelope
from arch.cli.output import print_envelope, is_tty
from arch.store import ArchitectureStore

# Import all command modules so @register decorators execute
from arch.cli.commands import task_key  # noqa: F401
from arch.cli.commands import builtin   # noqa: F401


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with subcommands from the registry."""
    parser = argparse.ArgumentParser(
        description="Deterministic architecture-doc index/read/validation CLI"
    )
    parser.add_argument(
        "--root", type=Path, default=None,
        help="project root (default: parent of doc/tools)",
    )
    parser.add_argument(
        "--version", action="version", version="arch 1.0.0",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # Register each command from the global registry
    for name in registry.names():
        cmd_class = registry.get(name)
        if cmd_class is None:
            continue
        cmd = cmd_class()  # instantiate
        subparser = sub.add_parser(name, help=cmd.help)
        cmd.setup_parser(subparser)
        # Store the instance on the parser for later execution
        subparser.set_defaults(_cmd_instance=cmd)

    return parser


def _default_root() -> Path:
    """Return the project root (parent of doc/tools).

    app.py lives at <root>/doc/tools/arch/cli/app.py -> parents[4] is the project root.
    """
    return Path(__file__).resolve().parents[4]


def run(argv: list[str] | None = None) -> int:
    """Main entry point. Returns an exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    root = args.root.resolve() if args.root else _default_root()
    store = ArchitectureStore(root)

    cmd = getattr(args, "_cmd_instance", None)
    if cmd is None:
        cmd_class = registry.get(args.command)
        if cmd_class is None:
            envelope = error_envelope(
                code="NOT-FOUND",
                message=f"unknown command: {args.command}",
                field="command",
                suggestion=f"available commands: {', '.join(registry.names())}",
                exit_code=20,
            )
            print_envelope(envelope, json_mode=False, stream=sys.stderr)
            return 20
        cmd = cmd_class()

    try:
        return cmd.execute(args, root, store)
    except (ValueError, OSError) as exc:
        envelope = error_envelope(
            code="ERROR",
            message=str(exc),
            exit_code=1,
        )
        print_envelope(envelope, json_mode=False, stream=sys.stderr)
        return 1