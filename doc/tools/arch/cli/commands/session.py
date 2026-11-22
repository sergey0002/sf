"""Kilo session audit command: parser and output only.

Read-only access to the local Kilo SQLite journal. Search, labeling and
aggregation live in :mod:`arch.session_audit`; this module keeps the CLI
surface, exit codes and JSON envelope.
"""

from __future__ import annotations

import argparse
import sqlite3
from typing import Any

from arch.cli.commands.base import Command
from arch.cli.commands.registry import register
from arch.cli.errors import EXIT_ARGS, EXIT_NOT_FOUND, ok_envelope
from arch.project_config import ProjectConfig
from arch.session_audit import (
    digest_session,
    find_sessions,
    open_db,
    resolve_db_path,
    session_events,
)


@register
class SessionCommand(Command):
    """Read-only Kilo session search, digest and drill-down."""

    name = "session"

    def setup_parser(self, subparser: argparse.ArgumentParser) -> None:
        sub = subparser.add_subparsers(dest="session_action", required=True)

        p = sub.add_parser("find", help="find sessions by a dialogue substring")
        p.add_argument("--match", required=True, help="substring to search in dialogue text")
        p.add_argument("--db", help="Kilo SQLite path (default: KILO_AUDIT_DB or ~/.local/share/kilo/kilo.db)")
        p.add_argument("--directory", help="project directory to scope the search")
        p.add_argument("--all-projects", action="store_true", help="search every project in the database")
        p.add_argument("--role", choices=("any", "user", "assistant"), default="any", help="message role filter")
        p.add_argument("--limit", type=int, default=20, help="maximum sessions to return")
        p.add_argument("--json", action="store_true", help="JSON output")

        p = sub.add_parser("digest", help="compact digest of one session with markers and statistics")
        p.add_argument("session_id", nargs="?", help="session ID; omit when using --match")
        p.add_argument("--match", help="resolve the most recent session containing this substring")
        p.add_argument("--db", help="Kilo SQLite path")
        p.add_argument("--directory", help="project directory used by --match")
        p.add_argument("--all-projects", action="store_true", help="resolve --match across every project")
        p.add_argument("--max-events", type=int, default=1000, help="timeline events to keep (head and tail)")
        p.add_argument("--full-text", action="store_true", help="keep full user and assistant text")
        p.add_argument("--no-children", action="store_true", help="skip child session summaries")
        p.set_defaults(json=True)

        p = sub.add_parser("events", help="drill into message or part events of one session")
        p.add_argument("session_id", help="session ID")
        p.add_argument("--message", dest="message_id", help="only this message ID")
        p.add_argument("--part", dest="part_id", help="only this part ID")
        p.add_argument("--offset", type=int, default=0, help="event offset")
        p.add_argument("--limit", type=int, default=100, help="maximum events to return")
        p.add_argument("--full", action="store_true", help="include full text and tool output")
        p.add_argument("--db", help="Kilo SQLite path")
        p.set_defaults(json=True)

    def execute(
        self, args: argparse.Namespace, project_config: ProjectConfig, store: Any
    ) -> int:
        try:
            db_path = resolve_db_path(args.db)
            db = open_db(db_path)
        except (OSError, sqlite3.Error) as exc:
            return self._fail(
                "DB",
                f"cannot open Kilo database: {exc}",
                field="db",
                suggestion="set KILO_AUDIT_DB or pass --db <path>",
                exit_code=1,
                args=args,
            )

        try:
            if args.session_action == "find":
                return self._find(args, db, db_path, project_config)
            if args.session_action == "digest":
                return self._digest(args, db, db_path, project_config)
            if args.session_action == "events":
                return self._events(args, db, db_path)
        except ValueError as exc:
            code = EXIT_NOT_FOUND if "not found" in str(exc) else EXIT_ARGS
            return self._fail(
                "NOT-FOUND" if code == EXIT_NOT_FOUND else "ARGS",
                str(exc),
                field="session_id" if code == EXIT_NOT_FOUND else "match",
                exit_code=code,
                args=args,
            )
        except sqlite3.Error as exc:
            return self._fail("DB", f"Kilo database error: {exc}", exit_code=1, args=args)
        finally:
            db.close()

        return self._fail(
            "ARGS", f"unknown session action: {args.session_action}",
            exit_code=EXIT_ARGS, args=args,
        )

    def _find(
        self,
        args: argparse.Namespace,
        db: sqlite3.Connection,
        db_path: Any,
        project_config: ProjectConfig,
    ) -> int:
        directory = args.directory or str(project_config.root)
        result = find_sessions(
            db,
            args.match,
            directory=directory,
            all_projects=args.all_projects,
            role=args.role,
            limit=args.limit,
        )
        result["db"] = str(db_path)
        if args.json:
            return self._json(ok_envelope(data=result), args)
        print(f"db: {db_path}")
        if not result["sessions"]:
            print("no sessions matched")
            return 0
        for item in result["sessions"]:
            print(
                f"{item['id']}\t{item.get('updated_at') or '-'}\t"
                f"matches={item['match_count']}\t{item.get('title') or '-'}"
            )
            first = item.get("first_match") or {}
            if first:
                snippet = (first.get("snippet") or "").replace("\n", " ")[:120]
                print(f"  {first.get('message_id')} [{first.get('role')}] {snippet}")
        return 0

    def _digest(
        self,
        args: argparse.Namespace,
        db: sqlite3.Connection,
        db_path: Any,
        project_config: ProjectConfig,
    ) -> int:
        session_id = args.session_id
        resolved = None
        if not session_id:
            if not args.match:
                return self._fail(
                    "ARGS", "provide session_id or --match",
                    field="session_id", exit_code=EXIT_ARGS, args=args,
                )
            directory = args.directory or str(project_config.root)
            found = find_sessions(
                db,
                args.match,
                directory=directory,
                all_projects=args.all_projects,
                limit=5,
            )
            if not found["sessions"]:
                raise ValueError(f"session not found by match: {args.match!r}")
            session_id = found["sessions"][0]["id"]
            resolved = {
                "match": args.match,
                "candidates": [
                    {"id": item["id"], "title": item.get("title"), "match_count": item["match_count"]}
                    for item in found["sessions"]
                ],
            }
        data = digest_session(
            db,
            session_id,
            max_events=args.max_events,
            full_text=args.full_text,
            include_children=not args.no_children,
        )
        data["db"] = str(db_path)
        if resolved:
            data["resolved"] = resolved
        return self._json(ok_envelope(data=data), args)

    def _events(
        self,
        args: argparse.Namespace,
        db: sqlite3.Connection,
        db_path: Any,
    ) -> int:
        data = session_events(
            db,
            args.session_id,
            message_id=args.message_id,
            part_id=args.part_id,
            offset=args.offset,
            limit=args.limit,
            full=args.full,
        )
        data["db"] = str(db_path)
        return self._json(ok_envelope(data=data), args)
