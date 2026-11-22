"""Flow definition, flow selection and transition resolution.

Flows are declarative YAML. This module validates the versioned flow format,
evaluates the per-type flow selection table, and resolves a transition for a
current state and event. It contains no semantic judgement about task quality.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from .project_config import ProjectConfig

FLOW_SCHEMA_VERSION = "flow-1"
SELECTION_SCHEMA_VERSION = "flow-selection-1"
FLOW_SCHEMA_FILE = "flow.schema.json"
SELECTION_SCHEMA_FILE = "flow-selection.schema.json"
STATE_RE = re.compile(r"^[a-z][a-z0-9-]*$")
ID_RE = re.compile(r"^[a-z][a-z0-9._-]*$")
NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
EVENT_RE = re.compile(r"^[a-z][a-z0-9._-]*$")


class FlowError(ValueError):
    """A deterministic flow or selection failure."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        field: str | None = None,
        suggestion: str | None = None,
        exit_code: int = 1,
        data: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field
        self.suggestion = suggestion
        self.exit_code = exit_code
        self.data = data


def flow_path(config: ProjectConfig, type_id: str, flow_id: str) -> Path:
    return config.task_conf_root / "types" / type_id / "flows" / flow_id / "config.yaml"


def selection_path(config: ProjectConfig, type_id: str) -> Path:
    return config.task_conf_root / "types" / type_id / "flow-selection.yaml"


def _read_yaml(path: Path, label: str) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [f"{label} not found: {path.as_posix()}"]
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        return None, [f"{label}: cannot read {path.as_posix()}: {exc}"]
    if not isinstance(data, dict):
        return None, [f"{label}: YAML root must be a mapping"]
    return data, []


def _schema_errors(config: ProjectConfig, name: str, data: dict[str, Any]) -> list[str]:
    path = config.schemas_root / name
    if not path.is_file():
        return []
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{name}: invalid JSON schema: {exc}"]
    try:
        from jsonschema import Draft202012Validator

        validator = Draft202012Validator(schema)
        errors = []
        for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
            location = "/".join(str(part) for part in error.path) or "<root>"
            errors.append(f"{name}: {location}: {error.message}")
        return errors
    except Exception as exc:  # pragma: no cover - invalid external schema
        return [f"{name}: cannot apply schema: {exc}"]


def load_flow(config: ProjectConfig, type_id: str, flow_id: str) -> tuple[dict[str, Any] | None, list[str]]:
    data, errors = _read_yaml(flow_path(config, type_id, flow_id), f"flow {type_id}/{flow_id}")
    if errors:
        return None, errors
    errors.extend(validate_flow_definition(data, config=config, type_id=type_id, flow_id=flow_id))
    return data, errors


def _string_list(value: Any, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or not value:
        errors.append(f"{label} must be a non-empty array")
        return []
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{label} entries must be non-empty strings")
            continue
        result.append(item)
    return result


def _step_consistency_errors(
    flow: dict[str, Any],
    label: str,
    seen_states: set[str],
    initial: Any,
    transitions: list[Any],
    edges: dict[str, set[str]],
) -> list[str]:
    """Keep the executable happy path aligned with the declared step order.

    A versioned flow that declares ``steps`` must expose exactly those states,
    start at the first step, and have a transition between every consecutive
    pair. Forward skips are rejected so the documented order cannot drift from
    the executable one.
    """
    steps = flow.get("steps")
    if steps is None:
        return []
    if not isinstance(steps, list) or not steps:
        return [f"{label}: steps must be a non-empty array"]

    errors: list[str] = []
    step_ids: list[str] = []
    for index, step in enumerate(steps):
        item = f"{label}: steps[{index}]"
        if not isinstance(step, dict):
            errors.append(f"{item} must be a mapping")
            continue
        step_id = step.get("id")
        if not isinstance(step_id, str) or not STATE_RE.fullmatch(step_id):
            errors.append(f"{item}: id must be a lowercase slug")
            continue
        if step_id in step_ids:
            errors.append(f"{label}: duplicate step id {step_id!r}")
            continue
        step_ids.append(step_id)

    if not step_ids:
        return errors

    declared = set(step_ids)
    for state in sorted(declared - seen_states):
        errors.append(f"{label}: step {state!r} is not declared in states")
    for state in sorted(seen_states - declared):
        errors.append(f"{label}: state {state!r} has no declared step")
    if isinstance(initial, str) and initial != step_ids[0]:
        errors.append(
            f"{label}: initial_state {initial!r} must be the first step {step_ids[0]!r}"
        )

    order = {state: index for index, state in enumerate(step_ids)}
    for index, transition in enumerate(transitions):
        if not isinstance(transition, dict):
            continue
        source = transition.get("from")
        target = transition.get("to")
        if source in order and target in order and order[target] - order[source] > 1:
            errors.append(
                f"{label}: transition {transition.get('id')!r} skips steps: "
                f"{source} -> {target}"
            )

    for current, following in zip(step_ids, step_ids[1:]):
        if following not in edges.get(current, set()):
            errors.append(
                f"{label}: missing transition from step {current!r} to {following!r}"
            )
    return errors


def validate_flow_definition(
    flow: Any,
    *,
    config: ProjectConfig | None = None,
    type_id: str | None = None,
    flow_id: str | None = None,
) -> list[str]:
    """Return explicit schema and graph errors for a flow definition."""
    label = f"flow {type_id}/{flow_id}" if type_id and flow_id else "flow"
    if not isinstance(flow, dict):
        return [f"{label}: definition must be a mapping"]
    if "schema_version" not in flow:
        return []

    errors: list[str] = []
    if config is not None:
        errors.extend(_schema_errors(config, FLOW_SCHEMA_FILE, flow))

    if flow.get("schema_version") != FLOW_SCHEMA_VERSION:
        errors.append(f"{label}: unsupported schema_version {flow.get('schema_version')!r}")
        return errors
    if not isinstance(flow.get("id"), str) or not STATE_RE.fullmatch(flow["id"]):
        errors.append(f"{label}: id must be a lowercase slug")
    if type_id is not None and flow.get("type") != type_id:
        errors.append(f"{label}: type {flow.get('type')!r} does not match {type_id!r}")

    states = _string_list(flow.get("states"), f"{label}: states", errors)
    seen_states = set()
    for state in states:
        if not STATE_RE.fullmatch(state):
            errors.append(f"{label}: invalid state id {state!r}")
        elif state in seen_states:
            errors.append(f"{label}: duplicate state id {state!r}")
        seen_states.add(state)

    initial = flow.get("initial_state")
    if not isinstance(initial, str) or not initial:
        errors.append(f"{label}: initial_state must be a state id")
    elif initial not in seen_states:
        errors.append(f"{label}: initial_state {initial!r} is not declared in states")

    terminals = _string_list(flow.get("terminal_states"), f"{label}: terminal_states", errors)
    for state in terminals:
        if state not in seen_states:
            errors.append(f"{label}: terminal state {state!r} is not declared in states")

    transitions = flow.get("transitions")
    if not isinstance(transitions, list) or not transitions:
        errors.append(f"{label}: transitions must be a non-empty array")
        transitions = []

    edges: dict[str, set[str]] = defaultdict(set)
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    seen_transitions = set()
    for index, transition in enumerate(transitions):
        item = f"{label}: transitions[{index}]"
        if not isinstance(transition, dict):
            errors.append(f"{item} must be a mapping")
            continue
        transition_id = transition.get("id")
        if not isinstance(transition_id, str) or not ID_RE.fullmatch(transition_id):
            errors.append(f"{item}: id must be a lowercase transition id")
        elif transition_id in seen_transitions:
            errors.append(f"{label}: duplicate transition id {transition_id!r}")
        else:
            seen_transitions.add(transition_id)
        source = transition.get("from")
        target = transition.get("to")
        event = transition.get("event")
        if not isinstance(source, str) or source not in seen_states:
            errors.append(f"{item}: from must reference a declared state")
        if not isinstance(target, str) or target not in seen_states:
            errors.append(f"{item}: to must reference a declared state")
        if not isinstance(event, str) or not EVENT_RE.fullmatch(event):
            errors.append(f"{item}: event must be a lowercase event id")
        if isinstance(source, str) and isinstance(target, str):
            edges[source].add(target)
        if isinstance(source, str) and isinstance(event, str):
            groups[(source, event)].append(str(transition_id))
        when = transition.get("when")
        if when is not None and (not isinstance(when, list)
                                 or any(not isinstance(cond, str) or not cond for cond in when)):
            errors.append(f"{item}: when must be an array of condition ids")

    for (source, event), ids in sorted(groups.items()):
        if len(ids) > 1:
            errors.append(
                f"{label}: ambiguous transitions from {source!r} on {event!r}: {', '.join(ids)}"
            )

    errors.extend(_step_consistency_errors(
        flow, label, seen_states, initial, transitions, edges,
    ))

    if isinstance(initial, str) and initial in seen_states:
        reached = set()
        stack = [initial]
        while stack:
            state = stack.pop()
            if state in reached:
                continue
            reached.add(state)
            stack.extend(sorted(edges.get(state, ())))
        for state in states:
            if state not in reached:
                errors.append(f"{label}: state {state!r} is unreachable from {initial!r}")
        for state in terminals:
            if state in seen_states and state not in reached:
                errors.append(f"{label}: terminal state {state!r} is unreachable from {initial!r}")

    return list(dict.fromkeys(errors))


def load_selection(config: ProjectConfig, type_id: str) -> tuple[dict[str, Any] | None, list[str]]:
    data, errors = _read_yaml(selection_path(config, type_id), f"flow selection {type_id}")
    if errors:
        return None, errors
    type_data, type_errors = _read_yaml(
        config.task_conf_root / "types" / type_id / "config.yaml", f"task type {type_id}"
    )
    if type_errors:
        return None, type_errors
    allowed = type_data.get("allowed_flows", [])
    errors.extend(validate_flow_selection(
        data, config=config, type_id=type_id,
        allowed_flows=allowed if isinstance(allowed, list) else None,
    ))
    return data, errors


def validate_flow_selection(
    selection: Any,
    *,
    config: ProjectConfig | None = None,
    type_id: str | None = None,
    allowed_flows: list[str] | None = None,
) -> list[str]:
    label = f"flow selection {type_id}" if type_id else "flow selection"
    if not isinstance(selection, dict):
        return [f"{label}: definition must be a mapping"]
    errors: list[str] = []
    if config is not None:
        errors.extend(_schema_errors(config, SELECTION_SCHEMA_FILE, selection))
    if selection.get("schema_version") != SELECTION_SCHEMA_VERSION:
        errors.append(f"{label}: unsupported schema_version {selection.get('schema_version')!r}")
        return errors
    if type_id is not None and selection.get("type") != type_id:
        errors.append(f"{label}: type {selection.get('type')!r} does not match {type_id!r}")
    if type(selection.get("version")) is not int or selection["version"] < 1:
        errors.append(f"{label}: version must be a positive integer")

    facts = selection.get("facts", {})
    if not isinstance(facts, dict):
        errors.append(f"{label}: facts must be a mapping")
        facts = {}
    for name, spec in facts.items():
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            errors.append(f"{label}: invalid fact name {name!r}")
        if not isinstance(spec, dict):
            errors.append(f"{label}: fact {name!r} must be a mapping")
            continue
        kind = spec.get("type")
        if kind not in ("boolean", "enum", "string"):
            errors.append(f"{label}: fact {name!r} has unsupported type {kind!r}")
        if kind == "enum":
            values = spec.get("values")
            if not isinstance(values, list) or not values or any(
                not isinstance(value, str) or not value for value in values
            ):
                errors.append(f"{label}: enum fact {name!r} requires non-empty string values")

    rules = selection.get("rules")
    if not isinstance(rules, list) or not rules:
        errors.append(f"{label}: rules must be a non-empty array")
        rules = []
    seen_rules = set()
    fallbacks = []
    for index, rule in enumerate(rules):
        item = f"{label}: rules[{index}]"
        if not isinstance(rule, dict):
            errors.append(f"{item} must be a mapping")
            continue
        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or not ID_RE.fullmatch(rule_id):
            errors.append(f"{item}: id must be a lowercase rule id")
        elif rule_id in seen_rules:
            errors.append(f"{label}: duplicate rule id {rule_id!r}")
        else:
            seen_rules.add(rule_id)
        flow = rule.get("flow")
        if not isinstance(flow, str) or not flow:
            errors.append(f"{item}: flow is required")
        elif allowed_flows is not None and flow not in allowed_flows:
            errors.append(f"{item}: flow {flow!r} is not allowed by the type")
        if rule.get("fallback") is True:
            fallbacks.append(str(rule_id))
            if "when" in rule:
                errors.append(f"{item}: fallback rule cannot declare when")
            continue
        when = rule.get("when")
        if not isinstance(when, dict) or not when:
            errors.append(f"{item}: non-fallback rule requires a non-empty when mapping")
            continue
        for name, expected in when.items():
            if name not in facts:
                errors.append(f"{item}: unknown fact {name!r}")
                continue
            spec = facts.get(name, {})
            if isinstance(spec, dict) and spec.get("type") == "enum":
                values = spec.get("values", [])
                if expected not in values:
                    errors.append(f"{item}: fact {name!r} must be one of {', '.join(map(str, values))}")
    if len(fallbacks) > 1:
        errors.append(f"{label}: multiple fallback rules: {', '.join(fallbacks)}")
    return list(dict.fromkeys(errors))


def parse_facts(values: list[str]) -> dict[str, str]:
    facts: dict[str, str] = {}
    for value in values:
        name, separator, raw = value.partition("=")
        if not separator or not name.strip() or not raw.strip():
            raise FlowError("ARGS", f"--fact must use name=value, got {value!r}", field="fact")
        name = name.strip()
        if name in facts:
            raise FlowError("ARGS", f"duplicate --fact {name!r}", field="fact")
        facts[name] = raw.strip()
    return facts


def _fact_value(name: str, raw: str, spec: dict[str, Any]) -> Any:
    kind = spec.get("type")
    if kind == "boolean":
        lowered = raw.lower()
        if lowered in ("true", "yes", "1"):
            return True
        if lowered in ("false", "no", "0"):
            return False
        raise FlowError("INVALID-FACT", f"fact {name!r} expects true or false", field=name,
                        suggestion="use --fact name=true or --fact name=false")
    if kind == "enum":
        values = spec.get("values", [])
        if raw not in values:
            raise FlowError("INVALID-FACT", f"fact {name!r} must be one of {', '.join(map(str, values))}",
                            field=name, suggestion=f"use one of: {', '.join(map(str, values))}")
        return raw
    if kind == "string":
        return raw
    raise FlowError("INVALID-FACT", f"fact {name!r} has unsupported type {kind!r}", field=name)


def select_flow(
    config: ProjectConfig, type_id: str, raw_facts: list[str],
) -> dict[str, Any]:
    selection, errors = load_selection(config, type_id)
    if errors:
        raise FlowError("CONFIG", "; ".join(errors), field="flow-selection",
                        suggestion=f"fix {selection_path(config, type_id).relative_to(config.root).as_posix()}")
    assert selection is not None
    facts_conf = selection.get("facts", {})
    supplied = parse_facts(raw_facts)
    unknown = sorted(set(supplied) - set(facts_conf))
    if unknown:
        raise FlowError(
            "UNKNOWN-FACT", f"unknown fact(s): {', '.join(unknown)}", field=unknown[0],
            suggestion=f"known facts: {', '.join(sorted(facts_conf)) or 'none'}",
        )
    facts = {name: _fact_value(name, raw, facts_conf[name]) for name, raw in supplied.items()}

    missing: dict[str, list[str]] = {}
    matched: list[dict[str, Any]] = []
    fallback: dict[str, Any] | None = None
    for rule in selection.get("rules", []):
        if rule.get("fallback") is True:
            fallback = rule
            continue
        absent = [name for name in rule.get("when", {}) if name not in facts]
        if absent:
            for name in absent:
                missing[name] = list(facts_conf[name].get("values", []))
            continue
        if all(facts[name] == expected for name, expected in rule["when"].items()):
            matched.append(rule)

    if len(matched) > 1:
        ids = [str(rule.get("id")) for rule in matched]
        raise FlowError(
            "CONFLICT", f"conflicting flow selection rules: {', '.join(ids)}",
            field="fact", exit_code=5,
            suggestion="supply the fact that distinguishes the rules or ask the owner to resolve the table",
            data={"matched_rules": ids},
        )
    if len(matched) == 1:
        rule = matched[0]
        return {
            "type": type_id,
            "selection_version": selection["version"],
            "rule_id": rule.get("id"),
            "flow": rule.get("flow"),
            "reason": rule.get("reason"),
            "facts": facts,
            "matched_rules": [rule.get("id")],
        }
    if missing:
        fields = ", ".join(sorted(missing))
        raise FlowError(
            "MISSING-FACT", f"missing required fact(s): {fields}", field=sorted(missing)[0],
            suggestion="; ".join(
                f"{name}: {', '.join(values)}" if values else f"{name}: value required"
                for name, values in sorted(missing.items())
            ),
            data={"missing_facts": sorted(missing), "allowed_values": missing},
        )
    if fallback is not None:
        return {
            "type": type_id,
            "selection_version": selection["version"],
            "rule_id": fallback.get("id"),
            "flow": fallback.get("flow"),
            "reason": fallback.get("reason"),
            "facts": facts,
            "matched_rules": [fallback.get("id")],
            "fallback": True,
        }
    raise FlowError(
        "NO-RULE", "no flow selection rule matched the supplied facts", field="fact",
        suggestion="review the selection table or provide the missing fact",
        data={"facts": facts},
    )


def initial_flow_state(flow: dict[str, Any] | None) -> str | None:
    if not isinstance(flow, dict) or flow.get("schema_version") != FLOW_SCHEMA_VERSION:
        return None
    state = flow.get("initial_state")
    return state if isinstance(state, str) else None


def transition_options(flow: dict[str, Any] | None, state: str | None) -> list[dict[str, Any]]:
    if not isinstance(flow, dict) or flow.get("schema_version") != FLOW_SCHEMA_VERSION:
        return []
    options = []
    for transition in flow.get("transitions", []):
        if isinstance(transition, dict) and transition.get("from") == state:
            options.append({
                "id": transition.get("id"),
                "event": transition.get("event"),
                "to": transition.get("to"),
                "when": transition.get("when", []),
            })
    return options


def find_transition(flow: dict[str, Any] | None, state: str, event: str) -> dict[str, Any]:
    if not isinstance(flow, dict) or flow.get("schema_version") != FLOW_SCHEMA_VERSION:
        raise FlowError("NO-FLOW", "the selected flow has no executable transitions",
                        field="flow", suggestion="use a flow with schema_version flow-1")
    candidates = [
        transition for transition in flow.get("transitions", [])
        if isinstance(transition, dict)
        and transition.get("from") == state and transition.get("event") == event
    ]
    if not candidates:
        options = transition_options(flow, state)
        events = ", ".join(sorted({str(item["event"]) for item in options})) or "none"
        raise FlowError(
            "UNKNOWN-EVENT", f"no transition from {state!r} on event {event!r}",
            field="event", suggestion=f"available events: {events}",
            data={"state": state, "event": event, "available": options},
        )
    if len(candidates) > 1:
        ids = [str(item.get("id")) for item in candidates]
        raise FlowError(
            "CONFLICT", f"ambiguous transitions from {state!r} on {event!r}: {', '.join(ids)}",
            field="event", exit_code=5, data={"transition_ids": ids},
        )
    return candidates[0]
