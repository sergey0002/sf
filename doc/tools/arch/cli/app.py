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

from arch import __version__
from arch.cli.commands.base import Command
from arch.cli.commands.registry import registry
from arch.cli.errors import CliError, error_envelope
from arch.cli.output import print_envelope, is_tty
from arch.store import ArchitectureStore
from arch.project_config import load_project_config, ProjectConfig

# Import all command modules so @register decorators execute
from arch.cli.commands import task_key  # noqa: F401
from arch.cli.commands import builtin   # noqa: F401
from arch.cli.commands import task      # noqa: F401
from arch.cli.commands import session   # noqa: F401


class _LazyStore:
    """Construct ArchitectureStore only when a command actually reads documents."""

    def __init__(self, project_config: ProjectConfig) -> None:
        self._project_config = project_config
        self._store: ArchitectureStore | None = None

    def __getattr__(self, name: str) -> Any:
        if self._store is None:
            self._store = ArchitectureStore(self._project_config)
        return getattr(self._store, name)


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with subcommands from the registry."""
    parser = argparse.ArgumentParser(
        description="Deterministic architecture and task CLI",
        epilog="Operator guide: doc/skills/arch-cli/SKILL.md. Run <command> --help for its options.",
    )
    parser.add_argument(
        "--root", type=Path, default=None,
        help="project root (default: parent of doc/tools)",
    )
    parser.add_argument(
        "--config", type=Path, default=None,
        help="explicit path to project config (paths.yaml), relative to --root or absolute",
    )
    parser.add_argument(
        "--version", action="version", version=f"arch {__version__}",
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

    # Load project configuration
    project_config, config_errors = load_project_config(root, args.config)
    if config_errors:
        for err in config_errors:
            envelope = error_envelope(
                code="CONFIG",
                message=err,
                exit_code=1,
            )
            print_envelope(envelope, json_mode=False, stream=sys.stderr)
        return 1

    store = _LazyStore(project_config)

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
        return cmd.execute(args, project_config, store)
    except (ValueError, OSError) as exc:
        envelope = error_envelope(
            code="ERROR",
            message=str(exc),
            exit_code=1,
        )
        print_envelope(envelope, json_mode=False, stream=sys.stderr)
        return 1