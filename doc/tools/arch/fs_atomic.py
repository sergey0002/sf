"""Atomic single-record writes and journals for composite writes.

A single record is replaced atomically: the payload is written to a temporary
file in the same directory, flushed to disk, then moved over the target with
``os.replace``. Readers never observe a half-written ``task.json``.

A composite write (several child records plus a parent update) cannot be
atomic with plain file replacement. It records its intent in a journal first,
performs each atomic step, and removes the journal last. A leftover journal is
the only supported signal of an interrupted composite write.
"""

from __future__ import annotations

import json
import os
import re
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .constants import TASK_NUMBER_RE

JOURNAL_NAME = ".arch-write-journal.json"


class JournalError(ValueError):
    """A present journal cannot be used for recovery."""


class WriterBusyError(OSError):
    """Another cooperating CLI operation owns the task directory."""


@contextmanager
def lock_directory(directory: Path):
    """Non-blocking lock on the existing task directory, without a lock file."""
    try:
        import fcntl
    except ImportError as exc:  # Local lifecycle writers use POSIX directory locks.
        raise OSError("task writes require POSIX file locking") from exc
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise WriterBusyError(f"another task writer is active in {directory}") from exc
        yield
    finally:
        os.close(fd)


def stale_write_temps(path: Path) -> set[Path]:
    """Find regular files in the reserved namespace of this atomic target."""
    name = re.compile(rf"\.{re.escape(path.name)}\.[A-Za-z0-9_-]+\.tmp")
    return {entry for entry in path.parent.glob(f".{path.name}.*.tmp")
            if name.fullmatch(entry.name) and not entry.is_symlink() and entry.is_file()}


def atomic_write_text(path: Path, text: str) -> None:
    """Replace ``path`` with ``text`` without exposing partial content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def write_json_record(path: Path, data: Any) -> None:
    """Serialize ``data`` exactly like existing task records and write atomically."""
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def journal_path(directory: Path) -> Path:
    return directory / JOURNAL_NAME


def read_journal(directory: Path) -> dict[str, Any] | None:
    """Return a valid journal. Absence and invalid recovery state are distinct."""
    path = journal_path(directory)
    try:
        if path.is_symlink():
            raise JournalError("journal is a symbolic link")
        if not stat.S_ISREG(path.stat().st_mode):
            raise JournalError("journal is not a regular file")
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except JournalError:
        raise
    except (ValueError, OSError) as exc:
        raise JournalError(str(exc)) from exc
    if (not isinstance(data, dict) or type(data.get("schema_version")) is not int
            or data["schema_version"] != 1 or data.get("kind") != "decompose"
            or data.get("task_key") != directory.name):
        raise JournalError("invalid schema version, operation or task key")
    package = data.get("subtasks")
    if not isinstance(package, list) or not package:
        raise JournalError("journal requires a non-empty subtask package")
    seen = set()
    for entry in package:
        if not isinstance(entry, dict):
            raise JournalError("invalid journal subtask")
        subtask_id, title = entry.get("id"), entry.get("title")
        if (not isinstance(subtask_id, str) or not TASK_NUMBER_RE.fullmatch(subtask_id)
                or subtask_id in seen or not isinstance(title, str) or not title.strip()):
            raise JournalError("invalid or duplicate journal subtask ID or title")
        seen.add(subtask_id)
    return data


def write_journal(directory: Path, payload: dict[str, Any]) -> Path:
    """Record the intent of a composite write before touching any target."""
    path = journal_path(directory)
    write_json_record(path, payload)
    return path


def clear_journal(directory: Path) -> None:
    """Remove the journal after every composite step has completed."""
    journal_path(directory).unlink(missing_ok=True)
