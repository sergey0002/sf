"""Contract tests for status, release and branch fields in task.json.

These guard the scaffold/validation invariant: ``task init``/``task new`` must
produce a card that passes ``task validate`` immediately, and the release fields
must be mandatory and well formed.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "doc/tools/arch/__main__.py"


class TaskFieldsContractTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)
        (self.root / "doc").mkdir()
        shutil.copytree(ROOT / "doc/config", self.root / "doc/config")
        (self.root / "doc/tasks").mkdir()
        (self.root / "doc/architecture").mkdir()
        shutil.copytree(
            ROOT / "doc/architecture/schemas", self.root / "doc/architecture/schemas"
        )
        (self.root / "doc/config/task-registry.json").write_text(
            json.dumps({"schema_version": 1, "tasks": []}), encoding="utf-8"
        )

    def tearDown(self):
        self._temp.cleanup()

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, str(CLI), "--root", str(self.root), *args],
            text=True, capture_output=True, check=False,
        )

    def _new_card(self):
        result = self.cli("task", "new", "--title", "Field check", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)["data"]
        path = self.root / data["task_json"]
        return data["task_key"], path, json.loads(path.read_text(encoding="utf-8"))

    def _write(self, path, card):
        path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_new_card_is_valid_with_release_defaults(self):
        key, path, card = self._new_card()
        self.assertEqual(card["status"], "open")
        self.assertEqual(card["branch"], f"bugfix/{key}")
        self.assertEqual(card["release_branch"], "main")
        self.assertEqual(card["target_release"], "0.1.0")
        valid = self.cli("task", "validate", key)
        self.assertEqual(valid.returncode, 0, valid.stderr)

    def test_invalid_status_is_rejected(self):
        key, path, card = self._new_card()
        card["status"] = "invalid_status"
        self._write(path, card)
        result = self.cli("task", "validate", key)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("status must be one of", result.stderr)

    def test_paused_status_is_accepted(self):
        key, path, card = self._new_card()
        card["status"] = "paused"
        self._write(path, card)
        result = self.cli("task", "validate", key)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unset_branch_is_rejected(self):
        key, path, card = self._new_card()
        card["branch"] = "unset"
        self._write(path, card)
        result = self.cli("task", "validate", key)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("branch must be set", result.stderr)

    def test_malformed_branch_is_rejected(self):
        key, path, card = self._new_card()
        card["branch"] = "bad branch name!"
        self._write(path, card)
        result = self.cli("task", "validate", key)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("branch must be a valid git branch name", result.stderr)

    def test_unset_target_release_is_rejected(self):
        key, path, card = self._new_card()
        card["target_release"] = "unset"
        self._write(path, card)
        result = self.cli("task", "validate", key)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("target_release must be set", result.stderr)

    def test_subtask_inherits_parent_branch_and_release(self):
        key, _, parent = self._new_card()
        result = self.cli(
            "task", "decompose", key,
            "--subtask-id", "0001", "--subtask-title", "Child slice",
            "--subtask-type", "refactor",
            "--subtask-flow", "standard-implementation",
            "--subtask-complexity", "low",
            "--subtask-estimate", "1",
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        child_path = self.root / f"doc/tasks/{key}/subtasks/0001/task.json"
        child = json.loads(child_path.read_text(encoding="utf-8"))
        self.assertEqual(child["branch"], parent["branch"])
        self.assertEqual(child["release_branch"], parent["release_branch"])
        self.assertEqual(child["target_release"], parent["target_release"])
        valid = self.cli("task", "subtask", "validate", key, "0001")
        self.assertEqual(valid.returncode, 0, valid.stderr)


if __name__ == "__main__":
    unittest.main()
