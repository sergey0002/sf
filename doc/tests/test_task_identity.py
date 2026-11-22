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
            if not flows:
                self.assertIsNone(config["default_flow"])
                continue
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

    def _write_registry(self, root, tasks):
        registry = root / "doc/config/task-registry.json"
        registry.write_text(
            json.dumps({"schema_version": 1, "tasks": tasks}), encoding="utf-8"
        )
        return registry

    def test_task_key_next_reads_json_registry_without_scanning_tasks(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            self._write_registry(root, [
                {"task_key": "UI-0007", "task_number": "0007", "source": "ui",
                 "title": None, "created_at": None},
                {"task_key": "UI-0009", "task_number": "0009", "source": "ui",
                 "title": None, "created_at": None},
            ])
            (root / "doc/tasks/UI-0500").mkdir(parents=True)
            result = self._cli_at(root, "task-key", "--source", "ui", "--next")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["data"]["task_key"], "UI-0010")

            jira = self._cli_at(root, "task-key", "--source", "jira", "--next")
            self.assertNotEqual(jira.returncode, 0)
            both = self._cli_at(
                root, "task-key", "--source", "ui", "--next", "--number", "0042"
            )
            self.assertNotEqual(both.returncode, 0)

    def test_task_new_allocates_creates_and_registers_in_one_command(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            (root / "doc/tasks").mkdir(exist_ok=True)
            self._write_registry(root, [
                {"task_key": "UI-0007", "task_number": "0007", "source": "ui",
                 "title": None, "created_at": None},
            ])
            result = self._cli_at(root, "task", "new", "--title", "First", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)["data"]
            self.assertEqual(data["task_key"], "UI-0008")
            task = json.loads((root / data["task_json"]).read_text(encoding="utf-8"))
            self.assertEqual(task["title"], "First")
            self.assertEqual(task["task_number"], "0008")
            registry = json.loads(
                (root / "doc/config/task-registry.json").read_text(encoding="utf-8")
            )
            self.assertEqual([entry["task_key"] for entry in registry["tasks"]],
                             ["UI-0007", "UI-0008"])
            self.assertEqual(registry["tasks"][-1]["title"], "First")

            second = self._cli_at(root, "task", "new", "--json")
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(json.loads(second.stdout)["data"]["task_key"], "UI-0009")

    def test_task_new_stops_on_malformed_registry_without_writing(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            (root / "doc/tasks").mkdir(exist_ok=True)
            self._write_registry(root, [
                {"task_key": "UI-0007", "task_number": "0007", "source": "ui"},
                {"task_key": "UI-0007", "task_number": "0007", "source": "ui"},
            ])
            result = self._cli_at(root, "task", "new", "--json")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list((root / "doc/tasks").iterdir()), [])

    def test_task_init_registers_key_and_registry_init_bootstraps(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            (root / "doc/config/task-registry.json").unlink()
            init = self._cli_at(root, "task", "registry", "init")
            self.assertEqual(init.returncode, 0, init.stderr)
            (root / "doc/tasks").mkdir(exist_ok=True)
            result = self._cli_at(root, "task", "init", "UI-0042")
            self.assertEqual(result.returncode, 0, result.stderr)
            registry = self._cli_at(root, "task", "registry", "--json")
            self.assertEqual(registry.returncode, 0, registry.stderr)
            payload = json.loads(registry.stdout)["data"]
            self.assertEqual([entry["task_key"] for entry in payload["tasks"]], ["UI-0042"])

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
        self.assertIn("arch task new", create)
        self.assertIn("не читайте и не редактируйте `doc/config/task-registry.json`", create.lower())
        self.assertIn("arch task-key --source ui --next", create)
        self.assertIn("не выполняет задачу", create)
        self.assertIn("Хотите, приступлю?", create)
        self.assertIn("four digits", resume)

    def test_architecture_documents_record_source_key_contract(self):
        glossary = (ROOT / "doc/architecture/glossary.md").read_text(encoding="utf-8")
        task_entity = (ROOT / "doc/architecture/domains/task-lifecycle/entities/task-input.md").read_text(encoding="utf-8")
        constraints = (ROOT / "doc/architecture/system/constraints-risks.md").read_text(encoding="utf-8")
        self.assertIn("ввод пользователя использует `UI-1234`", glossary)
        self.assertIn("Ключи Jira — чистый номер", task_entity)
        self.assertIn("UI-реестр ведёт CLI", constraints)
        registry_doc = (ROOT / "doc/architecture/system/task-number-registry.md").read_text(encoding="utf-8")
        self.assertIn("doc/config/task-registry.json", registry_doc)
        self.assertIn("ведётся **только CLI**", registry_doc)
        manifest = (ROOT / "Манифест агентной software factory.md").read_text(encoding="utf-8")
        self.assertIn("source.type: ui", manifest)
        self.assertIn("Jira — номер без префикса", manifest)
        self.assertIn("<source-prefix>-2045", manifest)

    def test_environment_docs_cli_and_index(self):
        result = cli("validate")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = cli("index", "check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_task_registry_add_reconciles_existing_card(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            (root / "doc/tasks").mkdir(exist_ok=True)
            self._write_registry(root, [])
            created = self._cli_at(root, "task", "new", "--title", "Reconcile", "--json")
            self.assertEqual(created.returncode, 0, created.stderr)
            key = json.loads(created.stdout)["data"]["task_key"]
            self._write_registry(root, [])
            added = self._cli_at(root, "task", "registry", "add", key, "--json")
            self.assertEqual(added.returncode, 0, added.stderr)
            self.assertEqual(json.loads(added.stdout)["data"]["entry"]["title"], "Reconcile")
            missing = self._cli_at(root, "task", "registry", "add", "UI-0999", "--json")
            self.assertNotEqual(missing.returncode, 0)

    def _make_card(self, root, key, number, title="Card"):
        directory = root / "doc/tasks" / key
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "task.json").write_text(
            json.dumps({"task_key": key, "task_number": number, "title": title}),
            encoding="utf-8",
        )
        return directory

    def test_registry_check_detects_drift_without_writing(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            self._write_registry(root, [])
            self._make_card(root, "UI-0500", "0500")
            before = (root / "doc/config/task-registry.json").read_bytes()
            result = self._cli_at(root, "task", "registry", "check", "--json")
            self.assertEqual(result.returncode, 1)
            drift = json.loads(result.stdout)["data"]
            self.assertEqual(drift["missing_in_registry"], ["UI-0500"])
            self.assertEqual((root / "doc/config/task-registry.json").read_bytes(), before)

    def test_registry_sync_builds_and_prunes_from_directories(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            self._write_registry(root, [{
                "task_key": "UI-0001", "task_number": "0001", "source": "ui",
                "title": None, "created_at": None,
            }])
            self._make_card(root, "UI-0500", "0500", title="Built")
            sync = self._cli_at(root, "task", "registry", "sync", "--json")
            self.assertEqual(sync.returncode, 0, sync.stderr)
            payload = json.loads(sync.stdout)["data"]
            self.assertEqual(payload["added"], ["UI-0500"])
            self.assertEqual(payload["removed"], [])
            self.assertFalse(payload["ok"], "stale entry remains until --prune")
            registry = json.loads(
                (root / "doc/config/task-registry.json").read_text(encoding="utf-8")
            )
            titles = {entry["task_key"]: entry["title"] for entry in registry["tasks"]}
            self.assertEqual(titles["UI-0500"], "Built")

            renamed = root / "doc/tasks/UI-0501"
            (root / "doc/tasks/UI-0500").rename(renamed)
            card = json.loads((renamed / "task.json").read_text(encoding="utf-8"))
            card.update(task_key="UI-0501", task_number="0501")
            (renamed / "task.json").write_text(json.dumps(card), encoding="utf-8")
            self.assertEqual(self._cli_at(root, "task", "registry", "check").returncode, 1)
            prune = self._cli_at(root, "task", "registry", "sync", "--prune", "--json")
            self.assertEqual(prune.returncode, 0, prune.stderr)
            payload = json.loads(prune.stdout)["data"]
            self.assertIn("UI-0500", payload["removed"])
            self.assertIn("UI-0501", payload["added"])

    def test_registry_sync_refuses_number_mismatch(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            self._write_registry(root, [{
                "task_key": "UI-0500", "task_number": "0500", "source": "ui",
                "title": None, "created_at": None,
            }])
            self._make_card(root, "UI-0500", "0999")
            check = self._cli_at(root, "task", "registry", "check", "--json")
            self.assertEqual(check.returncode, 1)
            self.assertEqual(json.loads(check.stdout)["data"]["number_mismatch"][0]["task_key"],
                             "UI-0500")
            sync = self._cli_at(root, "task", "registry", "sync", "--json")
            self.assertNotEqual(sync.returncode, 0)

    def test_task_init_creates_directory_and_task_json(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            (root / "doc/tasks").mkdir(exist_ok=True)
            result = self._cli_at(root, "task", "init", "UI-9999")
            self.assertEqual(result.returncode, 0, result.stderr)
            task_dir = root / "doc/tasks/UI-9999"
            self.assertTrue(task_dir.is_dir(), "task directory should be created")
            self.assertTrue((task_dir / "task.json").exists(), "task.json should be created")
            self.assertTrue((task_dir / "stage1").is_dir(), "stage1 directory should be created")
            data = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
            self.assertEqual(data["task_key"], "UI-9999")
            self.assertEqual(data["task_number"], "9999")
            self.assertEqual(data["source"]["type"], "ui")
            self.assertFalse((task_dir / "task.md").exists(), "task.md must not be created")
            registry = json.loads(
                (root / "doc/config/task-registry.json").read_text(encoding="utf-8")
            )
            self.assertIn("UI-9999", [entry["task_key"] for entry in registry["tasks"]])

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
            "{schemas}/bodies/{slug}.json", "{config}/paths.yaml", "{config}/task-registry.json",
            "{task_conf}/types/{type}/{slug}.yaml", "{task_conf}/types/{type}/prompt.md",
            "{task_conf}/types/{type}/flows/{flow}/{slug}.yaml",
            "{task_conf}/types/{type}/flows/{flow}/prompt.md",
            "{task_conf}/types/{type}/flows/{flow}/stepsprompt/{slug}.md",
            "{tasks}/{task_key}/task.json", "{tasks}/{task_key}/stage{stage}/{slug}.md",
            "{tasks}/{task_key}/stage{stage}/{slug}.json",
            "{tasks}/{task_key}/state.json", "{tasks}/{task_key}/events.jsonl",
            "{tasks}/{task_key}/subtasks/{subtask_id}/task.json",
            "{tasks}/{task_key}/subtasks/{subtask_id}/state.json",
            "{tasks}/{task_key}/subtasks/{subtask_id}/events.jsonl",
        ])
        config["project"]["document_types"] = ["note"]
        config_path = root / roots["config"] / "paths.yaml"
        config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
        (root / roots["config"] / "task-registry.json").write_text(
            json.dumps({"schema_version": 1, "tasks": []}), encoding="utf-8"
        )
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
        (root / "doc" / "tasks").mkdir()
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

    def test_docs_only_close_runs_structural_gates_on_current_project(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            config, _ = self._paths_fixture(root, "handbook", "index.json")
            directory = root / "handbook/tasks/UI-9999"
            stage = directory / "stage1"
            stage.mkdir(parents=True)
            card = directory / "task.json"
            card.write_text(json.dumps(self._make_minimal_task({
                "task_type": "docs", "flow": "docs-only", "phase": "verification",
                "complexity": "low", "research_docs": [], "depends_on": [], "subtasks": [],
                "rollback_plan": "Restore fixture", "acceptance_policy": "case-coverage-v1",
                "acceptance_criteria": ["AC-1: sample has the expected body"],
            })), encoding="utf-8")
            plan = stage / "plan.md"
            plan.write_text("# Verify the sample document body\n", encoding="utf-8")
            verification = stage / "verification.json"
            verification.write_text(json.dumps({
                "task_key": "UI-9999", "stage_id": "stage1", "status": "not_run", "checks": [],
                "planned_checks": [{"id": "CASE-1", "covers": ["AC-1"], "expected": "Example body"}],
            }), encoding="utf-8")

            def run(*args):
                return self._cli_at(root, "--config", str(config), *args)

            original = card.read_bytes()

            def assert_blocked(reason):
                before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
                diagnosis = run("task", "diagnose", "UI-9999", "--json", "--brief")
                self.assertEqual(diagnosis.returncode, 0, diagnosis.stderr)
                data = json.loads(diagnosis.stdout)["data"]
                self.assertFalse(data["can_close"])
                preview = run("task", "close", "UI-9999", "--json", "--dry-run")
                self.assertEqual(preview.returncode, 0, preview.stderr)
                preview_data = json.loads(preview.stdout)["data"]
                self.assertFalse(preview_data["would_close"])
                self.assertIn(reason, " ".join(preview_data["blockers"]))
                self.assertEqual(data["close_blockers"], preview_data["blockers"][:3])
                refused = run("task", "close", "UI-9999", "--json")
                self.assertEqual(refused.returncode, 1, refused.stderr)
                self.assertEqual([entry["message"] for entry in json.loads(refused.stderr)["errors"]],
                                 preview_data["blockers"])
                self.assertEqual(before, {p: p.read_bytes() for p in root.rglob("*") if p.is_file()})

            built = run("index", "build")
            self.assertEqual(built.returncode, 0, built.stderr)
            assert_blocked("CASE-1")
            target = "handbook/architecture/sample.md"
            failed = run("task", "evidence", "UI-9999", "--file", target, "--case", "CASE-1",
                         "--run", sys.executable, "-c", "raise SystemExit(1)")
            self.assertEqual(failed.returncode, 1, failed.stderr)
            failed_evidence = json.loads(verification.read_bytes())
            self.assertEqual(failed_evidence["status"], "failed")
            failed_evidence["status"] = "passed"
            verification.write_text(json.dumps(failed_evidence), encoding="utf-8")
            assert_blocked("CASE-1")
            recorded = run("task", "evidence", "UI-9999", "--file", target, "--case", "CASE-1",
                           "--run", sys.executable, "-c",
                           f"from pathlib import Path; assert Path({target!r}).read_text().endswith('Example\\n')")
            self.assertEqual(recorded.returncode, 0, recorded.stderr)
            recorded_bytes = verification.read_bytes()
            original_plan = plan.read_bytes()
            plan.write_bytes(original_plan + b"Changed after evidence\n")
            assert_blocked("snapshot is stale")
            plan.write_bytes(original_plan)

            foreign = root / "handbook/foreign.txt"
            foreign.write_text("Undeclared file\n", encoding="utf-8")
            assert_blocked("docs-only paths-check:")
            foreign.unlink()

            index = root / "handbook/architecture/index.json"
            original_index = index.read_bytes()
            index.write_text("{}\n", encoding="utf-8")
            forged = json.loads(recorded_bytes)
            forged["checks"].append({"command": "true", "exit_code": 0,
                                      "result": "claimed architecture validation", "cases": []})
            verification.write_text(json.dumps(forged), encoding="utf-8")
            assert_blocked("docs-only validate:")
            index.write_bytes(original_index)
            verification.write_bytes(recorded_bytes)
            self.assertEqual(card.read_bytes(), original)

            migrated = run("task", "migrate", "UI-9999")
            self.assertEqual(migrated.returncode, 0, migrated.stderr)
            refused = run("task", "event", "UI-9999", "--id", "bypass", "--type", "phase.changed",
                          "--expected-revision", "1", "--phase", "completed")
            self.assertNotEqual(refused.returncode, 0, refused.stderr)
            self.assertIn("via arch task close", refused.stderr)
            closed = run("task", "close", "UI-9999", "--json")
            self.assertEqual(closed.returncode, 0, closed.stderr)
            self.assertEqual(json.loads(closed.stdout)["data"]["phase"], "completed")

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

    def test_flow_selection_reports_unknown_missing_and_conflict(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            (root / "doc/tasks").mkdir(exist_ok=True)
            unknown = self._cli_at(root, "task", "select-flow", "--type", "bugfix",
                                   "--fact", "not_a_fact=true")
            self.assertEqual(unknown.returncode, 1, unknown.stderr)
            self.assertIn("UNKNOWN-FACT", unknown.stderr)

            missing = self._cli_at(root, "task", "select-flow", "--type", "bugfix",
                                   "--fact", "symptom_confirmed=true")
            self.assertEqual(missing.returncode, 1, missing.stderr)
            self.assertIn("MISSING-FACT", missing.stderr)
            self.assertIn("investigation_needed", missing.stderr)

            selection = root / "doc/config/task-conf/types/bugfix/flow-selection.yaml"
            data = yaml.safe_load(selection.read_text(encoding="utf-8"))
            data["rules"] = [
                {"id": "rule.one", "when": {"symptom_confirmed": True},
                 "flow": "minimal-scaffold"},
                {"id": "rule.two", "when": {"symptom_confirmed": True},
                 "flow": "standard-implementation"},
            ]
            selection.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
            conflict = self._cli_at(root, "task", "select-flow", "--type", "bugfix",
                                    "--fact", "symptom_confirmed=true")
            self.assertEqual(conflict.returncode, 5, conflict.stderr)
            self.assertIn("CONFLICT", conflict.stderr)
            self.assertIn("rule.one", conflict.stderr)
            self.assertIn("rule.two", conflict.stderr)

            docs = self._cli_at(root, "task", "select-flow", "--type", "docs")
            self.assertEqual(docs.returncode, 0, docs.stderr)
            self.assertEqual(json.loads(docs.stdout)["data"]["flow"], "docs-only")

    def test_bugfix_flow_returns_from_verify_to_fix_and_rejects_stale_events(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            directory = root / "doc/tasks/UI-9999"
            (directory / "stage1").mkdir(parents=True)
            card = directory / "task.json"
            card.write_text(json.dumps(self._make_minimal_task({
                "kind": "bugfix", "task_type": "bugfix", "flow": "standard-implementation",
                "phase": "verification", "complexity": "low", "research_docs": [],
                "depends_on": [], "rollback_plan": "Restore fixture", "subtasks": [],
            })), encoding="utf-8")
            migrated = self._cli_at(root, "task", "migrate", "UI-9999")
            self.assertEqual(migrated.returncode, 0, migrated.stderr)

            def advance(event, revision, event_id=None):
                args = ["task", "advance", "UI-9999", "--event", event,
                        "--expected-revision", str(revision)]
                if event_id:
                    args += ["--id", event_id]
                result = self._cli_at(root, *args)
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)["data"]

            for event, revision in (
                ("context.ready", 1), ("reproduction.recorded", 2), ("plan.ready", 3),
                ("fix.applied", 4), ("review.passed", 5), ("architecture.synced", 6),
            ):
                advance(event, revision)

            diagnosis = self._cli_at(root, "task", "diagnose", "UI-9999", "--json")
            state = json.loads(diagnosis.stdout)["data"]
            self.assertEqual(state["flow_state"], "verify")
            self.assertEqual({item["event"] for item in state["available_transitions"]},
                             {"checks.failed", "checks.passed"})

            failed = advance("checks.failed", 7, "verify-failed")
            self.assertEqual(failed["flow_state"], "fix")
            self.assertEqual(failed["transition"]["to"], "fix")
            state_bytes = (directory / "state.json").read_bytes()

            unknown = self._cli_at(root, "task", "advance", "UI-9999", "--event", "unknown.event",
                                   "--expected-revision", "8")
            self.assertNotEqual(unknown.returncode, 0)
            self.assertIn("UNKNOWN-EVENT", unknown.stderr)
            self.assertEqual((directory / "state.json").read_bytes(), state_bytes)

            stale = self._cli_at(root, "task", "advance", "UI-9999", "--event", "fix.applied",
                                 "--expected-revision", "7")
            self.assertEqual(stale.returncode, 5, stale.stderr)
            self.assertIn("revision conflict", stale.stderr)
            self.assertEqual((directory / "state.json").read_bytes(), state_bytes)

            repeated = advance("checks.failed", 7, "verify-failed")
            self.assertTrue(repeated["record"]["duplicate"])
            self.assertEqual((directory / "state.json").read_bytes(), state_bytes)

            self.assertEqual(advance("fix.applied", 8)["flow_state"], "review-implementation")
            self.assertEqual(advance("review.passed", 9)["flow_state"], "architecture-sync")
            self.assertEqual(advance("architecture.synced", 10)["flow_state"], "verify")
            passed = advance("checks.passed", 11)
            self.assertEqual(passed["flow_state"], "close")
            self.assertTrue(passed["flow_terminal"])

    def test_docs_only_flow_short_path_without_children(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            directory = root / "doc/tasks/UI-9999"
            (directory / "stage1").mkdir(parents=True)
            card = directory / "task.json"
            card.write_text(json.dumps(self._make_minimal_task({
                "kind": "docs", "task_type": "docs", "flow": "docs-only",
                "phase": "verification", "complexity": "low", "research_docs": [],
                "depends_on": [], "rollback_plan": "Restore fixture", "subtasks": [],
            })), encoding="utf-8")
            self.assertEqual(self._cli_at(root, "task", "migrate", "UI-9999").returncode, 0)

            def advance(event, revision):
                result = self._cli_at(root, "task", "advance", "UI-9999", "--event", event,
                                      "--expected-revision", str(revision))
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)["data"]

            self.assertEqual(advance("context.ready", 1)["flow_state"], "change")
            self.assertEqual(advance("change.ready", 2)["flow_state"], "validate")
            self.assertEqual(advance("checks.failed", 3)["flow_state"], "change")
            self.assertEqual(advance("change.ready", 4)["flow_state"], "validate")
            terminal = advance("checks.passed", 5)
            self.assertEqual(terminal["flow_state"], "close")
            self.assertTrue(terminal["flow_terminal"])
            self.assertEqual(terminal["subtask_count"], 0)

            closed = self._cli_at(root, "task", "close", "UI-9999", "--json")
            self.assertEqual(closed.returncode, 0, closed.stderr)
            self.assertEqual(json.loads(closed.stdout)["data"]["phase"], "completed")

    def test_subtask_dependencies_compute_ready_blocked_and_cycles(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, _ = self._prepare_decompose_parent(root)
            created = self._cli_at(
                root, "task", "decompose", "UI-9999",
                "--subtask-id", "0001", "--subtask-title", "First",
                "--subtask-id", "0002", "--subtask-title", "Second",
                "--subtask-id", "0003", "--subtask-title", "Third",
                "--subtask-depends-on", "0002=0001",
                "--subtask-depends-on", "0003=0002",
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            parent = json.loads((tdir / "task.json").read_text(encoding="utf-8"))
            self.assertEqual(parent["subtasks"][1]["depends_on"], ["0001"])
            child = json.loads((tdir / "subtasks/0002/task.json").read_text(encoding="utf-8"))
            self.assertEqual(child["depends_on"], ["UI-9999-0001"])

            def rows():
                result = self._cli_at(root, "task", "diagnose", "UI-9999", "--json")
                self.assertEqual(result.returncode, 0, result.stderr)
                return {row["subtask_id"]: row for row in json.loads(result.stdout)["data"]["subtasks"]}

            first = rows()
            self.assertTrue(first["0001"]["ready"])
            self.assertFalse(first["0002"]["ready"])
            self.assertEqual(first["0002"]["blocked_by"], ["0001"])
            self.assertEqual(first["0003"]["blocked_by"], ["0002"])

            child_one = tdir / "subtasks/0001/task.json"
            data = json.loads(child_one.read_text(encoding="utf-8"))
            data["phase"] = "completed"
            child_one.write_text(json.dumps(data), encoding="utf-8")
            second = rows()
            self.assertTrue(second["0002"]["ready"])
            self.assertFalse(second["0003"]["ready"])
            self.assertEqual(second["0003"]["blocked_by"], ["0002"])

            cycle_tdir, _ = self._prepare_decompose_parent(root, "UI-9998")
            cycle = self._cli_at(
                root, "task", "decompose", "UI-9998",
                "--subtask-id", "0001", "--subtask-title", "First",
                "--subtask-id", "0002", "--subtask-title", "Second",
                "--subtask-depends-on", "0001=0002",
                "--subtask-depends-on", "0002=0001",
            )
            self.assertEqual(cycle.returncode, 5, cycle.stderr)
            self.assertIn("dependency cycle", cycle.stderr)
            self.assertFalse((cycle_tdir / "subtasks/0001").exists())
            self.assertFalse((cycle_tdir / "subtasks/0002").exists())

            unknown = self._cli_at(
                root, "task", "decompose", "UI-9998",
                "--subtask-id", "0001", "--subtask-title", "First",
                "--subtask-depends-on", "0001=0009",
            )
            self.assertEqual(unknown.returncode, 1, unknown.stderr)
            self.assertIn("unknown subtask", unknown.stderr)
            self.assertFalse((cycle_tdir / "subtasks/0001").exists())

    def test_decompose_uses_agent_chosen_shape_not_scaffold(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, _ = self._prepare_decompose_parent(root)
            default = self._cli_at(
                root, "task", "decompose", "UI-9999",
                "--subtask-id", "0001", "--subtask-title", "Default shape",
            )
            self.assertEqual(default.returncode, 0, default.stderr)
            child = json.loads((tdir / "subtasks/0001/task.json").read_text(encoding="utf-8"))
            self.assertEqual(child["task_type"], "subtask")
            self.assertIsNone(child["flow"])
            self.assertEqual(child["complexity"], "medium")
            self.assertEqual(
                self._cli_at(root, "task", "subtask", "validate", "UI-9999", "0001").returncode,
                0,
            )

            chosen = self._cli_at(
                root, "task", "decompose", "UI-9999",
                "--subtask-id", "0002", "--subtask-title", "Chosen shape",
                "--subtask-type", "0002=bugfix",
                "--subtask-flow", "0002=standard-implementation",
                "--subtask-complexity", "0002=low",
                "--subtask-estimate", "0002=3",
            )
            self.assertEqual(chosen.returncode, 0, chosen.stderr)
            child = json.loads((tdir / "subtasks/0002/task.json").read_text(encoding="utf-8"))
            self.assertEqual(child["task_type"], "bugfix")
            self.assertEqual(child["flow"], "standard-implementation")
            self.assertEqual(child["complexity"], "low")
            self.assertEqual(child["estimate_hours"], 3)
            parent = json.loads((tdir / "task.json").read_text(encoding="utf-8"))
            record = {row["id"]: row for row in parent["subtasks"]}["0002"]
            self.assertEqual(record["task_type"], "bugfix")
            self.assertEqual(record["estimate_hours"], 3)

            invalid = self._cli_at(
                root, "task", "decompose", "UI-9999",
                "--subtask-id", "0003", "--subtask-title", "Bad flow",
                "--subtask-type", "0003=feature",
                "--subtask-flow", "0003=minimal-scaffold",
            )
            self.assertEqual(invalid.returncode, 1, invalid.stderr)
            self.assertIn("not allowed", invalid.stderr)
            self.assertFalse((tdir / "subtasks/0003").exists())

    def test_estimate_hours_must_be_positive_number(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, card = self._prepare_decompose_parent(root)
            for value in (0, -1, "many"):
                task = json.loads(card.read_bytes())
                task["estimate_hours"] = value
                card.write_text(json.dumps(task), encoding="utf-8")
                result = self._cli_at(root, "task", "validate", "UI-9999")
                self.assertNotEqual(result.returncode, 0, value)
                self.assertIn("estimate_hours", result.stderr)
            task = json.loads(card.read_bytes())
            task["estimate_hours"] = 6
            card.write_text(json.dumps(task), encoding="utf-8")
            self.assertEqual(self._cli_at(root, "task", "validate", "UI-9999").returncode, 0)

    def _write_acceptance_plan(
        self, tdir, card, plan_text, *, complexity="medium", estimate_hours=None,
    ):
        task = json.loads(card.read_bytes())
        task.update(
            acceptance_policy="case-coverage-v1",
            acceptance_criteria=["AC-1: observable result"],
            complexity=complexity,
        )
        if estimate_hours is None:
            task.pop("estimate_hours", None)
        else:
            task["estimate_hours"] = estimate_hours
        card.write_text(json.dumps(task), encoding="utf-8")
        stage = tdir / "stage1"
        stage.mkdir(exist_ok=True)
        (stage / "plan.md").write_text(plan_text, encoding="utf-8")
        (stage / "verification.json").write_text(json.dumps({
            "task_key": "UI-9999", "stage_id": "stage1", "checks": [],
            "planned_checks": [{"id": "CASE-1", "covers": ["AC-1"], "expected": "OK"}],
        }), encoding="utf-8")

    def _plan_ready(self, root):
        result = self._cli_at(root, "task", "diagnose", "UI-9999", "--json", "--brief")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)["data"]

    MICRO_PLAN = (
        "<!-- plan-tier: micro -->\n# UI-9999: small change\n\n"
        "## Приёмка\n\n| CASE | AC | Дано | Действие | Ожидание |\n"
        "|---|---|---|---|---|\n| CASE-1 | AC-1 | fixture | command | exit 0 |\n\n"
        "## Проверка\n\n```bash\narch validate --brief\n```\n"
    )

    def test_plan_tier_must_match_complexity(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, card = self._prepare_decompose_parent(root)
            self._write_acceptance_plan(tdir, card, self.MICRO_PLAN, complexity="high")
            data = self._plan_ready(root)
            self.assertFalse(data["acceptance_plan_ready"])
            self.assertIn("not allowed for complexity", " ".join(data["close_blockers"]))

            self._write_acceptance_plan(
                tdir, card,
                "<!-- plan-tier: full -->\n# Full\n\n## Цель\n\nx\n\n## Правила проекта\n\nx\n\n"
                "## Решения\n\nx\n\n## Риск и откат\n\nx\n\n## Приёмка\n\nx\n\n"
                "## Оценка\n\nx\n\n## Проверка\n\nx\n",
                complexity="high",
            )
            self.assertTrue(self._plan_ready(root)["acceptance_plan_ready"])

    def test_plan_tier_marker_required_with_estimate(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, card = self._prepare_decompose_parent(root)
            plan = (
                "# UI-9999\n\n## Цель\n\nx\n\n## Приёмка\n\nx\n\n## Оценка\n\nx\n\n"
                "## Проверка\n\nx\n"
            )
            self._write_acceptance_plan(tdir, card, plan, complexity="medium", estimate_hours=4)
            data = self._plan_ready(root)
            self.assertFalse(data["acceptance_plan_ready"])
            self.assertIn("plan-tier", " ".join(data["close_blockers"]))

            self._write_acceptance_plan(
                tdir, card, "<!-- plan-tier: standard -->\n" + plan,
                complexity="medium", estimate_hours=4,
            )
            self.assertTrue(self._plan_ready(root)["acceptance_plan_ready"])

    def test_micro_plan_requires_sections_and_respects_line_limit(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, card = self._prepare_decompose_parent(root)
            self._write_acceptance_plan(
                tdir, card, self.MICRO_PLAN, complexity="low", estimate_hours=1,
            )
            self.assertTrue(self._plan_ready(root)["acceptance_plan_ready"])

            oversized = self.MICRO_PLAN + "\n" + "\n".join(f"line {i}" for i in range(70))
            self._write_acceptance_plan(
                tdir, card, oversized, complexity="low", estimate_hours=1,
            )
            data = self._plan_ready(root)
            self.assertFalse(data["acceptance_plan_ready"])
            self.assertIn("limit is 60", " ".join(data["close_blockers"]))

            missing = "<!-- plan-tier: micro -->\n# UI-9999\n\n## Приёмка\n\nx\n"
            self._write_acceptance_plan(
                tdir, card, missing, complexity="low", estimate_hours=1,
            )
            data = self._plan_ready(root)
            self.assertFalse(data["acceptance_plan_ready"])
            self.assertIn("requires sections", " ".join(data["close_blockers"]))

    def test_legacy_plan_without_tier_stays_ready(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, card = self._prepare_decompose_parent(root)
            self._write_acceptance_plan(tdir, card, "# Test plan\n", complexity="medium")
            self.assertTrue(self._plan_ready(root)["acceptance_plan_ready"])

    def test_scan_task_conf_reports_unreachable_and_ambiguous_flow(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            (root / "doc/tasks").mkdir(exist_ok=True)
            flow_path = (root / "doc/config/task-conf/types/bugfix/flows/"
                         "standard-implementation/config.yaml")
            flow = yaml.safe_load(flow_path.read_text(encoding="utf-8"))
            flow["states"].append("orphan")
            flow_path.write_text(yaml.safe_dump(flow, allow_unicode=True), encoding="utf-8")
            unreachable = self._cli_at(root, "scan", "--scope", "task-conf", "--brief")
            self.assertEqual(unreachable.returncode, 1)
            self.assertIn("unreachable", unreachable.stderr)

            flow["states"].remove("orphan")
            flow["transitions"].append({
                "id": "bug.ambiguous", "from": "verify", "event": "checks.failed", "to": "fix",
            })
            flow_path.write_text(yaml.safe_dump(flow, allow_unicode=True), encoding="utf-8")
            ambiguous = self._cli_at(root, "scan", "--scope", "task-conf", "--brief")
            self.assertEqual(ambiguous.returncode, 1)
            self.assertIn("ambiguous transitions", ambiguous.stderr)

    def test_scan_requires_step_consistency_and_selection_table(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            (root / "doc/tasks").mkdir(exist_ok=True)
            selection = root / "doc/config/task-conf/types/feature/flow-selection.yaml"
            selection.unlink()
            missing = self._cli_at(root, "scan", "--scope", "task-conf", "--brief")
            self.assertEqual(missing.returncode, 1)
            self.assertIn("flow-selection.yaml", missing.stderr)

            selection.write_text(
                "schema_version: flow-selection-1\ntype: feature\nversion: 1\n"
                "facts: {}\nrules:\n  - id: feature.default\n    fallback: true\n"
                "    flow: standard-implementation\n",
                encoding="utf-8",
            )
            flow_path = (root / "doc/config/task-conf/types/bugfix/flows/"
                         "standard-implementation/config.yaml")
            flow = yaml.safe_load(flow_path.read_text(encoding="utf-8"))
            for transition in flow["transitions"]:
                if transition["id"] == "bug.fix.applied":
                    transition["to"] = "architecture-sync"
                if transition["id"] == "bug.review.passed":
                    transition["to"] = "close"
            flow_path.write_text(yaml.safe_dump(flow, allow_unicode=True), encoding="utf-8")
            reordered = self._cli_at(root, "scan", "--scope", "task-conf", "--brief")
            self.assertEqual(reordered.returncode, 1)
            self.assertIn("skips steps", reordered.stderr)
            self.assertIn("missing transition from step 'fix'", reordered.stderr)

    def test_advance_reports_unsupported_flow_for_legacy_template(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            (root / "doc/tasks").mkdir(exist_ok=True)
            directory = root / "doc/tasks/UI-9999"
            (directory / "stage1").mkdir(parents=True)
            (directory / "task.json").write_text(json.dumps(self._make_minimal_task({
                "task_type": "feature", "flow": "standard-implementation",
                "phase": "verification", "complexity": "medium", "research_docs": [],
                "depends_on": [], "rollback_plan": "Restore fixture",
                "implementation_plan": ["legacy"], "subtasks": [],
            })), encoding="utf-8")
            self.assertEqual(self._cli_at(root, "task", "migrate", "UI-9999").returncode, 0)
            state_before = (directory / "state.json").read_bytes()
            result = self._cli_at(root, "task", "advance", "UI-9999",
                                  "--event", "context.ready", "--expected-revision", "1")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("UNSUPPORTED-FLOW", result.stderr)
            self.assertIn("flow-1", result.stderr)
            self.assertEqual((directory / "state.json").read_bytes(), state_before)

    def test_close_syncs_subtask_status_and_stage_history(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, parent = self._prepare_decompose_parent(root)
            created = self._cli_at(
                root, "task", "decompose", "UI-9999",
                "--subtask-id", "0001", "--subtask-title", "First",
                "--subtask-id", "0002", "--subtask-title", "Second",
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            for sub_id in ("0001", "0002"):
                child = tdir / "subtasks" / sub_id / "task.json"
                data = json.loads(child.read_text(encoding="utf-8"))
                data["phase"] = "completed"
                child.write_text(json.dumps(data), encoding="utf-8")

            closed = self._cli_at(root, "task", "close", "UI-9999", "--json")
            self.assertEqual(closed.returncode, 0, closed.stderr)
            card = json.loads(parent.read_text(encoding="utf-8"))
            self.assertEqual(card["phase"], "completed")
            self.assertEqual([entry["status"] for entry in card["subtasks"]],
                             ["completed", "completed"])
            self.assertEqual(card["stage_history"],
                             [{"stage_id": "stage1", "status": "completed"}])

    def test_stale_evidence_blocks_close_without_case_policy(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, parent = self._prepare_decompose_parent(root)
            stage = tdir / "stage1"
            (stage / "plan.md").write_text("# plan\n", encoding="utf-8")
            (root / "input.txt").write_text("before", encoding="utf-8")

            def write_evidence():
                entries = []
                for name in ("doc/tasks/UI-9999/stage1/plan.md", "input.txt"):
                    entries.append({"path": name,
                                    "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest()})
                (stage / "verification.json").write_text(json.dumps({
                    "task_key": "UI-9999", "stage_id": "stage1", "status": "passed",
                    "checked_revision": "sha256:fixture", "checks": [],
                    "snapshot_files": entries,
                }), encoding="utf-8")

            write_evidence()
            self.assertTrue(json.loads(
                self._cli_at(root, "task", "diagnose", "UI-9999", "--json").stdout
            )["data"]["can_close"])
            before = parent.read_bytes()
            (root / "input.txt").write_text("after", encoding="utf-8")
            refused = self._cli_at(root, "task", "close", "UI-9999", "--json")
            self.assertEqual(refused.returncode, 1, refused.stderr)
            self.assertIn("snapshot is stale: input.txt", refused.stderr)
            self.assertEqual(parent.read_bytes(), before)

            write_evidence()
            closed = self._cli_at(root, "task", "close", "UI-9999", "--json")
            self.assertEqual(closed.returncode, 0, closed.stderr)

    def test_decompose_and_subtask_status_support_json(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, _ = self._prepare_decompose_parent(root)
            created = self._cli_at(
                root, "task", "decompose", "UI-9999",
                "--subtask-id", "0001", "--subtask-title", "First", "--json",
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            payload = json.loads(created.stdout)["data"]
            self.assertEqual(payload["subtasks_created"][0]["subtask_id"], "0001")
            status = self._cli_at(
                root, "task", "subtask", "status", "UI-9999", "0001", "--json"
            )
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertEqual(json.loads(status.stdout)["data"]["phase"], "intake")
            validated = self._cli_at(
                root, "task", "subtask", "validate", "UI-9999", "0001", "--json"
            )
            self.assertEqual(validated.returncode, 0, validated.stderr)
            self.assertTrue(json.loads(validated.stdout)["data"]["ok"])

    def test_workspace_preflight_reports_declared_and_module_overlap(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, card = self._prepare_decompose_parent(root)
            task = json.loads(card.read_bytes())
            task["scope"]["allowed_files_modules"] = ["doc/tools/arch/"]
            task["scope"]["write_files"] = ["doc/tools/arch/task_ops.py"]
            task["changed_files"] = {
                "added": [], "modified": ["doc/tools/arch/task_ops.py"], "deleted": [],
            }
            card.write_text(json.dumps(task), encoding="utf-8")
            git = ["git", "-C", str(root), "-c", "user.email=t@example.invalid",
                   "-c", "user.name=test"]
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run([*git, "add", "-A"], check=True)
            subprocess.run([*git, "commit", "-qm", "base"], check=True)

            clean = self._cli_at(root, "task", "workspace", "UI-9999", "--json")
            self.assertEqual(clean.returncode, 0, clean.stderr)
            self.assertEqual(json.loads(clean.stdout)["data"]["preflight"]["status"], "clean")

            target = root / "doc/tools/arch/task_ops.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("changed\n", encoding="utf-8")
            overlap = self._cli_at(root, "task", "workspace", "UI-9999", "--json")
            self.assertEqual(overlap.returncode, 0, overlap.stderr)
            preflight = json.loads(overlap.stdout)["data"]["preflight"]
            self.assertEqual(preflight["status"], "isolate")
            self.assertIn("doc/tools/arch/task_ops.py", preflight["intersections"])
            self.assertEqual(preflight["foreign_changes"], [])
            diagnosis = json.loads(
                self._cli_at(root, "task", "diagnose", "UI-9999", "--json").stdout
            )["data"]
            self.assertEqual(diagnosis["write_scope"]["status"], "isolate")

            target.unlink()
            other = root / "doc/tools/arch/other.py"
            other.write_text("other\n", encoding="utf-8")
            review = self._cli_at(root, "task", "workspace", "UI-9999", "--json")
            self.assertEqual(review.returncode, 0, review.stderr)
            preflight = json.loads(review.stdout)["data"]["preflight"]
            self.assertEqual(preflight["status"], "review")
            self.assertIn("doc/tools/arch/other.py", preflight["module_overlaps"])

    def test_evidence_freshness_is_separate_from_historical_closure(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, card = self._prepare_decompose_parent(root)
            stage = tdir / "stage1"
            (stage / "plan.md").write_text("# plan\n", encoding="utf-8")
            (root / "input.txt").write_text("before", encoding="utf-8")
            task = json.loads(card.read_bytes())
            task.update(
                acceptance_policy="case-coverage-v1",
                acceptance_criteria=["AC-1: observable outcome"],
                phase="completed",
            )
            card.write_text(json.dumps(task), encoding="utf-8")
            entries = [
                {"path": name, "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest()}
                for name in ("doc/tasks/UI-9999/stage1/plan.md", "input.txt")
            ]
            (stage / "verification.json").write_text(json.dumps({
                "task_key": "UI-9999", "stage_id": "stage1", "status": "passed",
                "checked_revision": "sha256:fixture",
                "planned_checks": [{"id": "CASE-1", "covers": ["AC-1"], "expected": "Outcome"}],
                "checks": [{"cases": ["CASE-1"], "command": "test", "exit_code": 0, "result": "OK"}],
                "snapshot_files": entries,
            }), encoding="utf-8")

            current = json.loads(
                self._cli_at(root, "task", "diagnose", "UI-9999", "--json").stdout
            )["data"]
            self.assertEqual(current["evidence_freshness"]["status"], "current")
            checked = self._cli_at(root, "task", "evidence", "UI-9999", "--check")
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertEqual(json.loads(checked.stdout)["data"]["status"], "current")

            (root / "input.txt").write_text("after", encoding="utf-8")
            stale = json.loads(
                self._cli_at(root, "task", "diagnose", "UI-9999", "--json").stdout
            )["data"]
            self.assertEqual(stale["phase"], "completed")
            self.assertEqual(stale["evidence_freshness"]["status"], "stale")
            self.assertEqual(stale["evidence_freshness"]["stale_files"], ["input.txt"])
            self.assertIn("historical closure", stale["evidence_freshness"]["note"])
            checked = self._cli_at(root, "task", "evidence", "UI-9999", "--check")
            self.assertEqual(checked.returncode, 1)
            payload = json.loads(checked.stdout)["data"]
            self.assertFalse(payload["current"])
            self.assertEqual(payload["status"], "stale")
            self.assertEqual(payload["stale_files"], ["input.txt"])

            doctor = json.loads(
                self._cli_at(root, "task", "doctor", "UI-9999", "--json").stdout
            )["data"]
            self.assertEqual(doctor["phase"], "completed")
            self.assertEqual(doctor["evidence_freshness"]["status"], "stale")
            self.assertIn("preflight", doctor)

    def test_baseline_records_command_and_refuses_changed_inputs(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, card = self._prepare_decompose_parent(root)
            (root / "input.txt").write_text("before", encoding="utf-8")
            original = card.read_bytes()
            result = self._cli_at(
                root, "task", "baseline", "UI-9999", "--file", "input.txt",
                "--run", sys.executable, "-c", "print('baseline')",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)["data"]
            self.assertEqual(payload["exit_code"], 0)
            baseline = tdir / "stage1/baseline.json"
            record = json.loads(baseline.read_text(encoding="utf-8"))
            self.assertEqual(record["command"].split()[0], sys.executable)
            self.assertEqual(record["exit_code"], 0)
            self.assertEqual(record["files"][0]["path"], "input.txt")
            self.assertEqual(card.read_bytes(), original)

            refused = self._cli_at(
                root, "task", "baseline", "UI-9999", "--file", "input.txt",
                "--run", sys.executable, "-c",
                "open('input.txt', 'w', encoding='utf-8').write('changed')",
            )
            self.assertEqual(refused.returncode, 1)
            self.assertIn("changed during the run", refused.stderr)
            self.assertEqual(json.loads(baseline.read_text(encoding="utf-8")), record)

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

    def test_resume_refuses_added_options_for_already_written_child(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = self._prepare_temp_root(temp)
            tdir, parent = self._prepare_decompose_parent(root)
            original = parent.read_bytes()
            args = ("task", "decompose", "UI-9999", "--subtask-id", "0001", "--subtask-title", "First",
                    "--subtask-id", "0002", "--subtask-title", "Second", "--subtask-type", "0001=bugfix")
            first_run = self._cli_at(root, *args)
            self.assertEqual(first_run.returncode, 0, first_run.stderr)
            first = tdir / "subtasks/0001/task.json"
            saved_child = first.read_bytes()
            second = tdir / "subtasks/0002"
            (second / "task.json").unlink()
            (second / "stage1").rmdir()
            second.rmdir()
            parent.write_bytes(original)
            journal = tdir / ".arch-write-journal.json"
            journal.write_text(json.dumps({
                "schema_version": 1, "kind": "decompose", "task_key": "UI-9999",
                "subtasks": [
                    {"id": "0001", "title": "First", "task_type": "bugfix", "complexity": "medium"},
                    {"id": "0002", "title": "Second"},
                ],
            }), encoding="utf-8")
            before = self._snapshot_task_tree(tdir)

            for option in (("--subtask-depends-on", "0001=0002"),
                           ("--subtask-depends-on", "0001=0003"),
                           ("--subtask-estimate", "0001=3"),
                           ("--subtask-flow", "0001=standard-implementation")):
                with self.subTest(option=option):
                    refused = self._cli_at(root, *args, *option)
                    self.assertEqual(refused.returncode, 5, refused.stderr)
                    self.assertIn("different package", refused.stderr)
                    self.assertEqual(self._snapshot_task_tree(tdir), before)

            resumed = self._cli_at(root, *args)
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            self.assertEqual(first.read_bytes(), saved_child)
            self.assertTrue((second / "task.json").is_file())
            self.assertFalse(journal.exists())
            declared = json.loads(parent.read_bytes())["subtasks"]
            self.assertEqual([row["id"] for row in declared], ["0001", "0002"])
            for row in declared:
                self.assertNotIn("depends_on", row)
                self.assertNotIn("estimate_hours", row)

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

    def _record_fixture(self, root, task_key="UI-9999", overrides=None):
        directory = root / "doc" / "tasks" / task_key
        (directory / "stage1").mkdir(parents=True, exist_ok=True)
        card = directory / "task.json"
        task = self._make_minimal_task({
            "task_key": task_key,
            "task_number": task_key.split("-")[-1],
            "task_type": "bugfix", "flow": "standard-implementation",
            "complexity": "low", "research_docs": [], "depends_on": [],
            "rollback_plan": "Restore fixture", "phase": "verification", "subtasks": [],
            **(overrides or {}),
        })
        card.write_text(json.dumps(task), encoding="utf-8")
        return directory, card, task

    def _migrate_record(self, root, task_key="UI-9999"):
        result = self._cli_at(root, "task", "migrate", task_key)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)["data"]

    def test_versioned_record_migration_preserves_intent_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            self._paths_fixture(root, "doc", "index.json")
            directory, card, original = self._record_fixture(root)
            before = card.read_bytes()
            self.assertEqual(self._cli_at(root, "task", "validate", "UI-9999").returncode, 0)

            preview = self._cli_at(root, "task", "migrate", "UI-9999", "--dry-run")
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertTrue(json.loads(preview.stdout)["data"]["migrated"])
            self.assertEqual(card.read_bytes(), before)
            self.assertFalse((directory / "state.json").exists())
            self.assertFalse((directory / "events.jsonl").exists())

            first = self._migrate_record(root)
            self.assertTrue(first["migrated"])
            migrated = json.loads(card.read_text(encoding="utf-8"))
            for field in ("title", "intent", "scope", "acceptance_criteria", "authority", "source"):
                self.assertEqual(migrated[field], original[field])
            self.assertEqual(migrated["intent_digest"], first["intent_digest"])
            self.assertEqual(migrated["record_version"], 1)
            state = json.loads((directory / "state.json").read_text(encoding="utf-8"))
            events = (directory / "events.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(events), 1)
            self.assertEqual(json.loads(events[0])["type"], "record.migrated")
            self.assertEqual(state["revision"], 1)
            self.assertEqual(state["phase"], "verification")
            self.assertEqual(self._cli_at(root, "task", "validate", "UI-9999").returncode, 0)
            diagnosis = json.loads(
                self._cli_at(root, "task", "diagnose", "UI-9999", "--json").stdout
            )["data"]
            self.assertEqual(diagnosis["phase"], "verification")
            self.assertEqual(diagnosis["record"]["state"], "ok")

            second = self._migrate_record(root)
            self.assertFalse(second["migrated"])
            self.assertEqual(second["revision"], 1)
            self.assertEqual(second["intent_digest"], first["intent_digest"])
            self.assertEqual(
                (directory / "events.jsonl").read_text(encoding="utf-8").splitlines(), events
            )
            self.assertEqual(json.loads(card.read_text(encoding="utf-8"))["intent_digest"],
                             first["intent_digest"])

    def test_versioned_event_is_idempotent_and_rejects_revision_conflict(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            self._paths_fixture(root, "doc", "index.json")
            directory, _, _ = self._record_fixture(root)
            self._migrate_record(root)

            first = self._cli_at(
                root, "task", "event", "UI-9999", "--id", "event-1",
                "--type", "phase.changed", "--expected-revision", "1", "--phase", "execution",
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            payload = json.loads(first.stdout)["data"]
            self.assertFalse(payload["duplicate"])
            self.assertEqual(payload["revision"], 2)
            state_after = (directory / "state.json").read_bytes()
            events_after = (directory / "events.jsonl").read_bytes()

            duplicate = self._cli_at(
                root, "task", "event", "UI-9999", "--id", "event-1",
                "--type", "phase.changed", "--expected-revision", "1", "--phase", "execution",
            )
            self.assertEqual(duplicate.returncode, 0, duplicate.stderr)
            self.assertTrue(json.loads(duplicate.stdout)["data"]["duplicate"])
            self.assertEqual((directory / "state.json").read_bytes(), state_after)
            self.assertEqual((directory / "events.jsonl").read_bytes(), events_after)

            same_id = self._cli_at(
                root, "task", "event", "UI-9999", "--id", "event-1",
                "--type", "phase.changed", "--expected-revision", "2", "--phase", "planning",
            )
            self.assertEqual(same_id.returncode, 5)
            self.assertEqual((directory / "state.json").read_bytes(), state_after)
            self.assertEqual((directory / "events.jsonl").read_bytes(), events_after)

            stale = self._cli_at(
                root, "task", "event", "UI-9999", "--id", "event-2",
                "--type", "phase.changed", "--expected-revision", "1", "--phase", "planning",
            )
            self.assertEqual(stale.returncode, 5)
            self.assertIn("revision conflict", stale.stderr)
            self.assertEqual((directory / "state.json").read_bytes(), state_after)
            self.assertEqual((directory / "events.jsonl").read_bytes(), events_after)

            diagnosis = json.loads(
                self._cli_at(root, "task", "diagnose", "UI-9999", "--json").stdout
            )["data"]
            self.assertEqual(diagnosis["phase"], "execution")

    def test_versioned_replay_restores_state_and_rejects_corrupt_journal(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            self._paths_fixture(root, "doc", "index.json")
            directory, _, _ = self._record_fixture(root)
            self._migrate_record(root)
            migrated_state = (directory / "state.json").read_bytes()

            appended = self._cli_at(
                root, "task", "event", "UI-9999", "--id", "event-1",
                "--type", "phase.changed", "--expected-revision", "1", "--phase", "execution",
            )
            self.assertEqual(appended.returncode, 0, appended.stderr)
            current_state = (directory / "state.json").read_bytes()

            (directory / "state.json").write_bytes(migrated_state)
            stale = json.loads(
                self._cli_at(root, "task", "diagnose", "UI-9999", "--json").stdout
            )["data"]
            self.assertEqual(stale["record"]["state"], "stale")
            self.assertEqual(stale["phase"], "verification")

            restored = self._cli_at(root, "task", "replay", "UI-9999")
            self.assertEqual(restored.returncode, 0, restored.stderr)
            replay = json.loads(restored.stdout)["data"]
            self.assertTrue(replay["restored"])
            self.assertEqual(replay["revision"], 2)
            self.assertEqual(replay["phase"], "execution")
            self.assertEqual((directory / "state.json").read_bytes(), current_state)

            events = (directory / "events.jsonl").read_text(encoding="utf-8")
            (directory / "events.jsonl").write_text(
                events.replace('"execution"', '"planning"', 1), encoding="utf-8"
            )
            corrupt = self._cli_at(root, "task", "replay", "UI-9999")
            self.assertEqual(corrupt.returncode, 1)
            self.assertIn("digest does not match", corrupt.stderr)
            self.assertEqual((directory / "state.json").read_bytes(), current_state)

    def test_versioned_intent_is_immutable_and_close_writes_event(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            self._paths_fixture(root, "doc", "index.json")
            directory, card, _ = self._record_fixture(root)
            self._migrate_record(root)
            migrated_bytes = card.read_bytes()

            tampered = json.loads(migrated_bytes)
            tampered["title"] = "rewritten intent"
            card.write_text(json.dumps(tampered), encoding="utf-8")
            refused = self._cli_at(root, "task", "validate", "UI-9999")
            self.assertEqual(refused.returncode, 1)
            self.assertIn("intent fields changed", refused.stderr)
            card.write_bytes(migrated_bytes)

            closed = self._cli_at(root, "task", "close", "UI-9999", "--json")
            self.assertEqual(closed.returncode, 0, closed.stderr)
            state = json.loads((directory / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["phase"], "completed")
            self.assertEqual(state["revision"], 2)
            self.assertEqual(json.loads(card.read_text(encoding="utf-8"))["phase"], "verification")
            events = [
                json.loads(line)
                for line in (directory / "events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([event["type"] for event in events],
                             ["record.migrated", "phase.changed"])

            again = self._cli_at(root, "task", "close", "UI-9999", "--json")
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertTrue(json.loads(again.stdout)["data"]["already_closed"])
            self.assertEqual(
                len((directory / "events.jsonl").read_text(encoding="utf-8").splitlines()), 2
            )

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

    def test_in_copy_gate_leaves_checkout_unchanged(self):
        with tempfile.TemporaryDirectory() as dirname:
            project = Path(dirname) / "project"
            shutil.copytree(
                ROOT, project,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc",
                                              ".pytest_cache", "build", "dist", "*.egg-info"),
            )
            sentinel = project / "checkout-sentinel.txt"
            sentinel.write_text("unchanged", encoding="utf-8")
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

            result = subprocess.run(
                ["bash", "doc/tests/run.sh", "--in-copy", "--index-only"], cwd=project,
                text=True, capture_output=True, check=False, env=env,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "unchanged")

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
