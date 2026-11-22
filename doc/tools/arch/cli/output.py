"""Output formatting for the arch CLI.

Responsibilities:
- Print JSON envelope to stdout (agent mode)
- Print human-readable text to stdout (TTY mode)
- Route diagnostics/warnings to stderr
- Respect --json, --brief, --quiet, --verbose flags
"""

from __future__ import annotations

import json
import sys
from typing import Any

from .errors import CliEnvelope, CliError


def is_tty(stream: Any = sys.stdout) -> bool:
    """Return True if the stream is a TTY (human at the terminal)."""
    return hasattr(stream, "isatty") and stream.isatty()


def print_envelope(
    envelope: CliEnvelope,
    *,
    json_mode: bool = False,
    brief: bool = False,
    quiet: bool = False,
    verbose: bool = False,
    stream: Any = sys.stdout,
) -> None:
    """Print a CliEnvelope respecting output mode flags.

    - json_mode: always emit machine-readable JSON envelope
    - brief: one-line OK / N incident(s) summary
    - quiet: print only errors, no OK summary
    - verbose: full per-incident detail (default for non-JSON)
    """
    if json_mode:
        _print_json(envelope, stream)
        return

    if brief:
        _print_brief(envelope, stream)
        return

    if quiet:
        _print_quiet(envelope, stream)
        return

    _print_verbose(envelope, stream)


def _print_json(envelope: CliEnvelope, stream: Any) -> None:
    stream.write(json.dumps(envelope.to_dict(), ensure_ascii=False, indent=2) + "\n")
    stream.flush()


def _print_brief(envelope: CliEnvelope, stream: Any) -> None:
    data = envelope.data or {}
    incident_count = data.get("incident_count", 0)
    error_count = data.get("error_count", 0)
    valid = data.get("valid")

    if valid is not None:
        if valid:
            stream.write("OK\n")
        else:
            stream.write(f"{error_count} error(s)\n")
    elif incident_count > 0:
        stream.write(f"{incident_count} incident(s) found\n")
    else:
        stream.write("OK\n")
    stream.flush()


def _print_quiet(envelope: CliEnvelope, stream: Any) -> None:
    """Print only errors (no OK summary) to save context."""
    errors = envelope.errors or []
    if not errors:
        return
    for err in errors:
        field_part = f" [{err.field}]" if err.field else ""
        stream.write(
            f"[{err.code}] {err.message}{field_part} (exit {err.exit_code})\n"
        )
        if err.suggestion:
            stream.write(f"      fix: {err.suggestion}\n")
    stream.flush()


def _print_verbose(envelope: CliEnvelope, stream: Any) -> None:
    """Full detail (default for non-JSON, non-brief, non-quiet).

    Scan/validate commands carry ``incident_count``/``valid`` in their data and
    get the incident summary. Other structured commands fall back to their JSON
    envelope so that human mode never replaces real data with a scan summary.
    """
    data = envelope.data or {}
    is_scan = (
        "incident_count" in data
        or "scanned_documents" in data
        or "valid" in data
    )
    errors = envelope.errors or []

    if is_scan:
        incident_count = data.get("incident_count", 0)
        scanned = data.get("scanned_documents", 0)
        if incident_count == 0:
            stream.write(f"Scan complete: {scanned} documents scanned, 0 incident(s) found\n")
            stream.write("No issues. All documentation is valid.\n")
        else:
            stream.write(
                f"Scan complete: {scanned} documents scanned, {incident_count} incident(s) found\n"
            )
            stream.write("\n")
            for err in errors:
                field_part = f" [{err.field}]" if err.field else ""
                stream.write(
                    f"[{err.code}] {err.message}{field_part} (exit {err.exit_code})\n"
                )
                if err.suggestion:
                    stream.write(f"      fix: {err.suggestion}\n")
        stream.flush()
        return

    if errors:
        for err in errors:
            field_part = f" [{err.field}]" if err.field else ""
            stream.write(
                f"[{err.code}] {err.message}{field_part} (exit {err.exit_code})\n"
            )
            if err.suggestion:
                stream.write(f"      fix: {err.suggestion}\n")
        stream.flush()
        return

    _print_json(envelope, stream)


def print_stderr(message: str) -> None:
    """Print a diagnostic message to stderr (never stdout in agent mode)."""
    print(message, file=sys.stderr)