"""Built-in command implementations for the arch CLI.

Each command is a separate class implementing the Command interface.
This follows SRP (one responsibility per class) and LSP (all commands
are substitutable via the Command base class).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path, PurePosixPath

from arch.cli.commands.base import Command
from arch.cli.commands.registry import register
from arch.cli.errors import (
    CliError,
    EXIT_ARGS,
    EXIT_ERROR,
    EXIT_NOT_FOUND,
    multi_error_envelope,
    ok_envelope,
)
from arch.cli.output import print_envelope

from arch.store import ArchitectureStore
from arch.validation import (
    flow_prompt_steps,
    load_task_conf_step_prompt,
    validate_task_json,
    validate_paths,
    load_task_conf_types,
)
from arch.body_validation import validate_document_body
from arch.flows import load_selection, validate_flow_definition
from arch.doc_ops import (
    DEFAULT_CONTEXT_BYTES,
    DEFAULT_READ_BYTES,
    DocOpsError,
    check_links,
    context,
    impact,
    read_section,
    search,
    table_of_contents,
)
from arch.project_config import ProjectConfig
from arch.task_ops import pending_write
from arch.task_record import record_errors


# ============================================================================
# List command
# ============================================================================

@register
class ListCommand(Command):
    """List docs by exact metadata filters."""

    name = "list"

    def setup_parser(self, subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--id", dest="doc_ids", action="append", help="exact document ID (repeatable)")
        subparser.add_argument("--type", dest="doc_type")
        subparser.add_argument("--domain")
        subparser.add_argument("--status")
        subparser.add_argument("--json", action="store_true", help="JSON envelope output")

    def execute(self, args: argparse.Namespace, project_config: ProjectConfig, store: ArchitectureStore) -> int:
        docs, errors = store.load_documents()
        if errors:
            errs = [CliError(code="DOC-LOAD", message=e, exit_code=1) for e in errors]
            envelope = multi_error_envelope(errs)
            print_envelope(envelope, json_mode=getattr(args, "json", False), stream=sys.stderr)
            return 1

        doc_ids = set(args.doc_ids or ())
        items = []
        for doc in docs:
            md = doc.metadata
            if doc_ids and md.get("id") not in doc_ids:
                continue
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

    def execute(self, args: argparse.Namespace, project_config: ProjectConfig, store: ArchitectureStore) -> int:
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

    def execute(self, args: argparse.Namespace, project_config: ProjectConfig, store: ArchitectureStore) -> int:
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
        subparser.add_argument("--brief", action="store_true", help="one-line success; detailed errors on stderr")

    def execute(self, args: argparse.Namespace, project_config: ProjectConfig, store: ArchitectureStore) -> int:
        if args.path:
            target = project_config.root / args.path
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

        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        if brief:
            print(f"OK validate: {args.path or 'architecture'}")
        elif not quiet:
            print("Architecture documentation is valid")
        return 0


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
                               help="one-line success; actionable incidents on stderr")
        subparser.add_argument("--verbose", action="store_true",
                               help="full per-incident detail (default for non-JSON)")

    def execute(self, args: argparse.Namespace, project_config: ProjectConfig, store: ArchitectureStore) -> int:
        scope = args.scope
        errors: list[str] = []
        incidents: list[CliError] = []
        scanned_count = 0

        # --- Documents ---
        docs = []
        if scope in ("all", "docs", "index"):
            docs, load_errors = store.load_documents()
            scanned_count = len(docs)
            for le in load_errors:
                incidents.append(CliError(code="DOC-LOAD", message=le, exit_code=1))
                errors.append(le)

        if scope in ("all", "docs"):
            link_errors = store.validate_links(docs)
            for le in link_errors:
                incidents.append(CliError(code="DOC-LINK", message=le, exit_code=1))
                errors.append(le)

            related_errors = store.validate_related(docs)
            for re_ in related_errors:
                incidents.append(CliError(code="DOC-RELATED", message=re_, exit_code=1))
                errors.append(re_)

            schemas_dir = project_config.schemas_root
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
            index_rel = store.index_path.relative_to(project_config.root)
            try:
                actual_index = json.loads(store.index_path.read_text(encoding="utf-8"))
                expected_index = store.make_index(docs)
                if actual_index != expected_index:
                    msg = f"{index_rel}: stale; run `arch index build`"
                    incidents.append(CliError(code="DOC-INDEX", message=msg, exit_code=1,
                                              suggestion="run `arch index build` to regenerate"))
                    errors.append(msg)
            except FileNotFoundError:
                msg = f"{index_rel}: missing; run `arch index build`"
                incidents.append(CliError(code="DOC-INDEX", message=msg, exit_code=1,
                                          suggestion="run `arch index build` to regenerate"))
                errors.append(msg)
            except json.JSONDecodeError as exc:
                msg = f"{index_rel}: invalid JSON: {exc}"
                incidents.append(CliError(code="DOC-INDEX", message=msg, exit_code=1))
                errors.append(msg)

        # --- Paths ---
        if scope in ("all", "paths"):
            path_errors = validate_paths(project_config)
            for pe in path_errors:
                incidents.append(CliError(code="PATH", message=pe, exit_code=1,
                                          suggestion="compare the file with the selected project's allowed_paths"))
                errors.append(pe)

        # --- Tasks ---
        if scope in ("all", "tasks"):
            task_errors = _scan_all_tasks(project_config)
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
            task_conf_errors = _scan_task_conf(project_config)
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
                print(f"OK scan: {scope}")
                return 0
            print(f"ERROR scan: {scope} ({total} incident(s))", file=sys.stderr)

        if quiet or brief:
            if total == 0:
                return 0
            for inc in incidents[:10] if brief else incidents:
                field_part = f" [{inc.field}]" if inc.field else ""
                print(
                    f"[{inc.code}] {inc.message}{field_part} (exit {inc.exit_code})",
                    file=sys.stderr,
                )
                if getattr(args, "fix_hints", False) and inc.suggestion:
                    print(f"      fix: {inc.suggestion}", file=sys.stderr)
            if brief and total > 10:
                print(f"{total - 10} more; rerun without --brief for full details.", file=sys.stderr)
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


def _scan_all_tasks(project_config: ProjectConfig) -> list[dict[str, str]]:
    """Scan every task.json in the configured tasks root and return incidents."""
    incidents: list[dict[str, str]] = []
    tasks_root = project_config.tasks_root
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
                "suggestion": f"create {tjson.relative_to(project_config.root)}",
            })
            continue
        try:
            data = json.loads(tjson.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            incidents.append({
                "message": f"task {task_key}: task.json invalid JSON: {exc}",
                "field": "task.json",
                "suggestion": f"fix JSON syntax in {tjson.relative_to(project_config.root)}",
            })
            continue
        errors = validate_task_json(data, task_key, project_config)
        errors.extend(record_errors(project_config, task_dir_path, data, task_key))
        task_md = task_dir_path / "task.md"
        if task_md.exists():
            errors.append(
                "task.md exists; manifest requires task.json as the only canonical input"
            )
        for err in errors:
            incidents.append({
                "message": f"task {task_key}: {err}",
                "field": "task.json",
                "suggestion": f"fix {tjson.relative_to(project_config.root)}",
            })

        pending = pending_write(task_dir_path)
        if pending is not None:
            incidents.append({
                "message": f"task {task_key}: {pending['message']}",
                "field": "task.json",
                "suggestion": ("inspect the journal and records before retrying"
                               if pending.get("state") == "invalid" else "rerun the recorded command to resume"),
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
                        "suggestion": f"create {st_json.relative_to(project_config.root)}",
                    })
                    continue
                try:
                    st_data = json.loads(st_json.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    incidents.append({
                        "message": f"task {task_key}/subtasks/{st_dir.name}: invalid JSON: {exc}",
                        "field": "task.json",
                        "suggestion": f"fix JSON syntax in {st_json.relative_to(project_config.root)}",
                    })
                    continue
                st_errors = validate_task_json(st_data, f"{task_key}-{st_dir.name}", project_config)
                st_errors.extend(record_errors(
                    project_config, st_dir, st_data, f"{task_key}-{st_dir.name}"
                ))
                st_md = st_dir / "task.md"
                if st_md.exists():
                    st_errors.append(
                        "task.md exists; manifest requires task.json as the only canonical input"
                    )
                for serr in st_errors:
                    incidents.append({
                        "message": f"task {task_key}/subtasks/{st_dir.name}: {serr}",
                        "field": "task.json",
                        "suggestion": f"fix {st_json.relative_to(project_config.root)}",
                    })

    return incidents


def _scan_task_conf(project_config: ProjectConfig) -> list[str]:
    """Validate task-conf hierarchy: types, flows, prompts."""
    errors: list[str] = []
    types, terrors = load_task_conf_types(project_config)
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
        prompt_path = project_config.task_conf_root / "types" / type_id / "prompt.md"
        if not prompt_path.exists():
            errors.append(
                f"task-conf type {type_id}: missing prompt.md at {prompt_path.relative_to(project_config.root)}"
            )
        for fid, flow in flows.items():
            errors.extend(validate_flow_definition(
                flow, config=project_config, type_id=type_id, flow_id=fid,
            ))
            flow_prompt = (
                project_config.task_conf_root / "types" / type_id / "flows" / fid / "prompt.md"
            )
            if not flow_prompt.exists():
                errors.append(
                    f"task-conf type {type_id} flow {fid}: missing prompt.md at {flow_prompt.relative_to(project_config.root)}"
                )
            try:
                step_ids = {step["id"] for step in flow_prompt_steps(flow)}
                for path in sorted((flow_prompt.parent / "stepsprompt").glob("*.md")):
                    if path.stem not in step_ids:
                        errors.append(f"task-conf {type_id}/{fid}: undeclared step prompt {path.name}")
                        continue
                    _, prompt_errors = load_task_conf_step_prompt(project_config, type_id, fid, path.stem)
                    errors.extend(prompt_errors)
            except (ValueError, OSError, RuntimeError) as exc:
                errors.append(f"task-conf {type_id}/{fid}: {exc}")
        selection_file = project_config.task_conf_root / "types" / type_id / "flow-selection.yaml"
        if selection_file.exists():
            _, selection_errors = load_selection(project_config, type_id)
            errors.extend(selection_errors)
        elif len(allowed) > 1:
            errors.append(
                f"task-conf type {type_id}: {len(allowed)} allowed flows require "
                f"types/{type_id}/flow-selection.yaml"
            )
    return errors


# ============================================================================
# Docs commands
# ============================================================================

@register
class DocsPathsCommand(Command):
    """Inspect configured paths and validate their contents."""

    name = "docs"

    def setup_parser(self, subparser: argparse.ArgumentParser) -> None:
        sub = subparser.add_subparsers(dest="docs_action", required=True)

        paths_parser = sub.add_parser(
            "paths", help="show or validate configured documentation paths"
        )
        action = paths_parser.add_mutually_exclusive_group(required=True)
        action.add_argument(
            "--check", action="store_true",
            help="check declared paths vs actual files",
        )
        action.add_argument("--resolved", action="store_true", help="show effective paths as JSON")
        sub.add_parser("tree", help="show the full architecture table of contents as JSON")

        related_parser = sub.add_parser(
            "related", help="show related document graph"
        )
        related_parser.add_argument("id", help="document ID (e.g. SYS-simple-factory)")
        related_parser.add_argument(
            "--depth", type=int, default=2, help="max traversal depth (default 2)",
        )

        read_parser = sub.add_parser(
            "read", help="read one addressable section: DOC-ID#section-id"
        )
        read_parser.add_argument("ref", help="DOC-ID#section-id")
        read_parser.add_argument(
            "--max-bytes", type=int, default=DEFAULT_READ_BYTES,
            help=f"maximum section size in bytes (default {DEFAULT_READ_BYTES})",
        )
        read_parser.add_argument("--json", action="store_true", help="JSON envelope output")

        toc_parser = sub.add_parser("toc", help="list stable and generated section anchors")
        toc_parser.add_argument("id", help="document ID")
        toc_parser.add_argument("--json", action="store_true", help="JSON envelope output")

        search_parser = sub.add_parser("search", help="search sections in product or reference docs")
        search_parser.add_argument("query", help="search terms (all must match)")
        search_parser.add_argument(
            "--scope", choices=("product", "reference", "all"), default="product",
            help="document corpus (default product)",
        )
        search_parser.add_argument("--limit", type=int, default=5, help="maximum hits (default 5)")
        search_parser.add_argument(
            "--include-archived", action="store_true",
            help="include superseded, deprecated and rejected documents",
        )
        search_parser.add_argument("--json", action="store_true", help="JSON envelope output")

        links_parser = sub.add_parser("check-links", help="report broken local links and anchors")
        links_parser.add_argument("--json", action="store_true", help="JSON envelope output")

        context_parser = sub.add_parser(
            "context", help="collect declared document context for a task and case"
        )
        context_parser.add_argument("--task", required=True, help="task or subtask key")
        context_parser.add_argument("--case", dest="case_id", help="planned CASE-N")
        context_parser.add_argument(
            "--max-bytes", type=int, default=DEFAULT_CONTEXT_BYTES,
            help=f"maximum payload size in bytes (default {DEFAULT_CONTEXT_BYTES})",
        )
        context_parser.add_argument(
            "--since-snapshot", type=Path, help="previous context JSON; return only the delta",
        )
        context_parser.add_argument("--json", action="store_true", help="JSON envelope output")

        impact_parser = sub.add_parser(
            "impact", help="report changed sections and declared consumers since a Git revision"
        )
        impact_parser.add_argument("--since", required=True, help="Git revision to compare with")
        impact_parser.add_argument(
            "--scope", choices=("docs", "all"), default="docs",
            help="compare architecture documents only (default) or every changed file",
        )
        impact_parser.add_argument("--json", action="store_true", help="JSON envelope output")

    def execute(self, args: argparse.Namespace, project_config: ProjectConfig, store: ArchitectureStore) -> int:
        if args.docs_action == "tree":
            docs, errors = store.load_documents()
            if errors:
                errs = [CliError(code="DOC-LOAD", message=error, exit_code=1) for error in errors]
                print_envelope(multi_error_envelope(errs), json_mode=True, stream=sys.stderr)
                return 1
            tree = {"directories": {}, "documents": []}
            for doc in sorted(docs, key=lambda item: item.relative_path):
                parent = tree
                for name in PurePosixPath(doc.relative_path).parts[:-1]:
                    parent = parent["directories"].setdefault(name, {"directories": {}, "documents": []})
                parent["documents"].append({
                    "id": doc.metadata["id"], "title": doc.metadata["title"],
                    "type": doc.metadata["type"], "status": doc.metadata["status"],
                    "path": doc.relative_path,
                })
            root = project_config.architecture_root
            data = {"architecture_root": root.relative_to(project_config.root).as_posix(), "tree": tree}
            if (root / "README.md").is_file():
                data["guide"] = "README.md"
            print_envelope(ok_envelope(data), json_mode=True)
            return 0

        if args.docs_action == "paths":
            if args.resolved:
                root = project_config.root

                def display(path: Path) -> str:
                    return path.relative_to(root).as_posix() if path.is_relative_to(root) else path.as_posix()

                data = {
                    "project_root": root.as_posix(),
                    "config": display(project_config.config_path),
                    "doc_root": display(project_config.doc_root),
                    "roots": {key: display(path) for key, path in project_config.roots.items()},
                }
                print_envelope(ok_envelope(data), json_mode=True)
                return 0
            errors = validate_paths(project_config)
            if errors:
                errs = [CliError(code="PATH", message=e, exit_code=1,
                                 suggestion="compare the file location with the selected project's allowed_paths")
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

        if args.docs_action in {"read", "toc", "search", "check-links", "context", "impact"}:
            try:
                if args.docs_action == "read":
                    data = read_section(store, args.ref, args.max_bytes)
                    if args.json:
                        print_envelope(ok_envelope(data), json_mode=True)
                    else:
                        print(data["content"])
                    return 0

                if args.docs_action == "toc":
                    data = table_of_contents(store, args.id)
                    if args.json:
                        print_envelope(ok_envelope(data), json_mode=True)
                    else:
                        print(f"{data['doc_id']}\t{data['path']}\t{data['status']}")
                        for item in data["sections"]:
                            marker = "stable" if item["stable"] else "slug"
                            print(f"{item['line_start']:>5}\t{'#' * item['level']} {item['title']}"
                                  f"\t#{item['anchor']}\t{marker}")
                    return 0

                if args.docs_action == "search":
                    data = search(
                        store, args.query, scope=args.scope, limit=args.limit,
                        include_archived=args.include_archived,
                    )
                    if args.json:
                        print_envelope(ok_envelope(data), json_mode=True)
                    else:
                        print(f"hits: {data['total_matched']} (showing {len(data['hits'])})")
                        for item in data["hits"]:
                            anchor = f"#{item['anchor']}" if item["anchor"] else ""
                            line = f":{item['line']}" if item["line"] else ""
                            print(f"{item['score']:>5}\t{item['id']}{anchor}{line}"
                                  f"\t{item['match']}\t{item['snippet']}")
                    return 0

                if args.docs_action == "check-links":
                    data = check_links(store)
                    if args.json:
                        envelope = ok_envelope(data) if not data["incident_count"] else (
                            multi_error_envelope(
                                [CliError(code=item["code"], message=item["message"], exit_code=1)
                                 for item in data["incidents"]],
                                data=data,
                            )
                        )
                        print_envelope(envelope, json_mode=True)
                    else:
                        for item in data["incidents"]:
                            print(f"[{item['code']}] {item['message']}", file=sys.stderr)
                        if not data["incident_count"]:
                            print(f"OK check-links: {data['scanned_documents']} documents")
                    return 1 if data["incident_count"] else 0

                if args.docs_action == "context":
                    data = context(
                        store, args.task, case_id=args.case_id,
                        max_bytes=args.max_bytes, since_snapshot=args.since_snapshot,
                    )
                    if args.json:
                        print_envelope(ok_envelope(data), json_mode=True)
                    else:
                        print(f"task {data['task_key']} stage {data['stage'] or '-'} "
                              f"complete={data['complete']}")
                        for item in data["items"]:
                            print(f"{item.get('kind')}\t{item.get('ref')}\t"
                                  f"{item.get('state')}\t{item.get('path') or ''}")
                        if data.get("delta"):
                            print(f"delta: {data['delta']}")
                    return 0

                if args.docs_action == "impact":
                    data = impact(store, args.since, scope=args.scope)
                    if args.json:
                        print_envelope(ok_envelope(data), json_mode=True)
                    else:
                        print(f"changed files: {len(data['changed_files'])}")
                        for item in data["affected"]:
                            print(f"{item['kind']}\t{item['id']}\t{item['via']}\t{item['path']}")
                        if data["unverified_coverage"]:
                            print("unverified coverage: " + ", ".join(data["unverified_coverage"]))
                    return 0
            except DocOpsError as exc:
                return self._fail(
                    exc.code, exc.message, field=exc.field, suggestion=exc.suggestion,
                    exit_code=exc.exit_code, data=exc.data, args=args,
                )

        return self._fail("ARGS", f"unknown docs action: {args.docs_action}",
                          exit_code=EXIT_ARGS, args=args)
