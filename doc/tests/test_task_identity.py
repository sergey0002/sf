import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "doc/tools/arch/__main__.py"
sys.path.insert(0, str(ROOT / "doc" / "tools"))
from arch.body_validation import get_supported_body_types  # noqa: E402
from arch.validation import load_task_conf_types  # noqa: E402


def cli(*args):
    return subprocess.run(
        [sys.executable, str(CLI), *args], cwd=ROOT,
        text=True, capture_output=True, check=False,
    )


class TaskIdentityContractTests(unittest.TestCase):
    def test_close_checks_task_and_subtask_dependencies(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            _, card = self._prepare_decompose_parent(root)
            task = json.loads(card.read_bytes())
            task["depends_on"] = ["UI-9998-0001", "UI-9997"]
            card.write_text(json.dumps(task), encoding="utf-8")
            child = root / "doc/tasks/UI-9998/subtasks/0001/task.json"
            child.parent.mkdir(parents=True)
            child.write_text('{"task_key":"UI-9998-0001","phase":"intake"}', encoding="utf-8")
            original = card.read_bytes()

            def diagnose():
                result = self._cli_at(root, "task", "diagnose", "UI-9999", "--json", "--brief")
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)["data"]

            data = diagnose()
            self.assertFalse(data["can_close"])
            self.assertEqual([dep["state"] for dep in data["dependencies"]], ["open", "missing"])
            preview = self._cli_at(root, "task", "close", "UI-9999", "--dry-run", "--json")
            self.assertEqual(json.loads(preview.stdout)["data"]["blockers"], data["close_blockers"])
            close = self._cli_at(root, "task", "close", "UI-9999", "--json")
            self.assertEqual(close.returncode, 1)
            self.assertEqual(card.read_bytes(), original)

            child.write_text('{"task_key":"UI-9998-0001","phase":"completed"}', encoding="utf-8")
            parent = root / "doc/tasks/UI-9997/task.json"
            parent.parent.mkdir()
            parent.write_text('{"task_key":"UI-9997","phase":"completed","depends_on":["UI-9999"]}', encoding="utf-8")
            self.assertIn("Dependency cycle", " ".join(diagnose()["close_blockers"]))
            parent.write_text('{"task_key":"UI-9997","phase":"completed"}', encoding="utf-8")
            self.assertTrue(diagnose()["can_close"])

    def test_evidence_records_real_exit_and_rejects_changed_snapshot(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            directory, card = self._prepare_decompose_parent(root)
            task = json.loads(card.read_bytes())
            task.update(acceptance_policy="case-coverage-v1", acceptance_criteria=["AC-1: expected output"])
            card.write_text(json.dumps(task), encoding="utf-8")
            stage = directory / "stage1"
            stage.mkdir(exist_ok=True)
            (stage / "plan.md").write_text("# Test plan\n", encoding="utf-8")
            evidence = stage / "verification.json"
            evidence.write_text(json.dumps({"task_key": "UI-9999", "stage_id": "stage1", "checks": [],
                                            "planned_checks": [{"id": "CASE-1", "covers": ["AC-1"], "expected": "OK"}]}),
                                encoding="utf-8")
            tracked = root / "input.txt"
            tracked.write_text("before", encoding="utf-8")
            cli_args = ("task", "evidence", "UI-9999")
            capture = (*cli_args, "--file", "input.txt", "--case", "CASE-1")

            rejected = self._cli_at(root, *capture, "--run", sys.executable, "-c", "raise SystemExit(7)")
            self.assertEqual(rejected.returncode, 7, rejected.stderr)
            self.assertEqual(json.loads(evidence.read_bytes())["checks"][0]["exit_code"], 7)
            before = evidence.read_bytes()
            changed = self._cli_at(root, *capture, "--run", sys.executable, "-c",
                                   "from pathlib import Path; Path('input.txt').write_text('after')")
            self.assertEqual(changed.returncode, 1, changed.stderr)
            self.assertEqual(evidence.read_bytes(), before)
            stale = self._cli_at(root, *cli_args, "--check")
            self.assertEqual(stale.returncode, 1, stale.stderr)
            self.assertFalse(json.loads(stale.stdout)["data"]["current"])
            passed = self._cli_at(root, *capture, "--replace-snapshot", "--run", sys.executable, "-c", "pass")
            self.assertEqual(passed.returncode, 0, passed.stderr)
            data = json.loads(evidence.read_bytes())
            self.assertEqual(data["status"], "passed")
            self.assertEqual([check["exit_code"] for check in data["checks"]], [0])
            self.assertEqual(self._cli_at(root, *cli_args, "--check").returncode, 0)

    def test_docs_tree_contains_all_indexed_records_without_bodies(self):
        result = cli("docs", "tree")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)["data"]
        self.assertEqual(payload["architecture_root"], "doc/architecture")
        self.assertEqual(payload["guide"], "README.md")

        def flatten(node, prefix=()):
            for item in node["documents"]:
                self.assertEqual(Path(item["path"]).parts[:-1], prefix)
                self.assertNotIn("content", item)
                yield item["id"], item["path"]
            for name, child in node["directories"].items():
                yield from flatten(child, (*prefix, name))

        index = json.loads((ROOT / "doc/architecture/index.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(flatten(payload["tree"])),
                         sorted((item["id"], item["path"]) for item in index["documents"]))

    def test_flow_step_prompt_override_fallback_and_invalid_ids(self):
        options = ("--type", "feature", "--flow", "standard-implementation")
        result = cli("task", "flow-steps", *options)
        self.assertEqual(result.returncode, 0, result.stderr)
        steps = json.loads(result.stdout)["data"]["steps"]
        ids = [step["id"] for step in steps]
        self.assertLess(ids.index("architecture-context"), ids.index("plan"))
        sources = {step["id"]: step["prompt_path"] for step in steps}
        self.assertTrue(sources["architecture-context"].endswith("stepsprompt/architecture-context.md"))
        selected = cli("task", "flow-prompt", *options, "--step", "architecture-context")
        self.assertEqual(selected.returncode, 0, selected.stderr)
        self.assertEqual(selected.stdout, (ROOT / sources["architecture-context"]).read_text(encoding="utf-8"))
        selected = cli("task", "flow-prompt", *options, "--step", "verify")
        self.assertEqual(selected.returncode, 0, selected.stderr)
        self.assertTrue(re.match(r"^\d+\. `verify`", selected.stdout))
        self.assertNotIn("`close`", selected.stdout)
        invalid = cli("task", "flow-prompt", *options, "--step", "../prompt")
        self.assertEqual(invalid.returncode, 20)
        self.assertEqual(invalid.stdout, "")

    def test_list_filters_exact_doc_ids_without_returning_bodies(self):
        result = cli("list", "--id", "ARCH-contract", "--id", "FLOW-cli-task-lifecycle",
                     "--id", "FLOW-cli-task", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)["data"]
        self.assertEqual([row["id"] for row in rows], ["ARCH-contract", "FLOW-cli-task-lifecycle"])
        self.assertEqual(rows[0]["path"], "system/architecture-contract.md")
        self.assertTrue(all("content" not in row and "status" in row for row in rows))

        result = cli("list", "--id", "ARCH-contract", "--id", "FLOW-cli-task-lifecycle",
                     "--domain", "task-lifecycle", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([row["id"] for row in json.loads(result.stdout)["data"]], ["FLOW-cli-task-lifecycle"])

    def test_brief_checks_name_success_and_keep_failure_details(self):
        for command, expected in (
            (("validate", "--brief"), "OK validate: architecture"),
            (("scan", "--scope", "index", "--brief"), "OK scan: index"),
        ):
            with self.subTest(command=command):
                result = cli(*command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, expected + "\n")
                self.assertEqual(result.stderr, "")

        result = cli("validate", "doc/config/paths.yaml", "--brief")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("doc/config/paths.yaml", result.stderr)
        self.assertIn("only .md files", result.stderr)

        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            # Create required roots for ProjectConfig
            (root / "doc" / "config").mkdir(parents=True)
            (root / "doc" / "architecture").mkdir(parents=True)
            (root / "doc" / "architecture" / "schemas").mkdir(parents=True)
            (root / "doc" / "config" / "task-conf").mkdir(parents=True)  # Exists but empty
            (root / "doc" / "skills").mkdir(parents=True)
            (root / "doc" / "tasks").mkdir(parents=True)
            # Copy the config file
            (root / "doc" / "config" / "paths.yaml").write_text((ROOT / "doc" / "config" / "paths.yaml").read_text(), encoding="utf-8")
            result = self._cli_at(root, "scan", "--scope", "task-conf", "--brief")
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("TASK-CONF", result.stderr)
            self.assertIn("doc/config/task-conf/types", result.stderr)

    def test_task_flow_prompts_follow_declared_steps(self):
        types, errors = load_task_conf_types(ROOT)
        self.assertEqual(errors, [])
        self.assertTrue(types)
        for type_id, config in types.items():
            flows = config["flows"]
            self.assertEqual(set(config["allowed_flows"]), set(flows))
            self.assertIn(config["default_flow"], flows)
            for flow_id, flow in flows.items():
                with self.subTest(type=type_id, flow=flow_id):
                    self.assertEqual(flow["type"], type_id)
                    for field in ("subtask_policy", "close_policy"):
                        self.assertEqual(flow[field], config[field])
                    steps = [step["id"] for step in flow["steps"]]
                    self.assertEqual(len(steps), len(set(steps)))
                    self.assertEqual(steps[-1], "close")
                    prompt = (
                        ROOT / "doc/config/task-conf/types" / type_id
                        / "flows" / flow_id / "prompt.md"
                    ).read_text(encoding="utf-8")
                    self.assertEqual(re.findall(r"^\d+\. `([^\x60]+)`", prompt, re.M), steps)

    def test_jira_has_four_digit_bare_key(self):
        result = cli("task-key", "--source", "jira", "--number", "0427")
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)["data"]
        self.assertEqual(value["task_key"], "0427")
        self.assertEqual(value["source_prefix"], None)
        self.assertEqual(value["task_number"], "0427")

    def test_user_input_is_ui_source_and_prefixed(self):
        result = cli("task-key", "--source", "ui", "--number", "0042")
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)["data"]
        self.assertEqual(value["source_type"], "ui")
        self.assertEqual(value["task_key"], "UI-0042")

    def test_other_source_requires_explicit_prefix(self):
        missing = cli("task-key", "--source", "github", "--number", "0042")
        self.assertNotEqual(missing.returncode, 0)
        success = cli("task-key", "--source", "github", "--prefix", "gh", "--number", "0042")
        self.assertEqual(success.returncode, 0, success.stderr)
        self.assertEqual(json.loads(success.stdout)["data"]["task_key"], "GH-0042")

    def test_rejects_bad_number_and_wrong_prefix_policy(self):
        for number in ("123", "12345", "12A4", "-123"):
            with self.subTest(number=number):
                self.assertNotEqual(cli("task-key", "--source", "jira", "--number", number).returncode, 0)
        self.assertNotEqual(cli("task-key", "--source", "jira", "--prefix", "JR", "--number", "1234").returncode, 0)
        self.assertNotEqual(cli("task-key", "--source", "ui", "--prefix", "USR", "--number", "1234").returncode, 0)
        self.assertNotEqual(cli("task-key", "--source", "github", "--prefix", "UI", "--number", "1234").returncode, 0)

    def test_numbered_fixture_is_consistent(self):
        task_path = ROOT / "doc/tasks/UI-0001/task.json"
        data = json.loads(task_path.read_text(encoding="utf-8"))
        self.assertEqual(data["task_number"], "0001")
        self.assertEqual(data["source"]["type"], "ui")
        self.assertEqual(data["task_key"], "UI-0001")
        self.assertEqual(task_path.parent.name, data["task_key"])
        self.assertRegex(data["task_number"], re.compile(r"^[0-9]{4}$"))
        derived = cli("task-key", "--source", data["source"]["type"], "--number", data["task_number"])
        self.assertEqual(derived.returncode, 0, derived.stderr)
        self.assertEqual(json.loads(derived.stdout)["data"]["task_key"], data["task_key"])
        for reference in data["project_context_refs"]:
            self.assertTrue((task_path.parent / reference).resolve().exists(), reference)
        self.assertFalse(task_path.parent.joinpath("task.md").exists())

    def test_skill_contracts_cover_identity_and_no_guessing(self):
        create = (ROOT / "doc/skills/create-task/SKILL.md").read_text(encoding="utf-8")
        resume = (ROOT / "doc/skills/go-to-task/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("source.type: ui", create)
        self.assertIn("four-decimal-digit task number", create)
        self.assertIn("Jira `1234` (no prefix)", create)
        self.assertIn("UI-1234", create)
        self.assertIn("Never invent or allocate one yourself", create)
        self.assertIn("four digits", resume)

    def test_architecture_documents_record_source_key_contract(self):
        glossary = (ROOT / "doc/architecture/glossary.md").read_text(encoding="utf-8")
        task_entity = (ROOT / "doc/architecture/domains/task-lifecycle/entities/task-input.md").read_text(encoding="utf-8")
        constraints = (ROOT / "doc/architecture/system/constraints-risks.md").read_text(encoding="utf-8")
        self.assertIn("ввод пользователя использует `UI-1234`", glossary)
        self.assertIn("Ключи Jira — чистый номер", task_entity)
        self.assertIn("аллокатор номеров/глобальный реестр уникальности", constraints)
        manifest = (ROOT / "Манифест агентной software factory.md").read_text(encoding="utf-8")
        self.assertIn("source.type: ui", manifest)
        self.assertIn("Jira — номер без префикса", manifest)
        self.assertIn("<source-prefix>-2045", manifest)

    def test_environment_docs_cli_and_index(self):
        result = cli("validate")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = cli("index", "check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_task_init_creates_directory_and_task_json(self):
        result = cli("task", "init", "UI-9999")
        self.assertEqual(result.returncode, 0, result.stderr)
        task_dir = ROOT / "doc/tasks/UI-9999"
        self.assertTrue(task_dir.is_dir(), "task directory should be created")
        self.assertTrue((task_dir / "task.json").exists(), "task.json should be created")
        self.assertTrue((task_dir / "stage1").is_dir(), "stage1 directory should be created")
        data = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
        self.assertEqual(data["task_key"], "UI-9999")
        self.assertEqual(data["task_number"], "9999")
        self.assertEqual(data["source"]["type"], "ui")
        self.assertFalse((task_dir / "task.md").exists(), "task.md must not be created")
        # cleanup
        import shutil
        shutil.rmtree(task_dir)

    def test_task_init_rejects_collision(self):
        result = cli("task", "init", "UI-0001")
        self.assertNotEqual(result.returncode, 0, "init on existing key should fail")
        self.assertIn("already exists", result.stderr)

    def test_task_init_rejects_invalid_key(self):
        for bad in ("123", "12345", "12A4", "ui-0001", "GH-123", "UI-0001-extra"):
            with self.subTest(key=bad):
                result = cli("task", "init", bad)
                self.assertNotEqual(result.returncode, 0, f"invalid key {bad} should fail")

    def test_task_validate_passes_for_ui_0001(self):
        result = cli("task", "validate", "UI-0001")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("is valid", result.stdout)

    def test_task_validate_rejects_missing(self):
        result = cli("task", "validate", "UI-9999")
        self.assertNotEqual(result.returncode, 0, "validate on missing task should fail")
        self.assertIn("not found", result.stderr)

    def test_task_workspace_and_status(self):
        result = cli("task", "workspace", "UI-0001")
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)["data"]
        self.assertEqual(value["task_key"], "UI-0001")

        result = cli("task", "status", "UI-0001")
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)["data"]
        self.assertEqual(value["task_key"], "UI-0001")
        self.assertFalse(value["has_task_md"])

    def test_task_validate_accepts_traceability_fields(self):
        result = cli("task", "validate", "UI-0001")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((ROOT / "doc/tasks/UI-0001/task.json").read_text(encoding="utf-8"))
        # New fields from data/ best practices
        self.assertIn("task_id", data)
        self.assertIn("kind", data)
        self.assertIn("scope", data)
        self.assertIsInstance(data["scope"], dict)
        self.assertIn("in", data["scope"])
        self.assertIn("out", data["scope"])
        self.assertIn("allowed_files_modules", data)
        self.assertIn("current_behavior", data)
        self.assertIn("evidence", data)
        self.assertIn("contracts_and_invariants", data)
        self.assertIn("risk", data)
        self.assertIn("authority", data)
        self.assertIn("source", data)
        self.assertIn("revision", data["source"])
        self.assertIn("captured_at", data["source"])
        # Traceability fields from UI-0005
        self.assertIn("attachments", data["source"])
        self.assertIn("comments", data["source"])
        self.assertIn("history", data["source"])
        self.assertIn("related_docs", data)
        self.assertIn("related_tests", data)
        self.assertIn("changed_files", data)
        self.assertIn("owner", data)
        self.assertIn("priority", data)
        self.assertIn("stage_history", data)

    def _cli_at(self, root, *args, cwd=None):
        return subprocess.run(
            [sys.executable, str(CLI), "--root", str(root), *args],
            cwd=cwd, text=True, capture_output=True, check=False,
        )

    def _paths_fixture(self, root, docs, index):
        architecture = f"{docs}/architecture"
        roots = {
            "architecture": architecture, "tasks": f"{docs}/tasks",
            "schemas": f"{architecture}/schemas", "task_conf": f"{docs}/config/task-conf",
            "skills": f"{docs}/skills", "config": f"{docs}/config", "index": index,
        }
        shutil.copytree(ROOT / "doc/architecture/schemas", root / roots["schemas"])
        shutil.copytree(ROOT / "doc/config/task-conf", root / roots["task_conf"])
        for key in ("tasks", "skills"):
            (root / roots[key]).mkdir()
        (root / architecture / "sample.md").write_text(
            "---\nid: DOC_SAMPLE\ntype: note\ntitle: Sample\nsummary: Fixture\nstatus: draft\n"
            "domain: system\n---\nExample\n", encoding="utf-8",
        )
        config = yaml.safe_load((ROOT / "doc/config/paths.yaml").read_text(encoding="utf-8"))
        config.update(doc_root=docs, roots=roots, allowed_paths=[
            "{architecture}/sample.md", "{architecture}/{index}", "{schemas}/{slug}.json",
            "{schemas}/bodies/{slug}.json", "{config}/paths.yaml",
            "{task_conf}/types/{type}/{slug}.yaml", "{task_conf}/types/{type}/prompt.md",
            "{task_conf}/types/{type}/flows/{flow}/{slug}.yaml",
            "{task_conf}/types/{type}/flows/{flow}/prompt.md",
            "{task_conf}/types/{type}/flows/{flow}/stepsprompt/{slug}.md",
            "{tasks}/{task_key}/task.json", "{tasks}/{task_key}/stage{stage}/{slug}.md",
            "{tasks}/{task_key}/stage{stage}/{slug}.json",
            "{tasks}/{task_key}/subtasks/{subtask_id}/task.json",
        ])
        config["project"]["document_types"] = ["note"]
        config_path = root / roots["config"] / "paths.yaml"
        config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
        return config_path, config

    def test_configured_paths_work_on_clean_layouts(self):
        with tempfile.TemporaryDirectory() as dirname:
            workspace = Path(dirname)
            for docs, index in (("doc", "index.json"), ("handbook", "cache/catalog.json"),
                                ("private/knowledge", "cache/catalog.json")):
                with self.subTest(docs=docs):
                    root = workspace / docs.split("/")[0]
                    config, _ = self._paths_fixture(root, docs, index)
                    if docs.startswith("private/"):
                        subprocess.run(["git", "init", "-q", str(root)], check=True)
                        (root / ".gitignore").write_text("/private/\n", encoding="utf-8")
                        subprocess.run(["git", "-C", str(root), "check-ignore", "-q",
                                        f"{docs}/architecture/sample.md"], check=True)
                    options = () if docs == "doc" else ("--config", str(config.relative_to(root)))
                    for args in (("list", "--json"), ("show", "DOC_SAMPLE"), ("index", "build"),
                                 ("index", "check"), ("validate", "--brief"),
                                 ("task", "init", "UI-9999"),
                                 ("task", "subtask", "init", "UI-9999", "0001"),
                                 ("task", "subtask", "validate", "UI-9999", "0001"),
                                 ("task", "flow-prompt", "--type", "feature", "--flow", "standard-implementation"),
                                 ("task", "flow-prompt", "--type", "feature", "--flow", "standard-implementation",
                                  "--step", "architecture-context"),
                                 ("docs", "tree"),
                                 ("docs", "paths", "--check")):
                        result = self._cli_at(root, *options, *args, cwd=workspace)
                        self.assertEqual(result.returncode, 0, (args, result.stdout, result.stderr))
                        if args[0] == "list":
                            self.assertIn("DOC_SAMPLE", result.stdout)
                        if args[0] == "show":
                            self.assertEqual(result.stdout, "Example\n")
                        if args == ("docs", "tree"):
                            self.assertEqual(json.loads(result.stdout)["data"]["architecture_root"],
                                             f"{docs}/architecture")
                    task_path = root / docs / "tasks/UI-9999/task.json"
                    task = json.loads(task_path.read_text(encoding="utf-8"))
                    task["implementation_plan"] = ["Verify configured task paths"]
                    task["subtasks"] = [{"id": "0001", "title": "Fixture", "status": "open",
                                         "path": "subtasks/0001/task.json"}]
                    task_path.write_text(json.dumps(task), encoding="utf-8")
                    result = self._cli_at(root, *options, "task", "validate", "UI-9999", cwd=workspace)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    expected_index = root / docs / "architecture" / index
                    self.assertIn("DOC_SAMPLE", expected_index.read_text(encoding="utf-8"))
                    self.assertFalse((root / index).exists())
                    paths = self._cli_at(root, *options, "docs", "paths", "--resolved", cwd=workspace)
                    self.assertEqual(paths.returncode, 0, paths.stderr)
                    resolved = json.loads(paths.stdout)["data"]
                    self.assertEqual(resolved["config"], config.relative_to(root).as_posix())
                    self.assertEqual(resolved["roots"]["index"], expected_index.relative_to(root).as_posix())
                    result = self._cli_at(root, *options, "task", "diagnose", "UI-9999",
                                          "--json", "--brief", cwd=workspace)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout)["data"]["refs"]["task"],
                                     f"{docs}/tasks/UI-9999/task.json")
                    if docs != "doc":
                        self.assertFalse((root / "doc/tasks/UI-9999").exists())
                    rogue = root / docs / "architecture/rogue.txt"
                    rogue.write_text("undeclared", encoding="utf-8")
                    result = self._cli_at(root, *options, "docs", "paths", "--check", cwd=workspace)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn(f"{docs}/architecture/rogue.txt", result.stdout + result.stderr)

    def test_bad_project_config_fails_before_index_write(self):
        with tempfile.TemporaryDirectory() as dirname:
            workspace = Path(dirname)
            root = workspace / "project"
            config_path, config = self._paths_fixture(root, "doc", "index.json")
            outside = workspace / "outside"
            outside.mkdir()
            (root / "linked-outside").symlink_to(outside, target_is_directory=True)
            candidates = (
                ("roots: [", "Invalid YAML"),
                ("roots: {}\nroots: {}\n", "duplicate key"),
                (yaml.safe_dump({**config, "allowed_paths": "bad"}), "allowed_paths"),
                (yaml.safe_dump({**config, "roots": {**config["roots"], "index": "../bad.json"}}),
                 "roots.index"),
                (yaml.safe_dump({**config, "roots": {**config["roots"], "tasks": "linked-outside"}}),
                 "roots.tasks"),
            )
            for contents, field in candidates:
                with self.subTest(field=field):
                    # Select the bad override while a valid default exists.
                    override = workspace / "override.yaml"
                    override.write_text(contents, encoding="utf-8")
                    before = {p: p.read_bytes() if p.is_file() else None for p in workspace.rglob("*")}
                    result = self._cli_at(root, "--config", str(override), "index", "build", cwd=workspace)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn(field, result.stderr)
                    self.assertIn("override.yaml", result.stderr)
                    after = {p: p.read_bytes() if p.is_file() else None for p in workspace.rglob("*")}
                    self.assertEqual(after, before)
            result = self._cli_at(root, "--config", str(config_path), "index", "build", cwd=workspace)
            self.assertEqual(result.returncode, 0, result.stderr)

    def _prepare_temp_root(self, temp):
        """Isolated root that still carries the real config contracts."""
        root = Path(temp.name)
        # Copy all required roots for ProjectConfig
        shutil.copytree(ROOT / "doc" / "config", root / "doc" / "config")
        shutil.copytree(ROOT / "doc" / "architecture", root / "doc" / "architecture")
        shutil.copytree(ROOT / "doc" / "skills", root / "doc" / "skills")
        return root

    def _make_minimal_task(self, overrides=None):
        base = {
            "schema_version": "draft-0.2",
            "task_key": "UI-9999",
            "task_number": "9999",
            "source": {"type": "ui", "native_id": None, "provenance": "test", "revision": None, "captured_at": None},
            "title": "t",
            "intent": "t",
            "kind": "feature",
            "scope": {"in": [], "out": [], "allowed_files_modules": []},
            "current_behavior": None,
            "evidence": [],
            "contracts_and_invariants": [],
            "acceptance_criteria": [],
            "target_release": "unset",
            "project_context_refs": [],
            "constraints": [],
            "assumptions": [],
            "open_questions": [],
            "risk": "low",
            "authority": {"allowed": [], "forbidden": [], "approval_required": []},
            "approvals": [],
            "related_docs": [],
            "related_tests": [],
            "changed_files": {"added": [], "modified": [], "deleted": []},
            "owner": "unset",
            "priority": "unset",
            "stage_history": [],
        }
        if overrides:
            base.update(overrides)
        return base

    def test_close_and_diagnose_share_blockers_without_writing(self):
        for declared in (True, False):
            temp = tempfile.TemporaryDirectory()
            with self.subTest(declared=declared), temp:
                root = self._prepare_temp_root(temp)
                tasks = root / "doc/tasks/UI-9999"
                tasks.mkdir(parents=True)
                parent = tasks / "task.json"
                parent.write_text(json.dumps(self._make_minimal_task({
                    "task_type": "bugfix", "flow": "standard-implementation",
                    "phase": "verification", "complexity": "low", "research_docs": [],
                    "depends_on": [], "rollback_plan": "Restore fixture",
                    "subtasks": ([{"id": "0001", "title": "Child", "status": "open",
                                   "path": "subtasks/0001/task.json"}] if declared else []),
                })), encoding="utf-8")
                if not declared:
                    child = tasks / "subtasks/0001/task.json"
                    child.parent.mkdir(parents=True)
                    child.write_text('{"phase": "execution"}', encoding="utf-8")
                before = parent.read_bytes()
                valid = self._cli_at(root, "task", "validate", "UI-9999")
                self.assertEqual(valid.returncode, 0, valid.stderr)
                diag = self._cli_at(root, "task", "diagnose", "UI-9999", "--json")
                diagnosis = json.loads(diag.stdout)["data"]
                self.assertFalse(diagnosis["can_close"])
                blockers = diagnosis["close_blockers"]
                self.assertIn("0001", blockers[0])
                preview = self._cli_at(root, "task", "close", "UI-9999", "--json", "--dry-run")
                self.assertEqual(preview.returncode, 0, preview.stderr)
                self.assertFalse(json.loads(preview.stdout)["data"]["would_close"])
                self.assertEqual(json.loads(preview.stdout)["data"]["blockers"], blockers)
                self.assertEqual(parent.read_bytes(), before)
                refused = self._cli_at(root, "task", "close", "UI-9999", "--json")
                self.assertEqual(refused.returncode, 1)
                self.assertEqual(refused.stdout, "")
                errors = json.loads(refused.stderr)["errors"]
                self.assertEqual([error["message"] for error in errors], blockers)
                self.assertEqual(parent.read_bytes(), before)

    def test_strict_acceptance_checks_each_case_and_verified_snapshot(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            self._paths_fixture(root, "doc", "index.json")
            directory = root / "doc/tasks/UI-9999"
            stage = directory / "stage1"
            stage.mkdir(parents=True)
            card = directory / "task.json"
            card.write_text(json.dumps(self._make_minimal_task({
                "task_type": "bugfix", "flow": "standard-implementation",
                "phase": "verification", "complexity": "low", "research_docs": [],
                "depends_on": [], "rollback_plan": "Restore fixture", "subtasks": [],
                "acceptance_policy": "case-coverage-v1",
                "acceptance_criteria": ["AC-1: index uses the configured location", "AC-2: invalid YAML is refused"],
            })), encoding="utf-8")
            original = card.read_bytes()
            plan = stage / "plan.md"
            plan.write_text("# Exact input, action and outcome for each case\n", encoding="utf-8")
            target = root / "doc/architecture/sample.md"
            evidence_file = stage / "verification.json"
            evidence = {"task_key": "UI-9999", "stage_id": "stage1", "status": "passed",
                        "checked_revision": "fixture", "planned_checks": [
                            {"id": "CASE-1", "covers": ["AC-1"], "expected": "Default index path"},
                            {"id": "CASE-2", "covers": ["AC-1"], "expected": "Overridden index path"},
                        ], "checks": [{"cases": ["CASE-1"], "command": "test default",
                                       "result": "Matched default path", "exit_code": 0}]}
            evidence["snapshot_files"] = [
                {"path": p.relative_to(root).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                for p in (plan, target)
            ]

            def diagnose():
                evidence_file.write_text(json.dumps(evidence), encoding="utf-8")
                result = self._cli_at(root, "task", "diagnose", "UI-9999", "--json", "--brief")
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)["data"]

            incomplete = diagnose()
            self.assertFalse(incomplete["acceptance_plan_ready"])
            self.assertIn("AC-2", " ".join(incomplete["close_blockers"]))
            evidence["planned_checks"].append({"id": "CASE-3", "covers": ["AC-2"], "expected": "YAML refused"})
            incomplete = diagnose()
            self.assertTrue(incomplete["acceptance_plan_ready"])
            self.assertIn("CASE-2, CASE-3", " ".join(incomplete["close_blockers"]))
            refused = self._cli_at(root, "task", "close", "UI-9999", "--json")
            self.assertEqual(refused.returncode, 1)
            self.assertEqual(card.read_bytes(), original)
            evidence["checks"].append({"cases": ["CASE-2", "CASE-3"], "command": "test override and refusal",
                                       "result": "Path and refusal matched", "exit_code": 0})
            self.assertTrue(diagnose()["can_close"])

            child = directory / "subtasks/0001"
            child_stage = child / "stage1"
            child_stage.mkdir(parents=True)
            child_card = json.loads(original)
            child_card.update(task_key="UI-9999-0001", task_number="0001", phase="completed",
                              acceptance_criteria=["AC-1: child outcome"])
            (child / "task.json").write_text(json.dumps(child_card), encoding="utf-8")
            blocked_child = diagnose()
            self.assertIn("Subtask 0001: acceptance", " ".join(blocked_child["close_blockers"]))
            self.assertFalse(blocked_child["can_close"])
            child_plan = child_stage / "plan.md"
            child_plan.write_text("# Child case and its oracle\n", encoding="utf-8")
            child_evidence = {
                "task_key": "UI-9999-0001", "stage_id": "stage1", "status": "passed", "checked_revision": "fixture",
                "planned_checks": [{"id": "CASE-1", "covers": ["AC-1"], "expected": "Child outcome"}],
                "checks": [{"cases": ["CASE-1"], "command": "child test", "result": "Child verified", "exit_code": 0}],
                "snapshot_files": [{"path": child_plan.relative_to(root).as_posix(),
                                    "sha256": hashlib.sha256(child_plan.read_bytes()).hexdigest()}],
            }
            (child_stage / "verification.json").write_text(json.dumps(child_evidence), encoding="utf-8")
            self.assertTrue(diagnose()["can_close"])
            target.write_text("A newer version\n", encoding="utf-8")
            stale = diagnose()
            self.assertFalse(stale["can_close"])
            self.assertIn("snapshot is stale", " ".join(stale["close_blockers"]))
            self.assertEqual(card.read_bytes(), original)
            evidence["snapshot_files"][1]["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
            self.assertTrue(diagnose()["can_close"])
            closed = self._cli_at(root, "task", "close", "UI-9999", "--json")
            self.assertEqual(closed.returncode, 0, closed.stderr)
            self.assertEqual(json.loads(card.read_bytes())["phase"], "completed")

    def test_close_valid_task_and_brief_diagnosis(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tasks = root / "doc/tasks/UI-9999"
            (tasks / "stage1").mkdir(parents=True)
            parent = tasks / "task.json"
            parent.write_text(json.dumps(self._make_minimal_task({
                "task_type": "bugfix", "flow": "standard-implementation",
                "phase": "verification", "complexity": "low", "research_docs": [],
                "depends_on": [], "rollback_plan": "Restore fixture",
                "subtasks": [],
            })), encoding="utf-8")
            valid = self._cli_at(root, "task", "validate", "UI-9999")
            self.assertEqual(valid.returncode, 0, valid.stderr)
            brief = self._cli_at(root, "task", "diagnose", "UI-9999", "--json", "--brief")
            self.assertEqual(brief.returncode, 0, brief.stderr)
            result = json.loads(brief.stdout)["data"]
            self.assertNotIn("subtasks", result)
            self.assertTrue(result["can_close"])
            self.assertEqual(result["refs"]["task"], "doc/tasks/UI-9999/task.json")
            before = parent.read_bytes()
            preview = self._cli_at(root, "task", "close", "UI-9999", "--json", "--dry-run")
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertTrue(json.loads(preview.stdout)["data"]["would_close"])
            self.assertEqual(parent.read_bytes(), before)
            verdict = self._cli_at(root, "task", "close", "UI-9999", "--json")
            self.assertEqual(verdict.returncode, 0, verdict.stderr)
            self.assertEqual(json.loads(verdict.stdout)["data"]["phase"], "completed")
            self.assertEqual(json.loads(parent.read_text(encoding="utf-8"))["phase"], "completed")

    def test_task_config_queries_keep_working(self):
        flows = cli("task", "flows", "--type", "feature")
        self.assertEqual(flows.returncode, 0, flows.stderr)
        self.assertIn("standard-implementation", flows.stdout)

        prompt = cli("task", "type-prompt", "--type", "feature")
        self.assertEqual(prompt.returncode, 0, prompt.stderr)
        self.assertIn("Тип `feature`", prompt.stdout)

        flow_prompt = cli(
            "task", "flow-prompt", "--type", "feature",
            "--flow", "standard-implementation",
        )
        self.assertEqual(flow_prompt.returncode, 0, flow_prompt.stderr)
        self.assertIn("standard-implementation", flow_prompt.stdout)

    def _prepare_decompose_parent(self, root, task_key="UI-9999"):
        tdir = root / "doc" / "tasks" / task_key
        (tdir / "stage1").mkdir(parents=True)
        parent = tdir / "task.json"
        parent.write_text(json.dumps(self._make_minimal_task({
            "task_key": task_key,
            "task_number": task_key.split("-")[-1],
            "task_type": "refactor", "flow": "standard-implementation",
            "complexity": "medium", "research_docs": [],
            "depends_on": [], "rollback_plan": "Restore fixture",
            "phase": "verification", "subtasks": [],
        })), encoding="utf-8")
        return tdir, parent

    def test_decompose_rejects_invalid_package_before_writing(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = self._prepare_temp_root(temp)
        tdir, parent = self._prepare_decompose_parent(root)
        (tdir / "subtasks" / "0002").mkdir(parents=True)
        before = parent.read_bytes()

        conflict = self._cli_at(
            root, "task", "decompose", "UI-9999",
            "--subtask-id", "0001", "--subtask-title", "First",
            "--subtask-id", "0002", "--subtask-title", "Second",
        )
        self.assertNotEqual(conflict.returncode, 0)
        self.assertIn("already exists", conflict.stderr)
        self.assertFalse((tdir / "subtasks" / "0001").exists())
        self.assertEqual(parent.read_bytes(), before)
        self.assertFalse((tdir / ".arch-write-journal.json").exists())

        invalid = self._cli_at(
            root, "task", "decompose", "UI-9999",
            "--subtask-id", "0001", "--subtask-title", "First",
            "--subtask-id", "12", "--subtask-title", "Bad",
        )
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("four decimal digits", invalid.stderr)
        self.assertFalse((tdir / "subtasks" / "0001").exists())
        self.assertEqual(parent.read_bytes(), before)

    def test_decompose_writes_package_and_diagnose_reports_it(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = self._prepare_temp_root(temp)
        tdir, parent = self._prepare_decompose_parent(root)

        result = self._cli_at(
            root, "task", "decompose", "UI-9999",
            "--subtask-id", "0001", "--subtask-title", "First",
            "--subtask-id", "0002", "--subtask-title", "Second",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)["data"]
        self.assertEqual([entry["subtask_id"] for entry in payload["subtasks_created"]], ["0001", "0002"])
        declared = json.loads(parent.read_text(encoding="utf-8"))["subtasks"]
        self.assertEqual([entry["id"] for entry in declared], ["0001", "0002"])
        self.assertTrue((tdir / "subtasks" / "0001" / "task.json").exists())
        self.assertTrue((tdir / "subtasks" / "0002" / "stage1").is_dir())
        self.assertFalse((tdir / ".arch-write-journal.json").exists())

        diagnosis = self._cli_at(root, "task", "diagnose", "UI-9999", "--json")
        self.assertEqual(diagnosis.returncode, 0, diagnosis.stderr)
        data = json.loads(diagnosis.stdout)["data"]
        self.assertFalse(data["can_close"])
        self.assertEqual(data["subtask_count"], 2)

    def test_decompose_resumes_interrupted_write(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = self._prepare_temp_root(temp)
        tdir, parent = self._prepare_decompose_parent(root)
        planned = [
            {"id": "0001", "title": "First"},
            {"id": "0002", "title": "Second"},
            {"id": "0003", "title": "Third"},
        ]
        journal = tdir / ".arch-write-journal.json"
        journal.write_text(json.dumps({
            "schema_version": 1, "kind": "decompose",
            "task_key": "UI-9999", "subtasks": planned,
        }), encoding="utf-8")
        # 0001 was fully written, 0002 stopped between mkdir and task.json.
        first = tdir / "subtasks" / "0001"
        (first / "stage1").mkdir(parents=True)
        (first / "task.json").write_text(json.dumps({
            "task_key": "UI-9999-0001", "title": "First", "phase": "intake",
        }), encoding="utf-8")
        (tdir / "subtasks" / "0002" / "stage1").mkdir(parents=True)

        diagnosis = self._cli_at(root, "task", "diagnose", "UI-9999", "--json", "--brief")
        self.assertEqual(diagnosis.returncode, 0, diagnosis.stderr)
        data = json.loads(diagnosis.stdout)["data"]
        self.assertFalse(data["can_close"])
        self.assertEqual(data["incomplete_write"]["kind"], "decompose")
        self.assertIn("Incomplete decompose", data["close_blockers"][0])

        resumed = self._cli_at(
            root, "task", "decompose", "UI-9999",
            "--subtask-id", "0001", "--subtask-title", "First",
            "--subtask-id", "0002", "--subtask-title", "Second",
            "--subtask-id", "0003", "--subtask-title", "Third",
        )
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        self.assertTrue((tdir / "subtasks" / "0002" / "task.json").exists())
        self.assertTrue((tdir / "subtasks" / "0003" / "task.json").exists())
        declared = json.loads(parent.read_text(encoding="utf-8"))["subtasks"]
        self.assertEqual([entry["id"] for entry in declared], ["0001", "0002", "0003"])
        self.assertFalse(journal.exists())

    def test_decompose_refuses_different_package_while_journal_pending(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = self._prepare_temp_root(temp)
        tdir, parent = self._prepare_decompose_parent(root)
        journal = tdir / ".arch-write-journal.json"
        journal.write_text(json.dumps({
            "schema_version": 1, "kind": "decompose",
            "task_key": "UI-9999",
            "subtasks": [{"id": "0001", "title": "First"}],
        }), encoding="utf-8")
        before = parent.read_bytes()

        result = self._cli_at(
            root, "task", "decompose", "UI-9999",
            "--subtask-id", "0002", "--subtask-title", "Second",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("different package", result.stderr)
        self.assertFalse((tdir / "subtasks" / "0002").exists())
        self.assertEqual(parent.read_bytes(), before)
        self.assertTrue(journal.exists())

    def _snapshot_task_tree(self, directory):
        return {path.relative_to(directory).as_posix(): path.read_bytes() if path.is_file() else None
                for path in directory.rglob("*")}

    def test_invalid_decompose_journal_blocks_readiness_and_mutations(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, _ = self._prepare_decompose_parent(root)
            journal = tdir / ".arch-write-journal.json"
            for payload in ("{broken", "[]", '{"schema_version": 1, "kind": "decompose", "task_key": "UI-9999", "subtasks": []}'):
                with self.subTest(payload=payload):
                    journal.write_text(payload, encoding="utf-8")
                    before = self._snapshot_task_tree(tdir)
                    diagnosis = self._cli_at(root, "task", "diagnose", "UI-9999", "--json")
                    data = json.loads(diagnosis.stdout)["data"]
                    self.assertFalse(data["can_close"])
                    self.assertEqual(data["incomplete_write"]["state"], "invalid")
                    status = self._cli_at(root, "task", "status", "UI-9999", "--json")
                    self.assertEqual(json.loads(status.stdout)["data"]["incomplete_write"]["state"], "invalid")
                    scan = self._cli_at(root, "scan", "--scope", "tasks", "--brief")
                    self.assertEqual(scan.returncode, 1)
                    self.assertIn("Invalid write journal", scan.stderr)
                    preview = self._cli_at(root, "task", "close", "UI-9999", "--dry-run", "--json")
                    self.assertFalse(json.loads(preview.stdout)["data"]["would_close"])
                    for args in (("close", "UI-9999"), ("decompose", "UI-9999", "--subtask-id", "0001", "--subtask-title", "First"),
                                 ("subtask", "init", "UI-9999", "0001")):
                        self.assertNotEqual(self._cli_at(root, "task", *args).returncode, 0)
                        self.assertEqual(self._snapshot_task_tree(tdir), before)

    def test_resume_conflict_in_later_child_changes_nothing(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, _ = self._prepare_decompose_parent(root)
            (tdir / ".arch-write-journal.json").write_text(json.dumps({
                "schema_version": 1, "kind": "decompose", "task_key": "UI-9999", "subtasks": [
                    {"id": "0001", "title": "First"}, {"id": "0002", "title": "Second"},
                ],
            }), encoding="utf-8")
            child = tdir / "subtasks/0002/task.json"
            child.parent.mkdir(parents=True)
            child.write_text('{"task_key": "UI-9999-0002", "title": "Different"}', encoding="utf-8")
            before = self._snapshot_task_tree(tdir)
            result = self._cli_at(root, "task", "decompose", "UI-9999", "--subtask-id", "0001", "--subtask-title", "First",
                                  "--subtask-id", "0002", "--subtask-title", "Second")
            self.assertEqual(result.returncode, 5, result.stderr)
            self.assertEqual(self._snapshot_task_tree(tdir), before)

    def test_decompose_recovers_from_leftover_temps_and_committed_parent(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, parent = self._prepare_decompose_parent(root)
            journal = tdir / ".arch-write-journal.json"
            journal_bytes = json.dumps({"schema_version": 1, "kind": "decompose", "task_key": "UI-9999",
                                        "subtasks": [{"id": "0001", "title": "First"}]}).encode()
            journal.write_bytes(journal_bytes)
            child = tdir / "subtasks/0001"
            (child / "stage1").mkdir(parents=True)
            for temp in (child / ".task.json.aborted.tmp", tdir / ".task.json.parent.tmp",
                         tdir / "..arch-write-journal.json.aborted.tmp"):
                temp.write_text("{partial", encoding="utf-8")
            args = ("task", "decompose", "UI-9999", "--subtask-id", "0001", "--subtask-title", "First")
            result = self._cli_at(root, *args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(list(tdir.rglob("*.tmp")))
            self.assertTrue((child / "task.json").is_file())
            self.assertFalse(journal.exists())
            recorded = parent.read_bytes()
            journal.write_bytes(journal_bytes)
            self.assertEqual(self._cli_at(root, *args).returncode, 0)
            self.assertEqual(parent.read_bytes(), recorded)
            self.assertFalse(journal.exists())

            unpublished = tdir / "..arch-write-journal.json.unpublished.tmp"
            unpublished.write_text("{partial", encoding="utf-8")
            next_package = self._cli_at(root, "task", "decompose", "UI-9999", "--subtask-id", "0002",
                                        "--subtask-title", "Second")
            self.assertEqual(next_package.returncode, 0, next_package.stderr)
            self.assertFalse(unpublished.exists())
            self.assertEqual([row["id"] for row in json.loads(parent.read_bytes())["subtasks"]], ["0001", "0002"])

    def test_decompose_recovers_after_process_exits_during_atomic_write(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, parent = self._prepare_decompose_parent(root)
            child = tdir / "subtasks/0001"
            args = ("task", "decompose", "UI-9999", "--subtask-id", "0001", "--subtask-title", "First")
            # Stop at the actual replace boundary after the temp has been flushed.
            driver = """
import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv.pop(1))
from arch.cli.app import run
replace = os.replace
def stop_before_child(source, target):
    if Path(target).parent.name == '0001' and Path(target).name == 'task.json':
        os._exit(79)
    replace(source, target)
os.replace = stop_before_child
raise SystemExit(run(sys.argv[1:]))
"""
            before = parent.read_bytes()
            interrupted = subprocess.run([sys.executable, "-c", driver, str(ROOT / "doc/tools"),
                                          "--root", str(root), *args], capture_output=True, text=True)
            self.assertEqual(interrupted.returncode, 79, interrupted.stderr)
            self.assertEqual(parent.read_bytes(), before)
            self.assertTrue(list(child.glob(".task.json.*.tmp")))
            self.assertTrue((tdir / ".arch-write-journal.json").is_file())
            resumed = self._cli_at(root, *args)
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            self.assertTrue((child / "task.json").is_file())
            self.assertFalse(list(tdir.rglob("*.tmp")))
            self.assertFalse((tdir / ".arch-write-journal.json").exists())

    def test_task_writer_conflict_leaves_tree_unchanged(self):
        from arch.fs_atomic import lock_directory

        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, _ = self._prepare_decompose_parent(root)
            before = self._snapshot_task_tree(tdir)
            decompose = ("task", "decompose", "UI-9999", "--subtask-id", "0001", "--subtask-title", "First")
            with lock_directory(tdir):
                for args in (decompose, ("task", "close", "UI-9999", "--json"),
                             ("task", "subtask", "init", "UI-9999", "0002")):
                    refused = self._cli_at(root, *args)
                    self.assertEqual(refused.returncode, 5, refused.stderr)
                    self.assertIn("another task writer is active", refused.stderr)
                    self.assertEqual(self._snapshot_task_tree(tdir), before)
            result = self._cli_at(root, *decompose)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_task_validate_rejects_bad_task_id(self):
        import tempfile, json as _json
        from pathlib import Path
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = self._prepare_temp_root(temp)
        tdir = root / "doc" / "tasks" / "UI-9999"
        tdir.mkdir(parents=True)
        bad = self._make_minimal_task({"task_id": 123})
        (tdir / "task.json").write_text(_json.dumps(bad), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(CLI), "--root", str(root), "task", "validate", "UI-9999"],
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0, "bad task_id should fail")
        self.assertIn("task_id", result.stderr)

    def test_task_validate_rejects_bad_kind(self):
        import tempfile, json as _json
        from pathlib import Path
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = self._prepare_temp_root(temp)
        tdir = root / "doc" / "tasks" / "UI-9998"
        tdir.mkdir(parents=True)
        bad = self._make_minimal_task({"kind": 123})
        (tdir / "task.json").write_text(_json.dumps(bad), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(CLI), "--root", str(root), "task", "validate", "UI-9998"],
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0, "bad kind should fail")
        self.assertIn("kind", result.stderr)

    def test_task_validate_rejects_bad_scope(self):
        import tempfile, json as _json
        from pathlib import Path
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = self._prepare_temp_root(temp)
        tdir = root / "doc" / "tasks" / "UI-9997"
        tdir.mkdir(parents=True)
        bad = self._make_minimal_task({"scope": []})  # must be object, not array
        (tdir / "task.json").write_text(_json.dumps(bad), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(CLI), "--root", str(root), "task", "validate", "UI-9997"],
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0, "bad scope should fail")
        self.assertIn("scope", result.stderr)

    def test_task_validate_rejects_bad_risk(self):
        import tempfile, json as _json
        from pathlib import Path
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = self._prepare_temp_root(temp)
        tdir = root / "doc" / "tasks" / "UI-9996"
        tdir.mkdir(parents=True)
        bad = self._make_minimal_task({"risk": "extreme"})
        (tdir / "task.json").write_text(_json.dumps(bad), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(CLI), "--root", str(root), "task", "validate", "UI-9996"],
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0, "bad risk should fail")
        self.assertIn("risk", result.stderr)

    def test_task_validate_rejects_bad_authority(self):
        import tempfile, json as _json
        from pathlib import Path
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = self._prepare_temp_root(temp)
        tdir = root / "doc" / "tasks" / "UI-9995"
        tdir.mkdir(parents=True)
        bad = self._make_minimal_task({"authority": {"allowed": "not-an-array"}})
        (tdir / "task.json").write_text(_json.dumps(bad), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(CLI), "--root", str(root), "task", "validate", "UI-9995"],
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0, "bad authority should fail")
        self.assertIn("authority", result.stderr)

    def test_task_validate_accepts_traceability_fields(self):
        result = cli("task", "validate", "UI-0001")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((ROOT / "doc/tasks/UI-0001/task.json").read_text(encoding="utf-8"))
        self.assertIn("source", data)
        self.assertIn("attachments", data["source"])
        self.assertIn("comments", data["source"])
        self.assertIn("history", data["source"])
        self.assertIn("related_docs", data)
        self.assertIn("related_tests", data)
        self.assertIn("changed_files", data)
        self.assertIn("owner", data)
        self.assertIn("priority", data)
        self.assertIn("stage_history", data)

    def test_task_validate_rejects_bad_related_docs(self):
        import tempfile, json as _json
        from pathlib import Path
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = self._prepare_temp_root(temp)
        tdir = root / "doc" / "tasks" / "UI-9994"
        tdir.mkdir(parents=True)
        bad = self._make_minimal_task({"related_docs": ["not-a-valid-id", "lowercase-invalid"]})
        (tdir / "task.json").write_text(_json.dumps(bad), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(CLI), "--root", str(root), "task", "validate", "UI-9994"],
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0, "invalid related_docs should fail")
        self.assertIn("related_docs", result.stderr)

    def test_task_validate_rejects_bad_related_tests(self):
        import tempfile, json as _json
        from pathlib import Path
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = self._prepare_temp_root(temp)
        tdir = root / "doc" / "tasks" / "UI-9993"
        tdir.mkdir(parents=True)
        bad = self._make_minimal_task({"related_tests": [{"test_id": "T-1"}]})  # missing location
        (tdir / "task.json").write_text(_json.dumps(bad), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(CLI), "--root", str(root), "task", "validate", "UI-9993"],
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0, "related_tests missing location should fail")
        self.assertIn("related_tests", result.stderr)

    def test_task_validate_rejects_bad_changed_files(self):
        import tempfile, json as _json
        from pathlib import Path
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = self._prepare_temp_root(temp)
        tdir = root / "doc" / "tasks" / "UI-9992"
        tdir.mkdir(parents=True)
        bad = self._make_minimal_task({"changed_files": {"added": "not-an-array"}})
        (tdir / "task.json").write_text(_json.dumps(bad), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(CLI), "--root", str(root), "task", "validate", "UI-9992"],
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0, "changed_files.added not array should fail")
        self.assertIn("changed_files", result.stderr)

    def test_task_validate_accepts_new_fields(self):
        result = cli("task", "validate", "UI-0001")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((ROOT / "doc/tasks/UI-0001/task.json").read_text(encoding="utf-8"))
        self.assertIn("task_type", data)
        self.assertIn("subtasks", data)
        self.assertIn("depends_on", data)
        self.assertIn("phase", data)
        self.assertIn("rollback_plan", data)

    def test_task_validate_rejects_bad_task_type(self):
        import tempfile, json as _json
        from pathlib import Path
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = self._prepare_temp_root(temp)
        tdir = root / "doc" / "tasks" / "UI-9991"
        tdir.mkdir(parents=True)
        bad = self._make_minimal_task({"task_type": "invalid-type"})
        (tdir / "task.json").write_text(_json.dumps(bad), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(CLI), "--root", str(root), "task", "validate", "UI-9991"],
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0, "bad task_type should fail")
        self.assertIn("task_type", result.stderr)

    def test_task_validate_rejects_bad_phase(self):
        import tempfile, json as _json
        from pathlib import Path
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = self._prepare_temp_root(temp)
        tdir = root / "doc" / "tasks" / "UI-9990"
        tdir.mkdir(parents=True)
        bad = self._make_minimal_task({"phase": "invalid-phase"})
        (tdir / "task.json").write_text(_json.dumps(bad), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(CLI), "--root", str(root), "task", "validate", "UI-9990"],
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0, "bad phase should fail")
        self.assertIn("phase", result.stderr)

    def test_task_subtask_init_validate_status(self):
        import tempfile
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = self._prepare_temp_root(temp)
        parent = root / "doc" / "tasks" / "UI-0001"
        parent.mkdir(parents=True)
        (parent / "task.json").write_text("{}", encoding="utf-8")

        # Init a subtask under UI-0001 in the isolated root
        result = self._cli_at(root, "task", "subtask", "init", "UI-0001", "0001")
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)["data"]
        self.assertEqual(value["parent_task_key"], "UI-0001")
        self.assertEqual(value["subtask_id"], "0001")
        self.assertEqual(value["subtask_key"], "UI-0001-0001")

        # Validate the subtask
        result = self._cli_at(root, "task", "subtask", "validate", "UI-0001", "0001")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("is valid", result.stdout)

        # Status of the subtask
        result = self._cli_at(root, "task", "subtask", "status", "UI-0001", "0001")
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)["data"]
        self.assertEqual(value["subtask_key"], "UI-0001-0001")

    def test_task_subtask_init_rejects_collision(self):
        import tempfile
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = self._prepare_temp_root(temp)
        parent = root / "doc" / "tasks" / "UI-0004"
        parent.mkdir(parents=True)
        (parent / "task.json").write_text("{}", encoding="utf-8")

        # First create, then try again
        result = self._cli_at(root, "task", "subtask", "init", "UI-0004", "0001")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self._cli_at(root, "task", "subtask", "init", "UI-0004", "0001")
        self.assertNotEqual(result.returncode, 0, "subtask collision should fail")
        self.assertIn("already exists", result.stderr)

    def test_task_subtask_init_rejects_bad_id(self):
        result = cli("task", "subtask", "init", "UI-0001", "bad")
        self.assertNotEqual(result.returncode, 0, "bad subtask_id should fail")
        self.assertIn("four decimal digits", result.stderr)

    def test_task_validate_rejects_bad_subtasks(self):
        import tempfile, json as _json
        from pathlib import Path
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = self._prepare_temp_root(temp)
        tdir = root / "doc" / "tasks" / "UI-9989"
        tdir.mkdir(parents=True)
        bad = self._make_minimal_task({"subtasks": [{"id": "0001"}]})  # missing title, status, path
        (tdir / "task.json").write_text(_json.dumps(bad), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(CLI), "--root", str(root), "task", "validate", "UI-9989"],
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0, "bad subtasks should fail")
        self.assertIn("subtasks", result.stderr)

    def test_task_validate_rejects_bad_depends_on(self):
        import tempfile, json as _json
        from pathlib import Path
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = self._prepare_temp_root(temp)
        tdir = root / "doc" / "tasks" / "UI-9988"
        tdir.mkdir(parents=True)
        bad = self._make_minimal_task({"depends_on": "not-an-array"})
        (tdir / "task.json").write_text(_json.dumps(bad), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(CLI), "--root", str(root), "task", "validate", "UI-9988"],
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0, "bad depends_on should fail")
        self.assertIn("depends_on", result.stderr)

    def test_docs_related_command(self):
        result = cli("docs", "related", "SYS-simple-factory", "--depth", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)["data"]
        self.assertEqual(value["root"], "SYS-simple-factory")
        self.assertEqual(value["max_depth"], 1)
        ids = [d["id"] for d in value["documents"]]
        self.assertIn("SYS-simple-factory", ids)
        self.assertIn("DOM-task-intake", ids)
        self.assertIn("DOM-task-lifecycle", ids)
        # Depth 1 should not include depth-2 docs
        self.assertNotIn("CAP-task-intake", ids)

    def test_docs_related_unknown_id(self):
        result = cli("docs", "related", "NONEXISTENT-ID")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not found", result.stderr)

    def test_implemented_field_in_index(self):
        result = cli("index", "check")
        self.assertEqual(result.returncode, 0, result.stderr)
        index = json.loads((ROOT / "doc/architecture" / "index.json").read_text(encoding="utf-8"))
        for doc in index["documents"]:
            self.assertIn("implemented", doc, f"Doc {doc['id']} missing implemented field")
            self.assertIsInstance(doc["implemented"], bool)

    def test_body_validation_all_types(self):
        from arch.body_validation import get_supported_body_types
        types = get_supported_body_types()
        self.assertIn("decision", types)
        self.assertIn("flow", types)
        self.assertIn("entity", types)
        self.assertIn("component-view", types)
        self.assertIn("rule-set", types)
        self.assertIn("glossary", types)
        self.assertIn("domain", types)
        self.assertIn("system", types)
        self.assertIn("capability", types)
        self.assertIn("capability-spec", types)
        self.assertIn("data-view", types)
        self.assertIn("quality-attributes", types)
        self.assertIn("security-view", types)
        self.assertIn("system-context", types)
        self.assertIn("constraints-risks", types)

    def test_installed_package_reports_metadata_version_and_runtime_resources(self):
        from arch import __version__

        with tempfile.TemporaryDirectory() as dirname:
            workspace = Path(dirname)
            source = workspace / "source"
            shutil.copytree(
                ROOT, source,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc",
                                              ".pytest_cache", "build", "dist", "*.egg-info"),
            )
            dist = workspace / "dist"
            env = {**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                   "PYTHONDONTWRITEBYTECODE": "1"}
            build = subprocess.run(
                [sys.executable, "-m", "pip", "wheel", "--no-build-isolation",
                 "--no-deps", "-w", str(dist), str(source)],
                text=True, capture_output=True, check=False, env=env,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            wheels = sorted(dist.glob("arch_cli-*.whl"))
            self.assertEqual(len(wheels), 1, wheels)

            target = workspace / "target"
            install = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--no-index", "--no-deps",
                 "--target", str(target), str(wheels[0])],
                text=True, capture_output=True, check=False, env=env,
            )
            self.assertEqual(install.returncode, 0, install.stderr)
            installed_env = {**env, "PYTHONPATH": str(target)}

            metadata = subprocess.run(
                [sys.executable, "-c",
                 "import importlib.metadata as m; print(m.version('arch-cli'))"],
                cwd=workspace, text=True, capture_output=True, check=False, env=installed_env,
            )
            self.assertEqual(metadata.returncode, 0, metadata.stderr)
            self.assertEqual(metadata.stdout.strip(), __version__)

            console = target / "bin" / "arch"
            self.assertTrue(console.is_file(), console)
            version = subprocess.run(
                [str(console), "--version"], cwd=workspace,
                text=True, capture_output=True, check=False, env=installed_env,
            )
            self.assertEqual(version.returncode, 0, version.stderr)
            self.assertEqual(version.stdout.strip(), f"arch {__version__}")

            fixture = workspace / "project"
            self._paths_fixture(fixture, "doc", "index.json")
            listing = subprocess.run(
                [str(console), "--root", str(fixture), "list", "--id", "DOC_SAMPLE", "--json"],
                cwd=workspace, text=True, capture_output=True, check=False, env=installed_env,
            )
            self.assertEqual(listing.returncode, 0, listing.stderr)
            payload = json.loads(listing.stdout)["data"]
            self.assertEqual([item["id"] for item in payload], ["DOC_SAMPLE"])

    def test_index_gate_rejects_stale_index_without_writing(self):
        with tempfile.TemporaryDirectory() as dirname:
            workspace = Path(dirname)
            project = workspace / "project"
            shutil.copytree(
                ROOT, project,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc",
                                              ".pytest_cache", "build", "dist", "*.egg-info"),
            )
            local_config = project / "kilo.jsonc"
            if not local_config.exists() and (project / "kilo.jsonc!!!").exists():
                shutil.copy2(project / "kilo.jsonc!!!", local_config)
            index = project / "doc/architecture/index.json"
            original = index.read_bytes()
            data = json.loads(original)
            data["documents"][0]["title"] += " stale"
            index.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
            stale = index.read_bytes()
            before = self._tree_digest(project)
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

            rejected = subprocess.run(
                ["bash", "doc/tests/run.sh", "--index-only"], cwd=project,
                text=True, capture_output=True, check=False, env=env,
            )
            self.assertEqual(rejected.returncode, 1, rejected.stderr)
            self.assertIn("stale", (rejected.stdout + rejected.stderr).lower())
            self.assertEqual(index.read_bytes(), stale)
            self.assertEqual(self._tree_digest(project), before)

            index.write_bytes(original)
            accepted = subprocess.run(
                ["bash", "doc/tests/run.sh", "--index-only"], cwd=project,
                text=True, capture_output=True, check=False, env=env,
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)

    def test_index_gate_detects_environment_dependent_rebuild(self):
        with tempfile.TemporaryDirectory() as dirname:
            project = Path(dirname) / "project"
            shutil.copytree(
                ROOT, project,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc",
                                              ".pytest_cache", "build", "dist", "*.egg-info"),
            )
            local_config = project / "kilo.jsonc"
            if not local_config.exists() and (project / "kilo.jsonc!!!").exists():
                shutil.copy2(project / "kilo.jsonc!!!", local_config)
            store = project / "doc/tools/arch/store.py"
            text = store.read_text(encoding="utf-8")
            marker = '        records.sort(key=lambda x: x["id"])\n'
            self.assertIn(marker, text)
            store.write_text(text.replace(
                marker,
                marker +
                '        if records and __import__("os").environ.get("PYTHONHASHSEED") '
                'not in (None, "0"):\n'
                '            records[0]["summary"] += " [seed]"\n',
                1,
            ), encoding="utf-8")
            before = self._tree_digest(project)
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

            rejected = subprocess.run(
                ["bash", "doc/tests/run.sh", "--index-only"], cwd=project,
                text=True, capture_output=True, check=False, env=env,
            )
            self.assertEqual(rejected.returncode, 1, rejected.stdout + rejected.stderr)
            self.assertIn("PYTHONHASHSEED=12345", rejected.stderr)
            self.assertEqual(self._tree_digest(project), before)

    def test_in_copy_gate_tolerates_missing_local_config_without_touching_checkout(self):
        with tempfile.TemporaryDirectory() as dirname:
            project = Path(dirname) / "project"
            shutil.copytree(
                ROOT, project,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc",
                                              ".pytest_cache", "build", "dist", "*.egg-info"),
            )
            local_config = project / "kilo.jsonc"
            renamed = project / "kilo.jsonc!!!"
            if local_config.exists():
                if renamed.exists():
                    renamed.unlink()
                local_config.rename(renamed)
            self.assertFalse(local_config.exists())
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

            result = subprocess.run(
                ["bash", "doc/tests/run.sh", "--in-copy", "--index-only"], cwd=project,
                text=True, capture_output=True, check=False, env=env,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("restored kilo.jsonc", result.stderr)
            self.assertFalse(local_config.exists())
            self.assertTrue(renamed.is_file())

    def test_evidence_accepts_subtask_key(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            child = root / "doc/tasks/UI-9999/subtasks/0001"
            stage = child / "stage1"
            stage.mkdir(parents=True)
            (child / "task.json").write_text(json.dumps(self._make_minimal_task({
                "task_key": "UI-9999-0001", "task_number": "0001",
                "task_type": "scaffold", "flow": "minimal-scaffold",
                "phase": "verification", "acceptance_policy": "case-coverage-v1",
                "acceptance_criteria": ["AC-1: child observable check"],
            })), encoding="utf-8")
            (stage / "plan.md").write_text("# Child plan\n", encoding="utf-8")
            evidence = stage / "verification.json"
            evidence.write_text(json.dumps({
                "task_key": "UI-9999-0001", "stage_id": "stage1", "checks": [],
                "planned_checks": [{"id": "CASE-1", "covers": ["AC-1"], "expected": "OK"}],
            }), encoding="utf-8")
            (root / "input.txt").write_text("before", encoding="utf-8")
            capture = ("task", "evidence", "UI-9999-0001", "--file", "input.txt", "--case", "CASE-1")

            recorded = self._cli_at(root, *capture, "--run", sys.executable, "-c", "pass")
            self.assertEqual(recorded.returncode, 0, recorded.stderr)
            data = json.loads(evidence.read_bytes())
            self.assertEqual(data["status"], "passed")
            self.assertEqual([check["cases"] for check in data["checks"]], [["CASE-1"]])
            checked = self._cli_at(root, "task", "evidence", "UI-9999-0001", "--check")
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertTrue(json.loads(checked.stdout)["data"]["current"])

    def _tree_digest(self, root):
        digest = {}
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            digest[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        return digest


if __name__ == "__main__":
    unittest.main()
