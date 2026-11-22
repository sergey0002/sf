"""CLI-owned task-number registry stored as JSON.

The registry is the single source of task-number allocation. It is written
only by CLI commands (``task new`` and ``task init``) and read by
``task-key --next``. Nothing else reads or edits the registry file; the
architecture Markdown document only describes the policy.

Layout::

    {
      "schema_version": 1,
      "tasks": [
        {"task_key": "UI-0001", "task_number": "0001", "source": "ui",
         "title": null, "created_at": "2026-11-22T00:00:00Z"}
      ]
    }

Numbers are unique within a source family (UI, Jira, a registered prefix).
The registry does not reserve a number on read: ``task-key --next`` only
previews the next key. Registration happens together with ``task init``.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .fs_atomic import WriterBusyError, lock_directory, write_json_record
from .identity import normalize_task_identity, parse_task_key
from .project_config import ProjectConfig

REGISTRY_NAME = "task-registry.json"
SCHEMA_VERSION = 1


class RegistryError(ValueError):
    """The registry is missing, malformed or conflicts with the request."""


def registry_path(project_config: ProjectConfig) -> Path:
    return project_config.config_root / REGISTRY_NAME


def empty_registry() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "tasks": []}


def _family(source_prefix: str | None) -> str:
    return "" if source_prefix is None else f"{source_prefix}-"


def _validate_entry(entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise RegistryError("task registry entry must be an object")
    key = entry.get("task_key")
    number = entry.get("task_number")
    if not isinstance(key, str) or not isinstance(number, str):
        raise RegistryError("task registry entry requires task_key and task_number")
    try:
        parsed = parse_task_key(key)
    except ValueError as exc:
        raise RegistryError(f"task registry entry has an invalid key: {key!r}") from exc
    if parsed["task_number"] != number:
        raise RegistryError(f"task registry entry number does not match key: {key!r}")
    return entry


def load_registry(
    project_config: ProjectConfig, *, create: bool = False
) -> dict[str, Any]:
    path = registry_path(project_config)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        if create:
            registry = empty_registry()
            save_registry(project_config, registry)
            return registry
        raise RegistryError(
            f"task registry not found: {path}; run `arch task registry init`"
        ) from exc
    except (OSError, ValueError) as exc:
        raise RegistryError(f"cannot read task registry {path}: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
        raise RegistryError(f"unsupported task registry schema in {path}")
    tasks = raw.get("tasks")
    if not isinstance(tasks, list):
        raise RegistryError(f"task registry tasks must be a list: {path}")
    seen_keys: set[str] = set()
    seen_numbers: set[tuple[str, str]] = set()
    for entry in tasks:
        validated = _validate_entry(entry)
        key = validated["task_key"]
        parsed = parse_task_key(key)
        family_number = (_family(parsed["source_prefix"]), parsed["task_number"])
        if key in seen_keys:
            raise RegistryError(f"duplicate task_key in registry: {key}")
        if family_number in seen_numbers:
            raise RegistryError(
                f"duplicate task number {parsed['task_number']} for source family in registry"
            )
        seen_keys.add(key)
        seen_numbers.add(family_number)
    return raw


def save_registry(project_config: ProjectConfig, registry: dict[str, Any]) -> None:
    write_json_record(registry_path(project_config), registry)


def _max_number(registry: dict[str, Any], family: str) -> int:
    numbers = [
        int(parse_task_key(entry["task_key"])["task_number"])
        for entry in registry["tasks"]
        if _family(parse_task_key(entry["task_key"])["source_prefix"]) == family
    ]
    return max(numbers, default=0)


def next_task_key(
    registry: dict[str, Any], source: str, prefix: str | None = None
) -> dict[str, str | None]:
    """Return the next free key for a source without reserving it."""
    if source.strip().lower() != "ui":
        raise RegistryError(
            "--next is only supported for source ui; "
            "Jira and external numbers come from their tracker"
        )
    reference = normalize_task_identity(source, "0000", prefix)
    family = _family(reference["source_prefix"])
    number = _max_number(registry, family) + 1
    if number > 9999:
        raise RegistryError("task number space exhausted")
    return normalize_task_identity(source, f"{number:04d}", prefix)


def find_entry(registry: dict[str, Any], task_key: str) -> dict[str, Any] | None:
    for entry in registry["tasks"]:
        if entry["task_key"] == task_key:
            return entry
    return None


def register_entry(
    registry: dict[str, Any],
    identity: dict[str, str | None],
    *,
    title: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Append an identity to the registry data. Idempotent for the same key."""
    key = identity["task_key"]
    existing = find_entry(registry, key)
    if existing is not None:
        if existing["task_number"] != identity["task_number"]:
            raise RegistryError(f"task key {key} is already registered with another number")
        return existing
    parsed = parse_task_key(key)
    family = _family(parsed["source_prefix"])
    if any(
        _family(parse_task_key(entry["task_key"])["source_prefix"]) == family
        and entry["task_number"] == identity["task_number"]
        for entry in registry["tasks"]
    ):
        raise RegistryError(f"task number {identity['task_number']} is already registered")
    entry = {
        "task_key": key,
        "task_number": identity["task_number"],
        "source": parsed["source_type"],
        "title": title,
        "created_at": created_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    registry["tasks"].append(entry)
    return entry


@contextmanager
def registry_lock(project_config: ProjectConfig) -> Iterator[None]:
    """Serialize allocation and registration against other CLI writers."""
    try:
        with lock_directory(project_config.config_root):
            yield
    except WriterBusyError as exc:
        raise RegistryError(f"task registry is busy: {exc}") from exc


def scan_task_cards(project_config: ProjectConfig) -> dict[str, dict[str, Any]]:
    """Read top-level task cards once; subtask folders and invalid names are skipped."""
    cards: dict[str, dict[str, Any]] = {}
    tasks_root = project_config.tasks_root
    if not tasks_root.is_dir():
        return cards
    for entry in sorted(tasks_root.iterdir(), key=lambda path: path.name):
        if not entry.is_dir() or entry.is_symlink() or entry.name.startswith("."):
            continue
        try:
            parse_task_key(entry.name)
        except ValueError:
            continue
        card = entry / "task.json"
        if not card.is_file():
            continue
        title = None
        number = None
        try:
            data = json.loads(card.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                title = data.get("title")
                number = data.get("task_number")
        except (OSError, ValueError):
            pass
        cards[entry.name] = {
            "task_key": entry.name,
            "task_number": number,
            "title": title,
        }
    return cards


def registry_drift(
    project_config: ProjectConfig,
    registry: dict[str, Any],
    cards: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compare the registry with top-level task cards without writing."""
    cards = scan_task_cards(project_config) if cards is None else cards
    entries = {entry["task_key"]: entry for entry in registry["tasks"]}
    missing_in_registry = sorted(set(cards) - set(entries))
    missing_on_disk = sorted(set(entries) - set(cards))
    number_mismatch = []
    for key in sorted(set(cards) & set(entries)):
        card_number = cards[key].get("task_number") or parse_task_key(key)["task_number"]
        if entries[key]["task_number"] != card_number:
            number_mismatch.append(
                {
                    "task_key": key,
                    "registry_number": entries[key]["task_number"],
                    "task_json_number": card_number,
                }
            )
    return {
        "ok": not (missing_in_registry or missing_on_disk or number_mismatch),
        "cards": len(cards),
        "registry": len(entries),
        "missing_in_registry": missing_in_registry,
        "missing_on_disk": missing_on_disk,
        "number_mismatch": number_mismatch,
    }


def sync_registry(
    project_config: ProjectConfig,
    registry: dict[str, Any],
    *,
    prune: bool = False,
    cards: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Reconcile the registry with task cards. ``prune`` removes stale entries."""
    cards = scan_task_cards(project_config) if cards is None else cards
    added: list[str] = []
    removed: list[str] = []
    for key in sorted(cards):
        parsed = parse_task_key(key)
        card_number = cards[key].get("task_number")
        if card_number is not None and card_number != parsed["task_number"]:
            raise RegistryError(
                f"task.json number {card_number} does not match directory key {key}"
            )
        if find_entry(registry, key) is None:
            register_entry(registry, {"task_key": key, **parsed}, title=cards[key].get("title"))
            added.append(key)
    if prune:
        for entry in list(registry["tasks"]):
            if entry["task_key"] not in cards:
                registry["tasks"].remove(entry)
                removed.append(entry["task_key"])
    return {"added": added, "removed": removed, "count": len(registry["tasks"])}
