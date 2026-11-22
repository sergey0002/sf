"""Base command class for the arch CLI.

Every command implements:
- name() -> str
- setup_parser(subparser) -> None
- execute(args, root, store) -> int

This follows the Command pattern and Liskov Substitution Principle:
all commands share the same interface and can be substituted interchangeably.
"""

from __future__ import annotations

import argparse
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from arch.cli.errors import CliEnvelope, CliError, ok_envelope, error_envelope
from arch.cli.output import print_envelope, is_tty


class Command(ABC):
    """Abstract base for all CLI commands.

    Subclasses set ``name`` as a class attribute (e.g. ``name = "scan"``)
    so the command registry can discover them without instantiation.
    """

    name: str = ""
    help: str = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.name:
            raise TypeError(f"{cls.__name__} must define a non-empty 'name' class attribute")
        if not cls.help:
            cls.help = cls.__doc__ or ""

    @abstractmethod
    def setup_parser(self, subparser: argparse.ArgumentParser) -> None:
        """Add command-specific arguments to the subparser."""

    @abstractmethod
    def execute(
        self, args: argparse.Namespace, root: Path, store: Any
    ) -> int:
        """Execute the command and return an exit code."""

    # --- helpers ---------------------------------------------------------

    def _json(
        self,
        envelope: CliEnvelope,
        args: argparse.Namespace,
        stream: Any = sys.stdout,
    ) -> int:
        """Print a JSON envelope and return the exit code."""
        print_envelope(
            envelope,
            json_mode=True,
            stream=stream,
        )
        return envelope.code

    def _text(
        self,
        envelope: CliEnvelope,
        args: argparse.Namespace,
        stream: Any = sys.stdout,
    ) -> int:
        """Print human-readable output and return the exit code."""
        print_envelope(
            envelope,
            json_mode=False,
            brief=getattr(args, "brief", False),
            quiet=getattr(args, "quiet", False),
            verbose=getattr(args, "verbose", False),
            stream=stream,
        )
        return envelope.code

    def _fail(
        self,
        code: str,
        message: str,
        *,
        field: str | None = None,
        suggestion: str | None = None,
        exit_code: int = 1,
        data: Any = None,
        args: argparse.Namespace | None = None,
        stream: Any = sys.stderr,
    ) -> int:
        """Print a structured error to stderr and return exit code."""
        envelope = error_envelope(
            code=code,
            message=message,
            field=field,
            suggestion=suggestion,
            exit_code=exit_code,
            data=data,
        )
        if args and getattr(args, "json", False):
            print_envelope(envelope, json_mode=True, stream=stream)
        else:
            err = envelope.errors[0] if envelope.errors else None
            if err:
                field_part = f" [{err.field}]" if err.field else ""
                stream.write(
                    f"[{err.code}] {err.message}{field_part} (exit {err.exit_code})\n"
                )
                if err.suggestion:
                    stream.write(f"      fix: {err.suggestion}\n")
        stream.flush()
        return exit_code