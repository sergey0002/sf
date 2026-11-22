"""Command registry for the arch CLI.

Follows the Open/Closed Principle: new commands are registered here
without modifying the dispatcher or the main entry point.
"""

from __future__ import annotations

from typing import Protocol

from arch.cli.commands.base import Command


class CommandRegistry(Protocol):
    """Protocol for command registries."""

    def register(self, command: Command) -> None: ...
    def get(self, name: str) -> Command | None: ...
    def names(self) -> list[str]: ...


class SimpleCommandRegistry:
    """In-memory command registry.

    Commands are discovered and registered at startup.
    """

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        self._commands[command.name] = command

    def get(self, name: str) -> Command | None:
        return self._commands.get(name)

    def names(self) -> list[str]:
        return sorted(self._commands.keys())


# Global registry instance
registry = SimpleCommandRegistry()


def register(command: Command) -> None:
    """Decorator/helper to register a command globally."""
    registry.register(command)