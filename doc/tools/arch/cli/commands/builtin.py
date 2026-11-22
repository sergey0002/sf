"""Built-in command implementations for the arch CLI.

Each command is a separate class implementing the Command interface.
This follows SRP (one responsibility per class) and LSP (all commands
are substitutable via the Command base class).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from arch.cli.commands.base import Command
from arch.cli.commands.registry import register
from arch.cli.errors import (
    CliError,
    CliEnvelope,
    EXIT_ARGS,
    EXIT_CONFLICT,
    EXIT_ERROR,
    EXIT_NOT_FOUND,
    EXIT_OK,
    error_envelope,
    multi_error_envelope,
    ok_envelope,
)
from arch.cli.output import print_envelope, print_stderr

from arch.store import ArchitectureStore
from arch.validation import (
    validate_task_json,
    validate_paths,
    load_task_conf_types,
    load_task_conf_flows_for_type,
    load_task_conf_prompt,
    load_task_conf_flow_prompt,
    check_subtasks_closed,
)
from arch.identity import (
    normalize_task_identity,
    parse_task_key,
    task_dir,
    TASK_NUMBER_RE,
)
from arch.schema import scaffold_task_json, TASK_DIR_TEMPLATE
from arch.subtask import subtask_dir, scaffold_subtask_json, list_stages, list_sub_subtasks
from arch.body_validation import validate_document_body


# ============================================================================
# List command
# ============================================================================

@register
class ListCommand(Command):
    """List docs by exact metadata filters."""

    name = "list"

    def setup_parser(self, subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--type", dest="doc_type")
        subparser.add_argument("--domain")
        subparser.add_argument("--status")
        subparser.add_argument("--json", action="store_true", help="JSON envelope output")

    def execute(self, args: argparse.Namespace, root: Path, store: ArchitectureStore) -> int:
        docs, errors = store.load_documents()
        if errors:
            errs = [CliError(code="DOC-LOAD", message=e, exit_code=1) for e in errors]
            envelope = multi_error_envelope(errs)
            print_envelope(envelope, json_mode=getattr(args, "json", False), stream=sys.stderr)
            return 1

        items = []
        for doc in docs:
            md = doc.metadata
            if args.doc_type and md.get("type") != args.doc_type:
                continue
            if args.domain and md.get("domain") != args.domain:
                continue
            if args.status and md.get("status") != args.status:
                continue
            items.append({
                "id": md["id"],
                "type": md["type"],
                "title": md["title"],
                "domain": md.get("domain"),
                "status": md["status"],
                "path": doc.relative_path,
            })
        items.sort(key=lambda x: x["id"])

        if getattr(args, "json", False):
            print_envelope(ok_envelope(data=items), json_mode=True)
        else:
            for item in items:
                print(
                    f"{item['id']}\t{item['type']}\t"
                    f"{item.get('domain') or '-'}\t{item['path']}\t{item['title']}"
                )
        return 0


# ============================================================================
# Show command
# ============================================================================

@register
class ShowCommand(Command):
    """Show one exact document ID."""

    name = "show"

    def setup_parser(self, subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("id", help="document ID (e.g. SYS-simple-factory)")
        subparser.add_argument(
            "--format", choices=("markdown", "json"), default="markdown",
        )

    def execute(self, args: argparse.Namespace, root: Path, store: ArchitectureStore) -> int:
        docs, errors = store.load_documents()
        if errors:
            errs = [CliError(code="DOC-LOAD", message=e, exit_code=1) for e in errors]
            envelope = multi_error_envelope(errs)
            print_envelope(envelope, json_mode=False, stream=sys.stderr)
            return 1

        matches = [doc for doc in docs if doc.metadata.get("id") == args.id]
        if len(matches) != 1:
            return self._fail(
                "NOT-FOUND",
                f"expected exactly one document for id {args.id!r}, found {len(matches)}",
                field="id",
                suggestion="use `arch list` to see available document IDs",
                exit_code=EXIT_NOT_FOUND,
                args=args,
            )

        doc = matches[0]
        if args.format == "json":
            print_envelope(
                ok_envelope(data={
                    "metadata": doc.metadata,
                    "path": doc.relative_path,
                    "content": doc.body,
                }),
                json_mode=True,
            )
        else:
            print(doc.body, end="" if doc.body.endswith("\n") else "\n")
        return 0


# ============================================================================
# Index command
# ============================================================================

@register
class IndexCommand(Command):
    """Build/check generated index."""

    name = "index"

    def setup_parser(self, subparser: argparse.ArgumentParser) -> None:
        sub = subparser.add_subparsers(dest="index_action", required=True)
        sub.add_parser("build", help="validate sources then atomically build index.json")
        sub.add_parser("check", help="check index freshness without writing")

    def execute(self, args: argparse.Namespace, root: Path, store: ArchitectureStore) -> int:
        if args.index_action == "build":
            index, errors = store.build_index()
            if errors:
                errs = [CliError(code="INDEX", message=e, exit_code=1) for e in errors]
                envelope = multi_error_envelope(errs)
                print_envelope(envelope, json_mode=False, stream=sys.stderr)
                return 1
            assert index is not None
            store.write_index(index)
            print(f"Index built: {len(index['documents'])} documents")
            return 0

        errors = store.validate(check_index=True)
        if errors:
            errs = [CliError(code="INDEX", message=e, exit_code=1) for e in errors]
            envelope = multi_error_envelope(errs)
            print_envelope(envelope, json_mode=False, stream=sys.stderr)
            return 1
        print("Index is current")
        return 0


# ============================================================================
# Validate command
# ============================================================================

@register
class ValidateCommand(Command):
    """Validate architecture documents (all or a specific path)."""

    name = "validate"

    def setup_parser(self, subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("path", nargs="?", help="specific document or directory to validate")
        subparser.add_argument("--json", action="store_true", help="JSON envelope output")
        subparser.add_argument("--quiet", action="store_true", help="print only errors, no OK summary")
        subparser.add_argument("--brief", action="store_true", help="one-line summary: OK or N error(s)")

    def execute(self, args: argparse.Namespace, root: Path, store: ArchitectureStore) -> int:
        if args.path:
            target = root / args.path
            if not target.exists():
                return self._fail(
                    "NOT-FOUND", f"path not found: {args.path}",
                    field="path", suggestion="check the path relative to project root",
                    exit_code=EXIT_NOT_FOUND, args=args,
                )
            if target.is_file() and target.suffix == ".md":
                try:
                    metadata, body = store._parse_frontmatter(target)
                except (OSError, ValueError) as exc:
                    return self._fail(
                        "DOC-LOAD", f"{args.path}: {exc}",
                        exit_code=EXIT_ERROR,
                        suggestion=f"fix frontmatter in {args.path}",
                        args=args,
                    )
                schema = store._load_schema(store.document_schema_path)
                errors = store._validate_instance(metadata, schema, f"{args.path}:")
                doc_type = metadata.get("type")
                if doc_type:
                    schemas_dir = store.docs / "schemas"
                    body_errors = validate_document_body(body, doc_type, schemas_dir)
                    for be in body_errors:
                        errors.append(f"{args.path}: {be}")
            else:
                errors = [f"single-file validation supports only .md files, got: {args.path}"]
        else:
            errors = store.validate(check_index=True)

        json_mode = getattr(args, "json", False)
        brief = getattr(args, "brief", False)
        quiet = getattr(args, "quiet", False)

        if json_mode:
            envelope = ok_envelope(
                data={"valid": not errors, "error_count": len(errors), "path": args.path}
            ) if not errors else multi_error_envelope(
                [CliError(code="VALIDATION", message=e, exit_code=1) for e in errors],
                data={"valid": False, "error_count": len(errors), "path": args.path},
            )
            print_envelope(envelope, json_mode=True)
            return 1 if errors else 0

        if brief:
            if not errors:
                print("OK")
            else:
                print(f"{len(errors)} error(s)")
            return 1 if errors else 0

        if quiet:
            if not errors:
                return 0
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1

        if not errors:
            print("Architecture documentation is valid")
        else:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
        return 1 if errors else 0


# ============================================================================
# Scan command
# ============================================================================

@register
class ScanCommand(Command):
    """Scan documentation and report every incident."""

    name = "scan"

    def setup_parser(self, subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument(
            "--scope", choices=("all", "docs", "tasks", "task-conf", "index", "paths"),
            default="all", help="what to scan (default: all)",
        )
        subparser.add_argument("--json", action="store_true", help="JSON envelope output")
        subparser.add_argument("--fix-hints", action="store_true",
                               help="include actionable fix suggestions for each incident")
        subparser.add_argument("--quiet", action="store_true",
                               help="print only incidents, no OK summary (saves context)")
        subparser.add_argument("--brief", action="store_true",
                               help="one-line summary: OK or N incident(s) found")
        subparser.add_argument("--verbose", action="store_true",
                               help="full per-incident detail (default for non-JSON)")

    def execute(self, args: argparse.Namespace, root: Path, store: ArchitectureStore) -> int:
        scope = args.scope
        errors: list[str] = []
        incidents: list[CliError] = []
        scanned_count = 0

        # --- Documents ---
        docs = []
        if scope in ("all", "docs"):
            docs, load_errors = store.load_documents()
            scanned_count = len(docs)
            for le in load_errors:
                incidents.append(CliError(code="DOC-LOAD", message=le, exit_code=1))
                errors.append(le)

            link_errors = store.validate_links(docs)
            for le in link_errors:
                incidents.append(CliError(code="DOC-LINK", message=le, exit_code=1))
                errors.append(le)

            related_errors = store.validate_related(docs)
            for re_ in related_errors:
                incidents.append(CliError(code="DOC-RELATED", message=re_, exit_code=1))
                errors.append(re_)

            schemas_dir = store.docs / "schemas"
            for doc in docs:
                doc_type = doc.metadata.get("type")
                if doc_type:
                    body_errors = validate_document_body(doc.body, doc_type, schemas_dir)
                    for be in body_errors:
                        incidents.append(CliError(
                            code="DOC-BODY",
                            message=f"{doc.relative_path}: {be}",
                            exit_code=1,
                            suggestion=f"fix body structure in {doc.relative_path}",
                        ))
                        errors.append(f"{doc.relative_path}: {be}")

        # --- Index ---
        if scope in ("all", "index"):
            try:
                actual_index = json.loads(store.index_path.read_text(encoding="utf-8"))
                expected_index = store.make_index(docs)
                if actual_index != expected_index:
                    msg = "doc/architecture/index.json: stale; run `arch index build`"
                    incidents.append(CliError(code="DOC-INDEX", message=msg, exit_code=1,
                                              suggestion="run `arch index build` to regenerate"))
                    errors.append(msg)
            except FileNotFoundError:
                msg = "doc/architecture/index.json: missing; run `arch index build`"
                incidents.append(CliError(code="DOC-INDEX", message=msg, exit_code=1,
                                          suggestion="run `arch index build` to regenerate"))
                errors.append(msg)
            except json.JSONDecodeError as exc:
                msg = f"doc/architecture/index.json: invalid JSON: {exc}"
                incidents.append(CliError(code="DOC-INDEX", message=msg, exit_code=1))
                errors.append(msg)

        # --- Paths ---
        if scope in ("all", "paths"):
            path_errors = validate_paths(root)
            for pe in path_errors:
                incidents.append(CliError(code="PATH", message=pe, exit_code=1,
                                          suggestion="add path to doc/config/paths.yaml allowed_paths or remove the file"))
                errors.append(pe)

        # --- Tasks ---
        if scope in ("all", "tasks"):
            task_errors = _scan_all_tasks(root)
            for te in task_errors:
                incidents.append(CliError(
                    code="TASK", message=te["message"],
                    field=te.get("field"),
                    suggestion=te.get("suggestion"),
                    exit_code=1,
                ))
                errors.append(te["message"])

        # --- Task-conf ---
        if scope in ("all", "task-conf"):
            task_conf_errors = _scan_task_conf(root)
            for tce in task_conf_errors:
                incidents.append(CliError(code="TASK-CONF", message=tce, exit_code=1))
                errors.append(tce)

        total = len(incidents)
        json_mode = getattr(args, "json", False)

        if json_mode:
            envelope = ok_envelope(
                data={
                    "scope": scope,
                    "scanned_documents": scanned_count,
                    "incident_count": total,
                    "incidents": [i.to_dict() for i in incidents],
                }
            ) if not errors else multi_error_envelope(
                incidents,
                data={
                    "scope": scope,
                    "scanned_documents": scanned_count,
                    "incident_count": total,
                    "incidents": [i.to_dict() for i in incidents],
                },
            )
            print_envelope(envelope, json_mode=True)
            return 1 if total > 0 else 0

        brief = getattr(args, "brief", False)
        quiet = getattr(args, "quiet", False)

        if brief:
            if total == 0:
                print("OK")
            else:
                print(f"{total} incident(s) found")
            return 1 if total > 0 else 0

        if quiet:
            if total == 0:
                return 0
            for inc in incidents:
                field_part = f" [{inc.field}]" if inc.field else ""
                print(
                    f"[{inc.code}] {inc.message}{field_part} (exit {inc.exit_code})",
                    file=sys.stderr,
                )
                if getattr(args, "fix_hints", False) and inc.suggestion:
                    print(f"      fix: {inc.suggestion}", file=sys.stderr)
            return 1

        # Verbose (default)
        print(f"Scan complete: {scanned_count} documents scanned, {total} incident(s) found")
        if total == 0:
            print("No issues. All documentation is valid.")
        else:
            print()
            for inc in incidents:
                field_part = f" [{inc.field}]" if inc.field else ""
                print(f"[{inc.code}] {inc.message}{field_part} (exit {inc.exit_code})")
                if getattr(args, "fix_hints", False) and inc.suggestion:
                    print(f"      fix: {inc.suggestion}")
        return 1 if total > 0 else 0


def _scan_all_tasks(root: Path) -> list[dict[str, str]]:
    """Scan every task.json under doc/tasks/ and return incidents."""
    incidents: list[dict[str, str]] = []
    tasks_root = root / "doc" / "tasks"
    if not tasks_root.is_dir():
        return incidents

    for task_dir_path in sorted(tasks_root.iterdir()):
        if not task_dir_path.is_dir():
            continue
        task_key = task_dir_path.name
        tjson = task_dir_path / "task.json"
        if not tjson.exists():
            incidents.append({
                "message": f"task {task_key}: task.json missing",
                "field": "task.json",
                "suggestion": f"create {tjson.relative_to(root)}",
            })
            continue
        try:
            data = json.loads(tjson.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            incidents.append({
                "message": f"task {task_key}: task.json invalid JSON: {exc}",
                "field": "task.json",
                "suggestion": f"fix JSON syntax in {tjson.relative_to(root)}",
            })
            continue
        errors = validate_task_json(data, task_key, root)
        task_md = task_dir_path / "task.md"
        if task_md.exists():
            errors.append(
                "task.md exists; manifest requires task.json as the only canonical input"
            )
        for err in errors:
            incidents.append({
                "message": f"task {task_key}: {err}",
                "field": "task.json",
                "suggestion": f"fix {tjson.relative_to(root)}",
            })

        subtasks_dir = task_dir_path / "subtasks"
        if subtasks_dir.is_dir():
            for st_dir in sorted(subtasks_dir.iterdir()):
                if not st_dir.is_dir():
                    continue
                st_json = st_dir / "task.json"
                if not st_json.exists():
                    incidents.append({
                        "message": f"task {task_key}/subtasks/{st_dir.name}: task.json missing",
                        "field": "task.json",
                        "suggestion": f"create {st_json.relative_to(root)}",
                    })
                    continue
                try:
                    st_data = json.loads(st_json.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    incidents.append({
                        "message": f"task {task_key}/subtasks/{st_dir.name}: invalid JSON: {exc}",
                        "field": "task.json",
                        "suggestion": f"fix JSON syntax in {st_json.relative_to(root)}",
                    })
                    continue
                st_errors = validate_task_json(st_data, f"{task_key}-{st_dir.name}", root)
                st_md = st_dir / "task.md"
                if st_md.exists():
                    st_errors.append(
                        "task.md exists; manifest requires task.json as the only canonical input"
                    )
                for serr in st_errors:
                    incidents.append({
                        "message": f"task {task_key}/subtasks/{st_dir.name}: {serr}",
                        "field": "task.json",
                        "suggestion": f"fix {st_json.relative_to(root)}",
                    })

    return incidents


def _scan_task_conf(root: Path) -> list[str]:
    """Validate task-conf hierarchy: types, flows, prompts."""
    errors: list[str] = []
    types, terrors = load_task_conf_types(root)
    for te in terrors:
        errors.append(te)
    for type_id, conf in types.items():
        allowed = conf.get("allowed_flows", [])
        flows = conf.get("flows", {})
        for fid in allowed:
            if fid not in flows:
                errors.append(
                    f"task-conf type {type_id}: allowed_flow {fid!r} has no flow config at "
                    f"types/{type_id}/flows/{fid}/config.yaml"
                )
        prompt_path = root / "doc/config/task-conf/types" / type_id / "prompt.md"
        if not prompt_path.exists():
            errors.append(
                f"task-conf type {type_id}: missing prompt.md at {prompt_path.relative_to(root)}"
            )
        for fid in flows:
            flow_prompt = (
                root / "doc/config/task-conf/types" / type_id / "flows" / fid / "prompt.md"
            )
            if not flow_prompt.exists():
                errors.append(
                    f"task-conf type {type_id} flow {fid}: missing prompt.md at {flow_prompt.relative_to(root)}"
                )
    return errors


# ============================================================================
# Docs commands
# ============================================================================

@register
class DocsPathsCommand(Command):
    """Validate doc/ against declared paths in paths.yaml."""

    name = "docs"

    def setup_parser(self, subparser: argparse.ArgumentParser) -> None:
        sub = subparser.add_subparsers(dest="docs_action", required=True)

        paths_parser = sub.add_parser(
            "paths", help="validate doc/ against declared paths in paths.yaml"
        )
        paths_parser.add_argument(
            "--check", action="store_true", required=True,
            help="check declared paths vs actual files",
        )

        related_parser = sub.add_parser(
            "related", help="show related document graph"
        )
        related_parser.add_argument("id", help="document ID (e.g. SYS-simple-factory)")
        related_parser.add_argument(
            "--depth", type=int, default=2, help="max traversal depth (default 2)",
        )

    def execute(self, args: argparse.Namespace, root: Path, store: ArchitectureStore) -> int:
        if args.docs_action == "paths":
            errors = validate_paths(root)
            if errors:
                errs = [CliError(code="PATH", message=e, exit_code=1,
                                 suggestion="add to doc/config/paths.yaml allowed_paths or remove the file")
                        for e in errors]
                envelope = multi_error_envelope(errs)
                print_envelope(envelope, json_mode=False, stream=sys.stderr)
                return 1
            print("All doc/ paths are declared and valid")
            return 0

        if args.docs_action == "related":
            docs, errors = store.load_documents()
            if errors:
                errs = [CliError(code="DOC-LOAD", message=e, exit_code=1) for e in errors]
                envelope = multi_error_envelope(errs)
                print_envelope(envelope, json_mode=False, stream=sys.stderr)
                return 1
            id_by_doc = {d.metadata.get("id"): d for d in docs
                         if isinstance(d.metadata.get("id"), str)}
            if args.id not in id_by_doc:
                return self._fail(
                    "NOT-FOUND", f"document id {args.id!r} not found",
                    field="id", exit_code=EXIT_NOT_FOUND,
                    suggestion="use `arch list` to see available document IDs",
                    args=args,
                )
            visited: dict[str, int] = {args.id: 0}
            queue: list[tuple[str, int]] = [(args.id, 0)]
            max_depth = args.depth
            while queue:
                current_id, depth = queue.pop(0)
                if depth >= max_depth:
                    continue
                current_doc = id_by_doc.get(current_id)
                if not current_doc:
                    continue
                related = current_doc.metadata.get("related", [])
                if not isinstance(related, list):
                    continue
                for ref in related:
                    if not isinstance(ref, str):
                        continue
                    if ref not in visited:
                        visited[ref] = depth + 1
                        queue.append((ref, depth + 1))
            result = {
                "root": args.id,
                "max_depth": max_depth,
                "documents": [
                    {"id": doc_id, "depth": depth}
                    for doc_id, depth in sorted(
                        visited.items(), key=lambda x: (x[1], x[0])
                    )
                ],
            }
            print_envelope(ok_envelope(data=result), json_mode=True)
            return 0

        return self._fail("ARGS", f"unknown docs action: {args.docs_action}",
                          exit_code=EXIT_ARGS, args=args)


# ============================================================================
# Task command (lifecycle)
# ============================================================================

@register
class TaskCommand(Command):
    """Task lifecycle operations (init, validate, workspace, status)."""

    name = "task"

    def setup_parser(self, subparser: argparse.ArgumentParser) -> None:
        sub = subparser.add_subparsers(dest="task_action", required=True)

        # init
        p = sub.add_parser("init", help="create task directory and scaffold task.json")
        p.add_argument("task_key", help="task key (e.g. UI-0004, 0427, GH-0001)")

        # validate
        p = sub.add_parser("validate", help="validate task.json structure and consistency")
        p.add_argument("task_key", help="task key (e.g. UI-0004, 0427, GH-0001)")
        p.add_argument("--json", action="store_true", help="JSON envelope output")

        # workspace
        p = sub.add_parser("workspace", help="prepare task workspace (branch, base commit)")
        p.add_argument("task_key", help="task key (e.g. UI-0004, 0427, GH-0001)")

        # status
        p = sub.add_parser("status", help="show task state, stages and verification")
        p.add_argument("task_key", help="task key (e.g. UI-0004, 0427, GH-0001)")
        p.add_argument("--json", action="store_true", help="JSON output")

        # types
        p = sub.add_parser("types", help="list available task types from task-conf")
        p.add_argument("--json", action="store_true", help="JSON output")

        # flows
        p = sub.add_parser("flows", help="list flows for a task type from task-conf")
        p.add_argument("--type", required=True, help="task type (e.g. feature, bugfix)")
        p.add_argument("--json", action="store_true", help="JSON output")

        # type-prompt
        p = sub.add_parser("type-prompt", help="show the start prompt (skill) for a task type")
        p.add_argument("--type", required=True, help="task type")

        # flow-prompt
        p = sub.add_parser("flow-prompt", help="show the start prompt (skill) for a flow")
        p.add_argument("--type", required=True, help="task type")
        p.add_argument("--flow", required=True, help="flow id")

        # decompose
        p = sub.add_parser("decompose", help="create subtasks for a task")
        p.add_argument("task_key", help="task key")
        p.add_argument("--subtask-id", action="append", help="subtask ID (4 digits), repeatable")
        p.add_argument("--subtask-title", action="append", help="subtask title, repeatable")

        # diagnose
        p = sub.add_parser("diagnose", help="Gantt-style diagnosis of task and subtasks")
        p.add_argument("task_key", help="task key")
        p.add_argument("--json", action="store_true", help="JSON output")

        # close
        p = sub.add_parser("close", help="close a task (fails if subtasks not all completed)")
        p.add_argument("task_key", help="task key")
        p.add_argument("--json", action="store_true", help="JSON output")

        # subtask
        st = sub.add_parser("subtask", help="subtask lifecycle operations")
        st_sub = st.add_subparsers(dest="subtask_action", required=True)

        st_init = st_sub.add_parser("init", help="create subtask directory and scaffold task.json")
        st_init.add_argument("parent_task_key", help="parent task key")
        st_init.add_argument("subtask_id", help="subtask ID")

        st_validate = st_sub.add_parser("validate", help="validate subtask task.json")
        st_validate.add_argument("parent_task_key", help="parent task key")
        st_validate.add_argument("subtask_id", help="subtask ID")

        st_status = st_sub.add_parser("status", help="show subtask state")
        st_status.add_argument("parent_task_key", help="parent task key")
        st_status.add_argument("subtask_id", help="subtask ID")

    def execute(self, args: argparse.Namespace, root: Path, store: ArchitectureStore) -> int:
        if args.task_action == "subtask":
            return self._subtask(args, root)

        if args.task_action == "types":
            return self._types(args, root)
        if args.task_action == "flows":
            return self._flows(args, root)
        if args.task_action == "type-prompt":
            return self._type_prompt(args, root)
        if args.task_action == "flow-prompt":
            return self._flow_prompt(args, root)

        # Commands requiring task_key
        try:
            parsed = parse_task_key(args.task_key)
        except ValueError as exc:
            return self._fail(
                "ARGS", str(exc), field="task_key", exit_code=EXIT_ARGS,
                suggestion="use format: 1234 (Jira), UI-1234 (UI), or PREFIX-1234 (other)",
                args=args,
            )

        task_key = args.task_key
        task_number = parsed["task_number"]
        source_type = parsed["source_type"]
        source_prefix = parsed["source_prefix"]

        tdir = task_dir(root, task_key)
        tjson = tdir / "task.json"

        if args.task_action == "init":
            return self._task_init(args, root, tdir, tjson, task_key, task_number, source_type, source_prefix)
        if args.task_action == "validate":
            return self._task_validate(args, root, tdir, tjson, task_key)
        if args.task_action == "workspace":
            return self._task_workspace(args, root, tdir, tjson, task_key, task_number, source_type)
        if args.task_action == "status":
            return self._task_status(args, root, tdir, tjson, task_key, task_number, source_type, source_prefix)
        if args.task_action == "decompose":
            return self._task_decompose(args, root, tdir, tjson, task_key, task_number, source_type)
        if args.task_action == "diagnose":
            return self._task_diagnose(args, root, tdir, tjson, task_key, task_number, source_type)
        if args.task_action == "close":
            return self._task_close(args, root, tdir, tjson, task_key)

        return self._fail("ARGS", f"unknown task action: {args.task_action}",
                          exit_code=EXIT_ARGS, args=args)

    # ----- subtask -----

    def _subtask(self, args: argparse.Namespace, root: Path) -> int:
        parent_task_key = args.parent_task_key
        subtask_id = args.subtask_id
        if not TASK_NUMBER_RE.fullmatch(subtask_id):
            return self._fail(
                "ARGS", f"subtask_id must be exactly four decimal digits, got {subtask_id!r}",
                field="subtask_id", exit_code=EXIT_ARGS,
            )

        parent_tdir = task_dir(root, parent_task_key)
        if not parent_tdir.is_dir():
            return self._fail(
                "NOT-FOUND", f"parent task directory not found: {parent_tdir.relative_to(root)}",
                field="parent_task_key",
                suggestion=f"create parent task first: arch task init {parent_task_key}",
                exit_code=EXIT_NOT_FOUND,
            )

        stdir = subtask_dir(root, parent_task_key, subtask_id)
        stjson = stdir / "task.json"

        if args.subtask_action == "init":
            if stdir.exists():
                return self._fail(
                    "CONFLICT", f"subtask directory already exists: {stdir.relative_to(root)}",
                    field="subtask_id", exit_code=EXIT_CONFLICT,
                    suggestion=f"use a different --subtask-id or remove {stdir.relative_to(root)}",
                )
            stdir.mkdir(parents=True, exist_ok=True)
            (stdir / "stage1").mkdir(parents=True, exist_ok=True)
            stjson.write_text(
                scaffold_subtask_json(parent_task_key, subtask_id), encoding="utf-8"
            )
            print_envelope(
                ok_envelope(data={
                    "ok": True,
                    "parent_task_key": parent_task_key,
                    "subtask_id": subtask_id,
                    "subtask_key": f"{parent_task_key}-{subtask_id}",
                    "directory": str(stdir.relative_to(root)),
                    "task_json": str(stjson.relative_to(root)),
                    "stage_dir": str((stdir / "stage1").relative_to(root)),
                    "note": "subtasks are always manual; no external source binding",
                }),
                json_mode=False,
            )
            return 0

        if args.subtask_action == "validate":
            if not stjson.exists():
                return self._fail(
                    "NOT-FOUND", f"subtask task.json not found: {stjson.relative_to(root)}",
                    field="subtask_id", exit_code=EXIT_NOT_FOUND,
                    suggestion=f"create it: arch task subtask init {parent_task_key} {subtask_id}",
                )
            try:
                data = json.loads(stjson.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                return self._fail(
                    "INVALID", f"subtask task.json invalid JSON: {exc}",
                    field="task.json", exit_code=EXIT_ERROR,
                    suggestion=f"fix JSON syntax in {stjson.relative_to(root)}",
                )
            errors = validate_task_json(data, f"{parent_task_key}-{subtask_id}", root)
            st_md = stdir / "task.md"
            if st_md.exists():
                errors.append(
                    "task.md exists; manifest requires task.json as the only canonical input"
                )
            if errors:
                errs = [CliError(code="VALIDATION", message=e, field="task.json",
                                 exit_code=EXIT_ERROR,
                                 suggestion=f"fix {stjson.relative_to(root)}")
                        for e in errors]
                envelope = multi_error_envelope(errs)
                print_envelope(envelope, json_mode=False, stream=sys.stderr)
                return 1
            print_envelope(
                ok_envelope(data={"ok": True,
                                "message": f"subtask {parent_task_key}-{subtask_id} is valid"}),
                json_mode=False,
            )
            return 0

        if args.subtask_action == "status":
            if not stjson.exists():
                return self._fail(
                    "NOT-FOUND", f"subtask task.json not found: {stjson.relative_to(root)}",
                    field="subtask_id", exit_code=EXIT_NOT_FOUND,
                )
            try:
                data = json.loads(stjson.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                return self._fail(
                    "INVALID", f"subtask task.json invalid JSON: {exc}",
                    field="task.json", exit_code=EXIT_ERROR,
                )
            print_envelope(
                ok_envelope(data={
                    "parent_task_key": parent_task_key,
                    "subtask_id": subtask_id,
                    "subtask_key": f"{parent_task_key}-{subtask_id}",
                    "directory": str(stdir.relative_to(root)),
                    "task_json": str(stjson.relative_to(root)),
                    "stages": list_stages(stdir),
                    "sub_subtasks": list_sub_subtasks(stdir),
                    "phase": data.get("phase", "unset"),
                    "task_type": data.get("task_type", "unset"),
                }),
                json_mode=False,
            )
            return 0

        return self._fail("ARGS", f"unknown subtask action: {args.subtask_action}",
                          exit_code=EXIT_ARGS)

    # ----- task types -----

    def _types(self, args: argparse.Namespace, root: Path) -> int:
        types, errors = load_task_conf_types(root)
        if errors:
            errs = [CliError(code="CONFIG", message=e, exit_code=1) for e in errors]
            envelope = multi_error_envelope(errs)
            print_envelope(envelope, json_mode=False, stream=sys.stderr)
            return 1

        items = []
        for tid, conf in sorted(types.items()):
            items.append({
                "id": tid,
                "title": conf.get("title"),
                "description": conf.get("description"),
                "complexity_default": conf.get("complexity_default"),
                "default_flow": conf.get("default_flow"),
                "allowed_flows": conf.get("allowed_flows", []),
                "subtask_policy": conf.get("subtask_policy"),
                "close_policy": conf.get("close_policy"),
                "flow_count": len(conf.get("flows", {})),
            })

        if getattr(args, "json", False):
            print_envelope(ok_envelope(data=items), json_mode=True)
        else:
            for item in items:
                print(
                    f"{item['id']}\t{item.get('title') or '-'}\t"
                    f"default_flow={item.get('default_flow') or '-'}\t"
                    f"subtasks={item.get('subtask_policy') or '-'}\t"
                    f"close={item.get('close_policy') or '-'}\t"
                    f"flows={item.get('flow_count')}"
                )
        return 0

    def _flows(self, args: argparse.Namespace, root: Path) -> int:
        type_id = args.type
        types, errors = load_task_conf_types(root)
        if errors:
            errs = [CliError(code="CONFIG", message=e, exit_code=1) for e in errors]
            envelope = multi_error_envelope(errs)
            print_envelope(envelope, json_mode=False, stream=sys.stderr)
            return 1
        if type_id not in types:
            return self._fail(
                "NOT-FOUND", f"task type {type_id!r} not found in task-conf",
                field="type", exit_code=EXIT_NOT_FOUND,
                suggestion=f"available types: {', '.join(sorted(types))}",
            )
        flows, flow_errors = load_task_conf_flows_for_type(root, type_id)
        if flow_errors:
            errs = [CliError(code="CONFIG", message=e, exit_code=1) for e in flow_errors]
            envelope = multi_error_envelope(errs)
            print_envelope(envelope, json_mode=False, stream=sys.stderr)
            return 1

        allowed = types[type_id].get("allowed_flows", [])
        items = []
        for fid in allowed:
            conf = flows.get(fid, {})
            items.append({
                "id": fid,
                "title": conf.get("title"),
                "description": conf.get("description"),
                "type": conf.get("type"),
            })

        if getattr(args, "json", False):
            print_envelope(
                ok_envelope(data={"type": type_id, "flows": items}), json_mode=True
            )
        else:
            print(f"Flows for task type {type_id}:")
            for item in items:
                print(f"  {item['id']}\t{item.get('title') or '-'}\t({item.get('type') or '-'})")
        return 0

    def _type_prompt(self, args: argparse.Namespace, root: Path) -> int:
        type_id = args.type
        types, errors = load_task_conf_types(root)
        if errors:
            errs = [CliError(code="CONFIG", message=e, exit_code=1) for e in errors]
            envelope = multi_error_envelope(errs)
            print_envelope(envelope, json_mode=False, stream=sys.stderr)
            return 1
        if type_id not in types:
            return self._fail(
                "NOT-FOUND", f"task type {type_id!r} not found in task-conf",
                field="type", exit_code=EXIT_NOT_FOUND,
                suggestion=f"available types: {', '.join(sorted(types))}",
            )
        prompt, prompt_errors = load_task_conf_prompt(root, type_id)
        if prompt_errors:
            errs = [CliError(code="NOT-FOUND", message=e, exit_code=EXIT_NOT_FOUND)
                    for e in prompt_errors]
            envelope = multi_error_envelope(errs)
            print_envelope(envelope, json_mode=False, stream=sys.stderr)
            return EXIT_NOT_FOUND
        print(prompt, end="" if prompt.endswith("\n") else "\n")
        return 0

    def _flow_prompt(self, args: argparse.Namespace, root: Path) -> int:
        type_id = args.type
        flow_id = args.flow
        types, errors = load_task_conf_types(root)
        if errors:
            errs = [CliError(code="CONFIG", message=e, exit_code=1) for e in errors]
            envelope = multi_error_envelope(errs)
            print_envelope(envelope, json_mode=False, stream=sys.stderr)
            return 1
        if type_id not in types:
            return self._fail(
                "NOT-FOUND", f"task type {type_id!r} not found in task-conf",
                field="type", exit_code=EXIT_NOT_FOUND,
                suggestion=f"available types: {', '.join(sorted(types))}",
            )
        flows, flow_errors = load_task_conf_flows_for_type(root, type_id)
        if flow_errors:
            errs = [CliError(code="CONFIG", message=e, exit_code=1) for e in flow_errors]
            envelope = multi_error_envelope(errs)
            print_envelope(envelope, json_mode=False, stream=sys.stderr)
            return 1
        if flow_id not in flows:
            return self._fail(
                "NOT-FOUND", f"flow {flow_id!r} not found for type {type_id!r}",
                field="flow", exit_code=EXIT_NOT_FOUND,
                suggestion=f"available flows: {', '.join(sorted(flows))}",
            )
        prompt, prompt_errors = load_task_conf_flow_prompt(root, type_id, flow_id)
        if prompt_errors:
            errs = [CliError(code="NOT-FOUND", message=e, exit_code=EXIT_NOT_FOUND)
                    for e in prompt_errors]
            envelope = multi_error_envelope(errs)
            print_envelope(envelope, json_mode=False, stream=sys.stderr)
            return EXIT_NOT_FOUND
        print(prompt, end="" if prompt.endswith("\n") else "\n")
        return 0

    # ----- task init -----

    def _task_init(self, args, root, tdir, tjson, task_key, task_number, source_type, source_prefix) -> int:
        if tdir.exists():
            return self._fail(
                "CONFLICT", f"task directory already exists: {tdir.relative_to(root)}",
                field="task_key", exit_code=EXIT_CONFLICT,
                suggestion=f"use a different task key or remove {tdir.relative_to(root)}",
            )
        tdir.mkdir(parents=True, exist_ok=True)
        (tdir / "stage1").mkdir(parents=True, exist_ok=True)
        tjson.write_text(
            scaffold_task_json(task_key, task_number, source_type, source_prefix),
            encoding="utf-8",
        )
        print_envelope(
            ok_envelope(data={
                "ok": True,
                "task_key": task_key,
                "task_number": task_number,
                "source_type": source_type,
                "source_prefix": source_prefix,
                "directory": str(tdir.relative_to(root)),
                "task_json": str(tjson.relative_to(root)),
                "stage_dir": str((tdir / "stage1").relative_to(root)),
            }),
            json_mode=False,
        )
        return 0

    # ----- task validate -----

    def _task_validate(self, args, root, tdir, tjson, task_key) -> int:
        if not tjson.exists():
            return self._fail(
                "NOT-FOUND", f"task.json not found: {tjson.relative_to(root)}",
                field="task_key", exit_code=EXIT_NOT_FOUND,
                suggestion=f"create it: arch task init {task_key}",
            )
        try:
            data = json.loads(tjson.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return self._fail(
                "INVALID", f"task.json invalid JSON: {exc}",
                field="task.json", exit_code=EXIT_ERROR,
                suggestion=f"fix JSON syntax in {tjson.relative_to(root)}",
            )
        errors = validate_task_json(data, task_key, root)
        task_md = tdir / "task.md"
        if task_md.exists():
            errors.append(
                "task.md exists; manifest requires task.json as the only canonical input"
            )
        if errors:
            errs = [CliError(code="VALIDATION", message=e, field="task.json",
                             exit_code=EXIT_ERROR,
                             suggestion=f"fix {tjson.relative_to(root)}")
                    for e in errors]
            envelope = multi_error_envelope(errs)
            print_envelope(envelope, json_mode=getattr(args, "json", False), stream=sys.stderr)
            return 1
        if getattr(args, "json", False):
            print_envelope(
                ok_envelope(data={"ok": True, "message": f"task {task_key} is valid"}),
                json_mode=True,
            )
        else:
            print(f"task {task_key} is valid")
        return 0

    # ----- task workspace -----

    def _task_workspace(self, args, root, tdir, tjson, task_key, task_number, source_type) -> int:
        if not tjson.exists():
            return self._fail(
                "NOT-FOUND", f"task.json not found: {tjson.relative_to(root)}",
                field="task_key", exit_code=EXIT_NOT_FOUND,
                suggestion=f"create it: arch task init {task_key}",
            )
        try:
            data = json.loads(tjson.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return self._fail(
                "INVALID", f"task.json invalid JSON: {exc}",
                field="task.json", exit_code=EXIT_ERROR,
                suggestion=f"fix JSON syntax in {tjson.relative_to(root)}",
            )
        errors = validate_task_json(data, task_key, root)
        if errors:
            errs = [CliError(code="VALIDATION", message=e, field="task.json",
                             exit_code=EXIT_ERROR,
                             suggestion=f"fix {tjson.relative_to(root)}")
                    for e in errors]
            envelope = multi_error_envelope(errs)
            print_envelope(envelope, json_mode=False, stream=sys.stderr)
            return 1
        release = data.get("target_release", "unset")
        print_envelope(
            ok_envelope(data={
                "ok": True,
                "task_key": task_key,
                "task_number": task_number,
                "directory": str(tdir.relative_to(root)),
                "task_json": str(tjson.relative_to(root)),
                "target_release": release,
                "branch_hint": (
                    f"futures/{task_number}" if source_type == "jira" else f"bugfix/{task_key}"
                ),
                "note": "workspace preparation is deterministic; actual git checkout requires configured repository",
            }),
            json_mode=False,
        )
        return 0

    # ----- task status -----

    def _task_status(self, args, root, tdir, tjson, task_key, task_number, source_type, source_prefix) -> int:
        if not tjson.exists():
            return self._fail(
                "NOT-FOUND", f"task.json not found: {tjson.relative_to(root)}",
                field="task_key", exit_code=EXIT_NOT_FOUND,
                suggestion=f"create it: arch task init {task_key}",
            )
        try:
            data = json.loads(tjson.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return self._fail(
                "INVALID", f"task.json invalid JSON: {exc}",
                field="task.json", exit_code=EXIT_ERROR,
                suggestion=f"fix JSON syntax in {tjson.relative_to(root)}",
            )
        stages = list_stages(tdir)
        verification_files = []
        for stage in stages:
            vfile = tdir / stage / "verification.json"
            if vfile.exists():
                verification_files.append(str(vfile.relative_to(root)))
        result = {
            "task_key": task_key,
            "task_number": task_number,
            "source_type": source_type,
            "source_prefix": source_prefix,
            "directory": str(tdir.relative_to(root)),
            "task_json": str(tjson.relative_to(root)),
            "stages": stages,
            "verification_files": verification_files,
            "has_task_md": (tdir / "task.md").exists(),
            "target_release": data.get("target_release", "unset"),
            "task_type": data.get("task_type", "unset"),
            "flow": data.get("flow", "unset"),
            "complexity": data.get("complexity", "unset"),
            "phase": data.get("phase", "unset"),
        }
        if getattr(args, "json", False):
            print_envelope(ok_envelope(data=result), json_mode=True)
        else:
            print_envelope(ok_envelope(data=result), json_mode=False)
        return 0

    # ----- task decompose -----

    def _task_decompose(self, args, root, tdir, tjson, task_key, task_number, source_type) -> int:
        if not tjson.exists():
            return self._fail(
                "NOT-FOUND", f"task.json not found: {tjson.relative_to(root)}",
                field="task_key", exit_code=EXIT_NOT_FOUND,
                suggestion=f"create it: arch task init {task_key}",
            )
        try:
            data = json.loads(tjson.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return self._fail(
                "INVALID", f"task.json invalid JSON: {exc}",
                field="task.json", exit_code=EXIT_ERROR,
                suggestion=f"fix JSON syntax in {tjson.relative_to(root)}",
            )
        subtask_ids = args.subtask_id or []
        subtask_titles = args.subtask_title or []
        if len(subtask_ids) != len(subtask_titles):
            return self._fail(
                "ARGS", "--subtask-id and --subtask-title must be provided in equal numbers",
                field="subtask", exit_code=EXIT_ARGS,
                suggestion="provide the same number of --subtask-id and --subtask-title flags",
            )

        created = []
        for st_id, st_title in zip(subtask_ids, subtask_titles):
            stdir = subtask_dir(root, task_key, st_id)
            if stdir.exists():
                return self._fail(
                    "CONFLICT", f"subtask directory already exists: {stdir.relative_to(root)}",
                    field="subtask_id", exit_code=EXIT_CONFLICT,
                    suggestion=f"use a different --subtask-id or remove {stdir.relative_to(root)}",
                )
            stdir.mkdir(parents=True, exist_ok=True)
            (stdir / "stage1").mkdir(parents=True, exist_ok=True)
            stjson_path = stdir / "task.json"
            stjson_path.write_text(
                scaffold_subtask_json(task_key, st_id, st_title),
                encoding="utf-8",
            )
            created.append({
                "subtask_id": st_id,
                "title": st_title,
                "directory": str(stdir.relative_to(root)),
                "task_json": str(stjson_path.relative_to(root)),
            })

        existing_subtasks = data.get("subtasks", [])
        if not isinstance(existing_subtasks, list):
            existing_subtasks = []
        for st_id, st_title in zip(subtask_ids, subtask_titles):
            existing_subtasks.append(
                {"id": st_id, "title": st_title, "status": "open",
                 "path": f"subtasks/{st_id}/task.json"}
            )
        data["subtasks"] = existing_subtasks
        tjson.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        print_envelope(
            ok_envelope(data={
                "ok": True,
                "task_key": task_key,
                "subtasks_created": created,
            }),
            json_mode=False,
        )
        return 0

    # ----- task diagnose -----

    def _task_diagnose(self, args, root, tdir, tjson, task_key, task_number, source_type) -> int:
        if not tjson.exists():
            return self._fail(
                "NOT-FOUND", f"task.json not found: {tjson.relative_to(root)}",
                field="task_key", exit_code=EXIT_NOT_FOUND,
                suggestion=f"create it: arch task init {task_key}",
            )
        try:
            data = json.loads(tjson.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return self._fail(
                "INVALID", f"task.json invalid JSON: {exc}",
                field="task.json", exit_code=EXIT_ERROR,
                suggestion=f"fix JSON syntax in {tjson.relative_to(root)}",
            )
        all_closed, close_errors = check_subtasks_closed(root, task_key)
        stages = list_stages(tdir)
        subtasks_info = []
        subtasks_dir = tdir / "subtasks"
        if subtasks_dir.is_dir():
            for st_dir in sorted(subtasks_dir.iterdir()):
                if not st_dir.is_dir():
                    continue
                st_json = st_dir / "task.json"
                if st_json.exists():
                    try:
                        st_data = json.loads(st_json.read_text(encoding="utf-8"))
                        subtasks_info.append({
                            "id": st_data.get("task_key", st_dir.name),
                            "title": st_data.get("title", ""),
                            "phase": st_data.get("phase", "unset"),
                            "task_type": st_data.get("task_type", "unset"),
                            "flow": st_data.get("flow", "unset"),
                        })
                    except json.JSONDecodeError:
                        subtasks_info.append({
                            "id": st_dir.name, "title": "",
                            "phase": "invalid", "error": "invalid JSON",
                        })
        closed_count = sum(1 for s in subtasks_info if s.get("phase") == "completed")
        result = {
            "task_key": task_key,
            "task_number": task_number,
            "source_type": source_type,
            "task_type": data.get("task_type"),
            "flow": data.get("flow"),
            "complexity": data.get("complexity"),
            "phase": data.get("phase"),
            "all_subtasks_closed": all_closed,
            "can_close": all_closed,
            "close_blockers": close_errors,
            "stages": stages,
            "subtasks": subtasks_info,
            "subtask_count": len(subtasks_info),
            "subtask_closed_count": closed_count,
        }
        if getattr(args, "json", False):
            print_envelope(ok_envelope(data=result), json_mode=True)
        else:
            print(f"Diagnosis for task {task_key}:")
            print(f"  type: {data.get('task_type')}  flow: {data.get('flow')}  complexity: {data.get('complexity')}")
            print(f"  phase: {data.get('phase')}")
            print(f"  subtasks: {closed_count}/{len(subtasks_info)} closed")
            print(f"  can_close: {all_closed}")
            if close_errors:
                print("  blockers:")
                for e in close_errors:
                    print(f"    - {e}")
            for s in subtasks_info:
                print(f"    [{s.get('phase')} ] {s.get('id')} — {s.get('title')}")
        return 0

    # ----- task close -----

    def _task_close(self, args, root, tdir, tjson, task_key) -> int:
        all_closed, close_errors = check_subtasks_closed(root, task_key)
        if not all_closed:
            errs = [CliError(code="BLOCKER", message=e, field="subtasks",
                             exit_code=EXIT_ERROR,
                             suggestion="complete all subtasks before closing")
                    for e in close_errors]
            print(f"ERROR: cannot close task {task_key}: subtasks not all completed", file=sys.stderr)
            for e in close_errors:
                print(f"  - {e}", file=sys.stderr)
            return 1
        if not tjson.exists():
            return self._fail(
                "NOT-FOUND", f"task.json not found: {tjson.relative_to(root)}",
                field="task_key", exit_code=EXIT_NOT_FOUND,
                suggestion=f"create it: arch task init {task_key}",
            )
        try:
            data = json.loads(tjson.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return self._fail(
                "INVALID", f"task.json invalid JSON: {exc}",
                field="task.json", exit_code=EXIT_ERROR,
                suggestion=f"fix JSON syntax in {tjson.relative_to(root)}",
            )
        data["phase"] = "completed"
        tjson.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if getattr(args, "json", False):
            print_envelope(
                ok_envelope(data={"ok": True, "task_key": task_key, "phase": "completed"}),
                json_mode=True,
            )
        else:
            print(f"Task {task_key} closed (phase=completed). All subtasks verified completed.")
        return 0