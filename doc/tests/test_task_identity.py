import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

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

    def _cli_at(self, root, *args):
        return subprocess.run(
            [sys.executable, str(CLI), "--root", str(root), *args],
            text=True, capture_output=True, check=False,
        )

    def _prepare_temp_root(self, temp):
        """Isolated root that still carries the real config contracts."""
        root = Path(temp.name)
        shutil.copytree(ROOT / "doc" / "config", root / "doc" / "config")
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


if __name__ == "__main__":
    unittest.main()
