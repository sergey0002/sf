"""Task lifecycle command: parser, dispatch and output only.

Lifecycle reads and writes live in :mod:`arch.task_ops`. This module keeps the
existing command names, flags, exit codes and output formats.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from typing import Any

from arch.cli.commands.base import Command
from arch.cli.commands.registry import register
from arch.cli.errors import (
    CliError,
    EXIT_ARGS,
    EXIT_NOT_FOUND,
    multi_error_envelope,
    ok_envelope,
)
from arch.cli.output import print_envelope
from arch.evidence import task_baseline, task_evidence
from arch.identity import parse_task_key
from arch.project_config import ProjectConfig
from arch import task_ops, task_record, task_registry
from arch.task_ops import SUBTASK_KEY_RE
from arch.validation import (
    flow_prompt_steps,
    flow_step_path,
    load_task_conf_flow_prompt,
    load_task_conf_step_prompt,
    load_task_conf_prompt,
    load_task_conf_types,
)
from arch.plan_policy import resolve_plan_policy


@register
class TaskCommand(Command):
    """Task lifecycle operations (init, validate, workspace, status)."""

    name = "task"

    def setup_parser(self, subparser: argparse.ArgumentParser) -> None:
        sub = subparser.add_subparsers(dest="task_action", required=True)

        p = sub.add_parser("init", help="create task directory and scaffold task.json")
        p.add_argument("task_key", help="task key (e.g. UI-0004, 0427, GH-0001)")
        p.add_argument("--title", help="task title stored in the scaffold")

        p = sub.add_parser("new", help="allocate the next UI key, create and register the task")
        p.add_argument("--source", default="ui", help="source for allocation (only ui is automatic)")
        p.add_argument("--title", help="task title stored in the scaffold")
        p.add_argument("--json", action="store_true", default=True, help="JSON envelope output")
        p.set_defaults(json=True)

        p = sub.add_parser("registry", help="inspect or initialize the CLI-owned task registry")
        p.add_argument("--json", action="store_true", default=True, help="JSON envelope output")
        reg = p.add_subparsers(dest="registry_action")
        reg_init = reg.add_parser("init", help="create an empty registry when it is missing")
        reg_init.add_argument("--json", action="store_true", default=True, help="JSON envelope output")
        reg_init.set_defaults(json=True)
        reg_add = reg.add_parser("add", help="register an existing task card by key")
        reg_add.add_argument("task_key", help="existing task key")
        reg_add.add_argument("--title", help="title override; defaults to task.json")
        reg_add.add_argument("--json", action="store_true", default=True, help="JSON envelope output")
        reg_add.set_defaults(json=True)
        reg_check = reg.add_parser("check", help="compare the registry with task directories")
        reg_check.add_argument("--json", action="store_true", help="JSON envelope output")
        reg_sync = reg.add_parser("sync", help="reconcile the registry with task directories")
        reg_sync.add_argument("--prune", action="store_true",
                              help="also remove entries whose task directory is gone")
        reg_sync.add_argument("--json", action="store_true", default=True, help="JSON envelope output")
        reg_sync.set_defaults(json=True)
        p.set_defaults(json=True)

        p = sub.add_parser("validate", help="validate task.json structure and consistency")
        p.add_argument("task_key", help="task key (e.g. UI-0004, 0427, GH-0001)")
        p.add_argument("--json", action="store_true", help="JSON envelope output")

        p = sub.add_parser("workspace", help="show workspace paths, branch hint and a write preflight")
        p.add_argument("task_key", help="task key (e.g. UI-0004, 0427, GH-0001)")
        p.add_argument("--json", action="store_true", help="JSON envelope output")

        p = sub.add_parser("status", help="show task state, stages and verification")
        p.add_argument("task_key", help="task key (e.g. UI-0004, 0427, GH-0001)")
        p.add_argument("--json", action="store_true", help="JSON output")

        p = sub.add_parser("plan-policy", help="show the resolved read-only plan policy")
        p.add_argument("--type", required=True, help="task type ID")
        p.add_argument("--json", action="store_true", help="JSON output")

        p = sub.add_parser("types", help="list available task types from task-conf")
        p.add_argument("--json", action="store_true", help="JSON output")

        p = sub.add_parser("flows", help="list flows for a task type from task-conf")
        p.add_argument("--type", required=True, help="task type (e.g. feature, bugfix)")
        p.add_argument("--json", action="store_true", help="JSON output")

        p = sub.add_parser("type-prompt", help="show the start prompt (skill) for a task type")
        p.add_argument("--type", required=True, help="task type")

        p = sub.add_parser("flow-prompt", help="show the start prompt (skill) for a flow")
        p.add_argument("--type", required=True, help="task type")
        p.add_argument("--flow", required=True, help="flow id")
        p.add_argument("--step", help="return only the prompt for this declared step ID")

        p = sub.add_parser("flow-steps", help="show the ordered flow steps as JSON without prompt bodies")
        p.add_argument("--type", required=True, help="task type")
        p.add_argument("--flow", required=True, help="flow id")
        p.set_defaults(json=True)

        p = sub.add_parser("select-flow", help="select a flow from the typed decision table")
        p.add_argument("--type", required=True, help="task type")
        p.add_argument("--fact", action="append", default=[], help="typed fact name=value, repeatable")
        p.set_defaults(json=True)

        p = sub.add_parser("decompose", help="create subtasks for a task")
        p.add_argument("task_key", help="task key")
        p.add_argument("--subtask-id", action="append", help="subtask ID (4 digits), repeatable")
        p.add_argument("--subtask-title", action="append", help="subtask title, repeatable")
        p.add_argument("--subtask-depends-on", action="append", default=[],
                       help="sibling dependency ID=DEP[,DEP], repeatable")
        p.add_argument("--subtask-type", action="append", default=[],
                       help="subtask task_type ID=TYPE, repeatable")
        p.add_argument("--subtask-flow", action="append", default=[],
                       help="subtask flow ID=FLOW, repeatable")
        p.add_argument("--subtask-complexity", action="append", default=[],
                       help="subtask complexity ID=LEVEL, repeatable")
        p.add_argument("--subtask-estimate", action="append", default=[],
                       help="subtask estimate in hours ID=HOURS, repeatable")
        p.add_argument("--json", action="store_true", help="JSON envelope output")

        p = sub.add_parser("advance", help="apply one flow event with revision and idempotency checks")
        p.add_argument("task_key", help="task key")
        p.add_argument("--event", required=True, help="flow event id")
        p.add_argument("--expected-revision", required=True, type=int,
                       help="revision the event applies to")
        p.add_argument("--id", dest="event_id", help="idempotency key (default: flow:<task>:<revision>:<event>)")
        p.add_argument("--dry-run", action="store_true", help="preview without writing")
        p.set_defaults(json=True)

        p = sub.add_parser("diagnose", help="show task, subtask and closure diagnostics")
        p.add_argument("task_key", help="task key")
        p.add_argument("--json", action="store_true", help="JSON output")
        p.add_argument("--brief", action="store_true", help="show summary and task references")

        p = sub.add_parser("doctor", help="one read-only summary of closure, evidence and workspace risks")
        p.add_argument("task_key", help="task key")
        p.add_argument("--json", action="store_true", help="JSON output")
        p.add_argument("--brief", action="store_true", help="omit detailed blockers")

        p = sub.add_parser("evidence", help="check snapshot freshness or record a real test result")
        p.add_argument("task_key", help="task key")
        mode = p.add_mutually_exclusive_group(required=True)
        mode.add_argument("--check", action="store_true", help="read-only check of recorded SHA-256 hashes")
        mode.add_argument("--run", nargs=argparse.REMAINDER, help="execute these arguments from the project root")
        p.add_argument("--file", action="append", default=[], help="project-relative snapshot input, repeatable")
        p.add_argument("--case", action="append", default=[], help="planned case ID observed by the run, repeatable")
        p.add_argument("--replace-snapshot", action="store_true", help="clear old results if recording a different snapshot")
        p.set_defaults(json=True)

        p = sub.add_parser("baseline", help="record a pre-change command, exit code and input hashes")
        p.add_argument("task_key", help="task or subtask key")
        p.add_argument("--run", nargs=argparse.REMAINDER, required=True,
                       help="execute these arguments from the project root")
        p.add_argument("--file", action="append", default=[], help="project-relative input, repeatable")
        p.set_defaults(json=True)

        p = sub.add_parser("close", help="close a task (fails if subtasks not all completed)")
        p.add_argument("task_key", help="task key")
        p.add_argument("--json", action="store_true", help="JSON output")
        p.add_argument("--dry-run", action="store_true", help="show what would happen without closing")

        p = sub.add_parser("migrate", help="add versioned record fields, state.json and events.jsonl")
        p.add_argument("task_key", help="task or subtask key")
        p.add_argument("--dry-run", action="store_true", help="preview changes without writing")
        p.set_defaults(json=True)

        p = sub.add_parser("event", help="append a lifecycle event with revision and idempotency checks")
        p.add_argument("task_key", help="task or subtask key")
        p.add_argument("--id", required=True, dest="event_id", help="idempotency key")
        p.add_argument("--type", required=True, dest="event_type",
                       choices=("phase.changed", "result.recorded"), help="event type")
        p.add_argument("--expected-revision", required=True, type=int,
                       help="revision the event applies to")
        p.add_argument("--phase", help="target phase for phase.changed")
        p.add_argument("--summary", help="result text for result.recorded")
        p.add_argument("--dry-run", action="store_true", help="preview without writing")
        p.set_defaults(json=True)

        p = sub.add_parser("replay", help="rebuild state.json from the event journal")
        p.add_argument("task_key", help="task or subtask key")
        p.add_argument("--dry-run", action="store_true", help="compare without writing")
        p.set_defaults(json=True)

        st = sub.add_parser("subtask", help="subtask lifecycle operations")
        st_sub = st.add_subparsers(dest="subtask_action", required=True)

        st_init = st_sub.add_parser("init", help="create subtask directory and scaffold task.json")
        st_init.add_argument("parent_task_key", help="parent task key")
        st_init.add_argument("subtask_id", help="subtask ID")
        st_init.add_argument("--task-type", help="subtask task_type (default: subtask)")
        st_init.add_argument("--flow", help="subtask flow")
        st_init.add_argument("--complexity", help="subtask complexity (default: parent)")
        st_init.add_argument("--estimate-hours", type=float, help="subtask estimate in hours")
        st_init.add_argument("--json", action="store_true", help="JSON envelope output")

        st_validate = st_sub.add_parser("validate", help="validate subtask task.json")
        st_validate.add_argument("parent_task_key", help="parent task key")
        st_validate.add_argument("subtask_id", help="subtask ID")
        st_validate.add_argument("--json", action="store_true", help="JSON envelope output")

        st_status = st_sub.add_parser("status", help="show subtask state")
        st_status.add_argument("parent_task_key", help="parent task key")
        st_status.add_argument("subtask_id", help="subtask ID")
        st_status.add_argument("--json", action="store_true", help="JSON envelope output")

    def execute(
        self, args: argparse.Namespace, project_config: ProjectConfig, store: Any
    ) -> int:
        if args.task_action == "subtask":
            return self._subtask(args, project_config)
        if args.task_action == "new":
            return self._new_task(args, project_config)
        if args.task_action == "registry":
            return self._registry(args, project_config)
        if args.task_action == "plan-policy":
            return self._plan_policy(args, project_config)
        if args.task_action == "types":
            return self._types(args, project_config)
        if args.task_action == "flows":
            return self._flows(args, project_config)
        if args.task_action == "type-prompt":
            return self._type_prompt(args, project_config)
        if args.task_action in ("flow-prompt", "flow-steps"):
            return self._flow_prompt(args, project_config)
        if args.task_action == "evidence":
            return self._evidence(args, project_config)
        if args.task_action == "baseline":
            return self._baseline(args, project_config)
        if args.task_action == "select-flow":
            return self._select_flow(args, project_config)
        if args.task_action in ("migrate", "event", "replay"):
            return self._record(args, project_config)
        if args.task_action == "close" and SUBTASK_KEY_RE.fullmatch(args.task_key):
            return self._close_record(args, project_config)

        try:
            parsed = parse_task_key(args.task_key)
        except ValueError as exc:
            return self._fail(
                "ARGS", str(exc), field="task_key", exit_code=EXIT_ARGS,
                suggestion="use format: 1234 (Jira), UI-1234 (UI), or PREFIX-1234 (other)",
                args=args,
            )

        try:
            return self._run_lifecycle(args, project_config, parsed)
        except task_ops.TaskOpsError as exc:
            json_errors = args.task_action in ("validate", "diagnose", "doctor", "close", "evidence", "advance")
            return self._fail(
                exc.code,
                exc.message,
                field=exc.field,
                suggestion=exc.suggestion,
                exit_code=exc.exit_code,
                args=args if json_errors else None,
            )

    def _new_task(self, args: argparse.Namespace, project_config: ProjectConfig) -> int:
        try:
            with task_registry.registry_lock(project_config):
                registry = task_registry.load_registry(project_config, create=True)
                identity = task_registry.next_task_key(registry, args.source)
                payload = task_ops.init_task(
                    project_config,
                    identity["task_key"],
                    identity["task_number"],
                    identity["source_type"],
                    identity["source_prefix"],
                    title=args.title,
                )
                try:
                    task_registry.register_entry(registry, identity, title=args.title)
                    task_registry.save_registry(project_config, registry)
                except (OSError, task_registry.RegistryError):
                    shutil.rmtree(project_config.root / payload["directory"], ignore_errors=True)
                    raise
        except task_registry.RegistryError as exc:
            return self._fail("REGISTRY", str(exc), field="task-registry.json",
                              exit_code=EXIT_ARGS, args=args)
        except task_ops.TaskOpsError as exc:
            return self._fail(exc.code, exc.message, field=exc.field,
                              suggestion=exc.suggestion, exit_code=exc.exit_code, args=args)
        except OSError as exc:
            return self._fail("WRITE", str(exc), field="task-registry.json",
                              exit_code=1, args=args)
        self._json(ok_envelope(data=payload), args)
        return 0

    def _registry(self, args: argparse.Namespace, project_config: ProjectConfig) -> int:
        path = task_registry.registry_path(project_config)
        try:
            if args.registry_action == "add":
                return self._registry_add(args, project_config)
            if args.registry_action == "check":
                return self._registry_check(args, project_config)
            if args.registry_action == "sync":
                return self._registry_sync(args, project_config)
            if args.registry_action == "init":
                with task_registry.registry_lock(project_config):
                    if not path.exists():
                        task_registry.save_registry(project_config, task_registry.empty_registry())
                    registry = task_registry.load_registry(project_config)
            else:
                registry = task_registry.load_registry(project_config)
        except (OSError, task_registry.RegistryError) as exc:
            return self._fail("REGISTRY", str(exc), field="task-registry.json",
                              exit_code=1, args=args)
        payload = {
            "path": path.relative_to(project_config.root).as_posix(),
            "schema_version": registry["schema_version"],
            "count": len(registry["tasks"]),
            "tasks": registry["tasks"],
        }
        self._json(ok_envelope(data=payload), args)
        return 0

    def _registry_add(self, args: argparse.Namespace, project_config: ProjectConfig) -> int:
        try:
            parsed = parse_task_key(args.task_key)
        except ValueError as exc:
            raise task_registry.RegistryError(str(exc)) from exc
        _, tjson = task_ops.task_paths(project_config, args.task_key)
        if not tjson.is_file():
            raise task_registry.RegistryError(
                f"task card not found: {tjson.relative_to(project_config.root).as_posix()}"
            )
        title = args.title
        if title is None:
            try:
                title = json.loads(tjson.read_text(encoding="utf-8")).get("title")
            except (OSError, ValueError):
                title = None
        with task_registry.registry_lock(project_config):
            registry = task_registry.load_registry(project_config, create=True)
            entry = task_registry.register_entry(
                registry, {"task_key": args.task_key, **parsed}, title=title
            )
            task_registry.save_registry(project_config, registry)
        self._json(ok_envelope(data={"ok": True, "entry": entry}), args)
        return 0

    def _registry_check(self, args: argparse.Namespace, project_config: ProjectConfig) -> int:
        try:
            registry = task_registry.load_registry(project_config, create=True)
            drift = task_registry.registry_drift(project_config, registry)
        except (OSError, task_registry.RegistryError) as exc:
            return self._fail("REGISTRY", str(exc), field="task-registry.json",
                              exit_code=1, args=args)
        if getattr(args, "json", False):
            self._json(ok_envelope(data=drift), args)
            return 0 if drift["ok"] else 1
        if drift["ok"]:
            print(f"task registry matches {drift['cards']} task directories")
            return 0
        for key in drift["missing_in_registry"]:
            print(f"missing in registry: {key}", file=sys.stderr)
        for key in drift["missing_on_disk"]:
            print(f"missing on disk: {key}", file=sys.stderr)
        for row in drift["number_mismatch"]:
            print(
                f"number mismatch: {row['task_key']} registry={row['registry_number']} "
                f"task.json={row['task_json_number']}",
                file=sys.stderr,
            )
        print("run: arch task registry sync", file=sys.stderr)
        return 1

    def _registry_sync(self, args: argparse.Namespace, project_config: ProjectConfig) -> int:
        try:
            with task_registry.registry_lock(project_config):
                registry = task_registry.load_registry(project_config, create=True)
                before = task_registry.registry_drift(project_config, registry)
                if before["number_mismatch"]:
                    raise task_registry.RegistryError(
                        "number mismatch between task.json and registry; fix task.json first"
                    )
                result = task_registry.sync_registry(
                    project_config, registry, prune=args.prune
                )
                if result["added"] or result["removed"]:
                    task_registry.save_registry(project_config, registry)
                after = task_registry.registry_drift(project_config, registry)
        except (OSError, task_registry.RegistryError) as exc:
            return self._fail("REGISTRY", str(exc), field="task-registry.json",
                              exit_code=1, args=args)
        payload = {**result, "ok": after["ok"], "drift": after}
        self._json(ok_envelope(data=payload), args)
        return 0

    def _evidence(self, args: argparse.Namespace, project_config: ProjectConfig) -> int:
        try:
            if args.check and (args.file or args.case or args.replace_snapshot):
                raise ValueError("--check uses recorded files and takes no recording options")
            payload, code = task_evidence(project_config, args.task_key, names=args.file, cases=args.case,
                                          argv=args.run, replace_snapshot=args.replace_snapshot)
        except task_ops.TaskOpsError as exc:
            return self._fail(exc.code, exc.message, field=exc.field, suggestion=exc.suggestion,
                              exit_code=exc.exit_code, args=args)
        except (ValueError, OSError, RuntimeError) as exc:
            return self._fail("EVIDENCE", str(exc), field="verification.json", exit_code=1, args=args)
        self._json(ok_envelope(data=payload), args)
        return code

    def _baseline(self, args: argparse.Namespace, project_config: ProjectConfig) -> int:
        try:
            payload, code = task_baseline(
                project_config, args.task_key, names=args.file, argv=args.run
            )
        except task_ops.TaskOpsError as exc:
            return self._fail(exc.code, exc.message, field=exc.field, suggestion=exc.suggestion,
                              exit_code=exc.exit_code, args=args)
        except (ValueError, OSError, RuntimeError) as exc:
            return self._fail("BASELINE", str(exc), field="baseline.json", exit_code=1, args=args)
        self._json(ok_envelope(data=payload), args)
        return code

    def _close_record(self, args: argparse.Namespace, project_config: ProjectConfig) -> int:
        try:
            payload, blockers = task_ops.close(project_config, args.task_key, args.dry_run)
        except task_ops.TaskOpsError as exc:
            return self._fail(exc.code, exc.message, field=exc.field, suggestion=exc.suggestion,
                              exit_code=exc.exit_code, args=args)
        if args.dry_run:
            return self._json(ok_envelope(data=payload), args)
        if blockers:
            errors = [CliError(code="BLOCKER", message=message, field="task.json",
                               suggestion="run task diagnose for blockers") for message in blockers]
            return self._json(multi_error_envelope(errors), args, stream=sys.stderr)
        return self._json(ok_envelope(data=payload), args)

    def _select_flow(self, args: argparse.Namespace, project_config: ProjectConfig) -> int:
        try:
            payload = task_ops.select_flow(project_config, args.type, args.fact)
        except task_ops.TaskOpsError as exc:
            return self._fail(exc.code, exc.message, field=exc.field,
                              suggestion=exc.suggestion, exit_code=exc.exit_code, args=args)
        return self._json(ok_envelope(data=payload), args)

    def _record(self, args: argparse.Namespace, project_config: ProjectConfig) -> int:
        try:
            if args.task_action == "migrate":
                payload = task_ops.migrate_record(project_config, args.task_key, args.dry_run)
            elif args.task_action == "event":
                payload = task_ops.append_record_event(
                    project_config, args.task_key, event_id=args.event_id,
                    event_type=args.event_type, expected_revision=args.expected_revision,
                    phase=args.phase, summary=args.summary, dry_run=args.dry_run,
                )
            else:
                payload = task_ops.replay_record(project_config, args.task_key, args.dry_run)
        except task_ops.TaskOpsError as exc:
            return self._fail(exc.code, exc.message, field=exc.field,
                              suggestion=exc.suggestion, exit_code=exc.exit_code, args=args)
        except task_record.RecordError as exc:
            return self._fail(exc.code, exc.message, field=exc.field,
                              suggestion=exc.suggestion, exit_code=exc.exit_code, args=args)
        return self._json(ok_envelope(data=payload), args)

    def _run_lifecycle(
        self, args: argparse.Namespace, project_config: ProjectConfig, parsed: dict[str, Any]
    ) -> int:
        task_key = args.task_key
        task_number = parsed["task_number"]
        source_type = parsed["source_type"]
        source_prefix = parsed["source_prefix"]

        if args.task_action == "init":
            tdir = task_ops.task_paths(project_config, task_key)[0]
            try:
                with task_registry.registry_lock(project_config):
                    registry = task_registry.load_registry(project_config, create=True)
                    payload = task_ops.init_task(
                        project_config, task_key, task_number, source_type, source_prefix,
                        title=getattr(args, "title", None),
                    )
                    try:
                        task_registry.register_entry(
                            registry,
                            {"task_key": task_key, **parsed},
                            title=getattr(args, "title", None),
                        )
                        task_registry.save_registry(project_config, registry)
                    except (OSError, task_registry.RegistryError):
                        shutil.rmtree(tdir, ignore_errors=True)
                        raise
            except task_registry.RegistryError as exc:
                return self._fail("REGISTRY", str(exc), field="task-registry.json",
                                  exit_code=EXIT_ARGS, args=args)
            except OSError as exc:
                return self._fail("WRITE", str(exc), field="task-registry.json",
                                  exit_code=1, args=args)
            print_envelope(ok_envelope(data=payload), json_mode=False)
            return 0

        if args.task_action == "validate":
            tdir, _ = task_ops.task_paths(project_config, task_key)
            data = task_ops.load_task(
                project_config, task_key, invalid_message="task.json invalid JSON"
            )
            errors = task_ops.validation_errors(project_config, tdir, data, task_key)
            if errors:
                errs = [
                    CliError(
                        code="VALIDATION",
                        message=error,
                        field="task.json",
                        suggestion=f"fix {tdir.relative_to(project_config.root).as_posix()}/task.json",
                    )
                    for error in errors
                ]
                print_envelope(
                    multi_error_envelope(errs),
                    json_mode=getattr(args, "json", False),
                    stream=sys.stderr,
                )
                return 1
            if getattr(args, "json", False):
                print_envelope(
                    ok_envelope(data={"ok": True, "message": f"task {task_key} is valid"}),
                    json_mode=True,
                )
            else:
                print(f"task {task_key} is valid")
            return 0

        if args.task_action == "workspace":
            payload, errors = task_ops.workspace_info(
                project_config, task_key, task_number, source_type
            )
            if errors:
                errs = [
                    CliError(
                        code="VALIDATION",
                        message=error,
                        field="task.json",
                        suggestion=f"fix {task_key}/task.json",
                    )
                    for error in errors
                ]
                print_envelope(
                    multi_error_envelope(errs),
                    json_mode=getattr(args, "json", False),
                    stream=sys.stderr,
                )
                return 1
            print_envelope(
                ok_envelope(data=payload), json_mode=getattr(args, "json", False)
            )
            return 0

        if args.task_action == "status":
            payload = task_ops.status_info(
                project_config, task_key, task_number, source_type, source_prefix
            )
            print_envelope(
                ok_envelope(data=payload), json_mode=getattr(args, "json", False)
            )
            return 0

        if args.task_action == "decompose":
            payload = task_ops.decompose(
                project_config, task_key, args.subtask_id or [], args.subtask_title or [],
                args.subtask_depends_on, args.subtask_type, args.subtask_flow,
                args.subtask_complexity, args.subtask_estimate,
            )
            print_envelope(
                ok_envelope(data=payload), json_mode=getattr(args, "json", False)
            )
            return 0

        if args.task_action == "advance":
            payload = task_ops.advance(
                project_config, task_key, args.event, args.expected_revision,
                dry_run=args.dry_run, event_id=args.event_id,
            )
            return self._json(ok_envelope(data=payload), args)

        if args.task_action == "diagnose":
            payload = task_ops.diagnose(
                project_config, task_key, task_number, source_type, args.brief
            )
            if args.json:
                return self._json(ok_envelope(data=payload), args)
            print(f"Diagnosis for task {task_key}:")
            print(f"  type: {payload.get('task_type')}  flow: {payload.get('flow')}  complexity: {payload.get('complexity')}")
            print(f"  phase: {payload.get('phase')}")
            print(f"  subtasks: {payload['subtask_closed_count']}/{payload['subtask_count']} closed")
            print(f"  can_close: {payload['can_close']}")
            if "acceptance_plan_ready" in payload:
                print(f"  acceptance_plan_ready: {payload['acceptance_plan_ready']}")
            for blocker in payload["close_blockers"]:
                print(f"    - {blocker}")
            if args.brief:
                if payload["blockers_truncated"]:
                    print(f"    … {payload['blocker_count'] - 3} more; rerun without --brief")
                for key, path in payload["refs"].items():
                    print(f"  {key}: {path}")
            else:
                for subtask in payload.get("subtasks", []):
                    print(f"    [{subtask['phase']}] {subtask['id']} — {subtask['title']}")
            return 0

        if args.task_action == "doctor":
            payload = task_ops.doctor(
                project_config, task_key, task_number, source_type, args.brief
            )
            if args.json:
                return self._json(ok_envelope(data=payload), args)
            print(f"Doctor for task {task_key}:")
            print(f"  phase: {payload.get('phase')}  can_close: {payload.get('can_close')}")
            freshness = payload.get("evidence_freshness")
            if freshness:
                print(f"  evidence: {freshness.get('status')} ({freshness.get('stage')})")
                for path in freshness.get("stale_files", []):
                    print(f"    - stale: {path}")
                if freshness.get("note"):
                    print(f"    note: {freshness['note']}")
            preflight = payload.get("preflight") or {}
            print(f"  workspace: {preflight.get('status')}")
            if preflight.get("recommendation"):
                print(f"    {preflight['recommendation']}")
            if payload.get("incomplete_write"):
                print(f"  incomplete_write: {payload['incomplete_write'].get('state')}")
            if not args.brief:
                for blocker in payload.get("close_blockers", []):
                    print(f"    - {blocker}")
            return 0

        if args.task_action == "close":
            payload, blockers = task_ops.close(project_config, task_key, args.dry_run)
            if args.dry_run:
                if args.json:
                    return self._json(ok_envelope(data=payload), args)
                if blockers:
                    print(f"DRY-RUN: would NOT close task {task_key}")
                    for blocker in blockers:
                        print(f"  - {blocker}")
                else:
                    print(f"DRY-RUN: would close task {task_key} (phase=completed)")
                return 0
            if blockers:
                errors = [
                    CliError(
                        code="BLOCKER",
                        message=message,
                        field="task.json",
                        suggestion="run task diagnose for blockers",
                    )
                    for message in blockers
                ]
                if args.json:
                    return self._json(multi_error_envelope(errors), args, stream=sys.stderr)
                print(f"ERROR: cannot close task {task_key}", file=sys.stderr)
                for error in errors:
                    print(f"  - {error.message}", file=sys.stderr)
                return 1
            if args.json:
                return self._json(ok_envelope(data=payload), args)
            print(f"Task {task_key} closed (phase=completed). All subtasks verified completed.")
            return 0

        return self._fail(
            "ARGS", f"unknown task action: {args.task_action}",
            exit_code=EXIT_ARGS, args=args,
        )

    # ----- subtask -----

    def _subtask(self, args: argparse.Namespace, project_config: ProjectConfig) -> int:
        parent_task_key = args.parent_task_key
        subtask_id = args.subtask_id
        try:
            if args.subtask_action == "init":
                payload = task_ops.subtask_init(
                    project_config, parent_task_key, subtask_id,
                    task_type=args.task_type,
                    flow=args.flow,
                    complexity=args.complexity,
                    estimate_hours=args.estimate_hours,
                )
                print_envelope(
                    ok_envelope(data=payload), json_mode=getattr(args, "json", False)
                )
                return 0
            if args.subtask_action == "validate":
                message, errors = task_ops.subtask_validate(
                    project_config, parent_task_key, subtask_id
                )
                if errors:
                    errs = [
                        CliError(
                            code="VALIDATION",
                            message=error,
                            field="task.json",
                            suggestion=f"fix subtasks/{subtask_id}/task.json",
                        )
                        for error in errors
                    ]
                    print_envelope(
                        multi_error_envelope(errs),
                        json_mode=getattr(args, "json", False),
                        stream=sys.stderr,
                    )
                    return 1
                print_envelope(
                    ok_envelope(data={"ok": True, "message": message}),
                    json_mode=getattr(args, "json", False),
                )
                return 0
            if args.subtask_action == "status":
                payload = task_ops.subtask_status(
                    project_config, parent_task_key, subtask_id
                )
                print_envelope(
                    ok_envelope(data=payload), json_mode=getattr(args, "json", False)
                )
                return 0
        except task_ops.TaskOpsError as exc:
            return self._fail(
                exc.code, exc.message, field=exc.field,
                suggestion=exc.suggestion, exit_code=exc.exit_code,
            )
        return self._fail(
            "ARGS", f"unknown subtask action: {args.subtask_action}",
            exit_code=EXIT_ARGS,
        )

    # ----- task types -----

    def _plan_policy(self, args: argparse.Namespace, project_config: ProjectConfig) -> int:
        before = project_config.root.stat().st_mtime_ns
        policy, problems = resolve_plan_policy(project_config, args.type)
        if problems or policy is None:
            return self._fail("CONFIG", "; ".join(problems), field="task_type", exit_code=1)
        if project_config.root.stat().st_mtime_ns != before:
            return self._fail("IO", "plan-policy changed the project tree", exit_code=1)
        print_envelope(ok_envelope(data=policy), json_mode=True)
        return 0

    def _types(self, args: argparse.Namespace, project_config: ProjectConfig) -> int:
        types, errors = load_task_conf_types(project_config)
        if errors:
            errs = [CliError(code="CONFIG", message=e, exit_code=1) for e in errors]
            print_envelope(multi_error_envelope(errs), json_mode=False, stream=sys.stderr)
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

    def _flows(self, args: argparse.Namespace, project_config: ProjectConfig) -> int:
        type_id = args.type
        types, errors = load_task_conf_types(project_config)
        if errors:
            errs = [CliError(code="CONFIG", message=e, exit_code=1) for e in errors]
            print_envelope(multi_error_envelope(errs), json_mode=False, stream=sys.stderr)
            return 1
        if type_id not in types:
            return self._fail(
                "NOT-FOUND", f"task type {type_id!r} not found in task-conf",
                field="type", exit_code=EXIT_NOT_FOUND,
                suggestion=f"available types: {', '.join(sorted(types))}",
            )
        flows = types[type_id].get("flows", {})
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

    def _type_prompt(self, args: argparse.Namespace, project_config: ProjectConfig) -> int:
        type_id = args.type
        types, errors = load_task_conf_types(project_config)
        if errors:
            errs = [CliError(code="CONFIG", message=e, exit_code=1) for e in errors]
            print_envelope(multi_error_envelope(errs), json_mode=False, stream=sys.stderr)
            return 1
        if type_id not in types:
            return self._fail(
                "NOT-FOUND", f"task type {type_id!r} not found in task-conf",
                field="type", exit_code=EXIT_NOT_FOUND,
                suggestion=f"available types: {', '.join(sorted(types))}",
            )
        prompt, prompt_errors = load_task_conf_prompt(project_config, type_id)
        if prompt_errors:
            errs = [CliError(code="NOT-FOUND", message=e, exit_code=EXIT_NOT_FOUND)
                    for e in prompt_errors]
            print_envelope(multi_error_envelope(errs), json_mode=False, stream=sys.stderr)
            return EXIT_NOT_FOUND
        print(prompt, end="" if prompt.endswith("\n") else "\n")
        return 0

    def _flow_prompt(self, args: argparse.Namespace, project_config: ProjectConfig) -> int:
        type_id = args.type
        flow_id = args.flow
        types, errors = load_task_conf_types(project_config)
        if errors:
            errs = [CliError(code="CONFIG", message=e, exit_code=1) for e in errors]
            print_envelope(multi_error_envelope(errs), json_mode=getattr(args, "json", False), stream=sys.stderr)
            return 1
        if type_id not in types:
            return self._fail(
                "NOT-FOUND", f"task type {type_id!r} not found in task-conf",
                field="type", exit_code=EXIT_NOT_FOUND,
                suggestion=f"available types: {', '.join(sorted(types))}",
                args=args,
            )
        flows = types[type_id].get("flows", {})
        if flow_id not in flows:
            return self._fail(
                "NOT-FOUND", f"flow {flow_id!r} not found for type {type_id!r}",
                field="flow", exit_code=EXIT_NOT_FOUND,
                suggestion=f"available flows: {', '.join(sorted(flows))}",
                args=args,
            )
        step_id = getattr(args, "step", None)
        if args.task_action == "flow-steps" or step_id is not None:
            try:
                steps = flow_prompt_steps(flows[flow_id])
                if args.task_action == "flow-steps":
                    items = []
                    for step in steps:
                        path = flow_step_path(project_config, type_id, flow_id, step["id"])
                        source = path if path.exists() or path.is_symlink() else path.parent.parent / "prompt.md"
                        item = {key: step[key] for key in ("id", "name", "action", "output", "gate") if key in step}
                        item["prompt_path"] = source.relative_to(project_config.root).as_posix()
                        items.append(item)
                    return self._json(ok_envelope(data={"type": type_id, "flow": flow_id, "steps": items}), args)
                ids = [step["id"] for step in steps]
                if step_id not in ids:
                    return self._fail("NOT-FOUND", f"step {step_id!r} not found in flow {flow_id!r}",
                                      field="step", exit_code=EXIT_NOT_FOUND,
                                      suggestion=f"available steps: {', '.join(ids)}")
                prompt, prompt_errors = load_task_conf_step_prompt(project_config, type_id, flow_id, step_id)
            except (ValueError, OSError, RuntimeError) as exc:
                return self._fail("CONFIG", str(exc), field="steps", exit_code=1, args=args)
        else:
            prompt, prompt_errors = load_task_conf_flow_prompt(project_config, type_id, flow_id)
        if prompt_errors:
            errs = [CliError(code="NOT-FOUND", message=e, exit_code=EXIT_NOT_FOUND)
                    for e in prompt_errors]
            print_envelope(multi_error_envelope(errs), json_mode=False, stream=sys.stderr)
            return EXIT_NOT_FOUND
        print(prompt, end="" if prompt.endswith("\n") else "\n")
        return 0
