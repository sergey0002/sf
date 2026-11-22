import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arch.session_audit import (  # noqa: E402
    digest_session,
    find_sessions,
    open_db,
    resolve_db_path,
    session_events,
)

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / "doc/tools/arch/__main__.py"


def _part(part_id, message_id, session_id, created, payload):
    return (
        part_id,
        message_id,
        session_id,
        created,
        json.dumps(payload, ensure_ascii=False),
    )


def build_db(directory: Path, root: Path) -> Path:
    db_path = directory / "kilo.db"
    db = sqlite3.connect(db_path)
    db.executescript(
        """
        CREATE TABLE session (
            id TEXT PRIMARY KEY, project_id TEXT, parent_id TEXT, title TEXT,
            directory TEXT, version TEXT, agent TEXT, model TEXT, cost REAL,
            tokens_input INTEGER, tokens_output INTEGER, tokens_reasoning INTEGER,
            tokens_cache_read INTEGER, tokens_cache_write INTEGER,
            time_created INTEGER, time_updated INTEGER
        );
        CREATE TABLE message (
            id TEXT PRIMARY KEY, session_id TEXT, time_created INTEGER, data TEXT
        );
        CREATE TABLE part (
            id TEXT PRIMARY KEY, message_id TEXT, session_id TEXT,
            time_created INTEGER, data TEXT
        );
        """
    )
    session_id = "ses_test"
    db.execute(
        "INSERT INTO session VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            session_id,
            "prj_test",
            None,
            "Test session",
            str(root),
            "7.8.32",
            "code",
            json.dumps({"id": "test-model", "providerID": "test-provider"}),
            0.0,
            100,
            50,
            5,
            10,
            0,
            1000,
            4000,
        ),
    )
    messages = [
        ("msg_u", 1000, {"role": "user"}),
        (
            "msg_a1",
            2000,
            {
                "role": "assistant",
                "modelID": "test-model",
                "providerID": "test-provider",
                "tokens": {"input": 10, "output": 5, "reasoning": 1, "cache": {"read": 2, "write": 0}, "total": 16},
            },
        ),
        (
            "msg_a2",
            3000,
            {
                "role": "assistant",
                "modelID": "test-model",
                "providerID": "test-provider",
                "tokens": {"input": 20, "output": 10, "reasoning": 2, "cache": {"read": 4, "write": 0}, "total": 32},
            },
        ),
        (
            "msg_a3",
            4000,
            {
                "role": "assistant",
                "modelID": "test-model",
                "providerID": "test-provider",
                "tokens": {"input": 30, "output": 15, "reasoning": 3, "cache": {"read": 6, "write": 0}, "total": 48},
            },
        ),
    ]
    for message_id, created, payload in messages:
        db.execute(
            "INSERT INTO message VALUES (?,?,?,?)",
            (message_id, session_id, created, json.dumps(payload, ensure_ascii=False)),
        )

    parts = [
        _part("prt_u", "msg_u", session_id, 1000, {"type": "text", "text": "читай ридми и выполни задачу UI-0001"}),
        _part(
            "prt_skill",
            "msg_a1",
            session_id,
            2001,
            {
                "type": "tool",
                "tool": "skill",
                "state": {
                    "status": "completed",
                    "input": {"name": "kilo-session-audit"},
                    "output": "skill body",
                    "metadata": {},
                    "time": {"start": 2000, "end": 2001},
                },
            },
        ),
        _part(
            "prt_flow",
            "msg_a1",
            session_id,
            2002,
            {
                "type": "tool",
                "tool": "read",
                "state": {
                    "status": "completed",
                    "input": {"filePath": str(root / "doc/config/task-conf/types/feature/flows/standard-implementation/prompt.md")},
                    "output": "flow prompt",
                    "metadata": {},
                },
            },
        ),
        _part(
            "prt_rule",
            "msg_a1",
            session_id,
            2003,
            {
                "type": "tool",
                "tool": "read",
                "state": {
                    "status": "completed",
                    "input": {"filePath": str(root / "doc/AGENTS.md")},
                    "output": "rules",
                    "metadata": {},
                },
            },
        ),
        _part(
            "prt_task",
            "msg_a1",
            session_id,
            2004,
            {
                "type": "tool",
                "tool": "read",
                "state": {
                    "status": "completed",
                    "input": {"filePath": str(root / "doc/tasks/UI-0001/stage1/plan.md")},
                    "output": "plan",
                    "metadata": {},
                },
            },
        ),
        _part(
            "prt_arch",
            "msg_a1",
            session_id,
            2005,
            {
                "type": "tool",
                "tool": "read",
                "state": {
                    "status": "completed",
                    "input": {"filePath": str(root / "doc/architecture/sample.md")},
                    "output": "arch",
                    "metadata": {},
                },
            },
        ),
        _part(
            "prt_diag",
            "msg_a1",
            session_id,
            2006,
            {
                "type": "tool",
                "tool": "bash",
                "state": {
                    "status": "completed",
                    "input": {"command": "arch task diagnose UI-0001 --json"},
                    "output": "{}",
                    "metadata": {"exit": 0},
                },
            },
        ),
        _part(
            "prt_edit",
            "msg_a2",
            session_id,
            3001,
            {
                "type": "tool",
                "tool": "edit",
                "state": {
                    "status": "completed",
                    "input": {"filePath": str(root / "doc/tools/arch/session_audit.py")},
                    "output": "edited",
                    "metadata": {},
                },
            },
        ),
        _part(
            "prt_fail",
            "msg_a2",
            session_id,
            3002,
            {
                "type": "tool",
                "tool": "bash",
                "state": {
                    "status": "completed",
                    "input": {"command": "bash doc/tests/run.sh --brief"},
                    "output": "ERROR",
                    "metadata": {"exit": 1},
                },
            },
        ),
        _part(
            "prt_rule_again",
            "msg_a2",
            session_id,
            3003,
            {
                "type": "tool",
                "tool": "read",
                "state": {
                    "status": "completed",
                    "input": {"filePath": str(root / "doc/AGENTS.md")},
                    "output": "rules",
                    "metadata": {},
                },
            },
        ),
        _part("prt_final", "msg_a3", session_id, 4001, {"type": "text", "text": "Готово"}),
    ]
    db.executemany("INSERT INTO part VALUES (?,?,?,?,?)", parts)
    db.commit()
    db.close()
    return db_path


class SessionAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "doc/architecture").mkdir(parents=True)
        (self.root / "doc/architecture/sample.md").write_text(
            "---\nid: SYS-test\ntype: system\ntitle: Sample\nsummary: Test\n"
            "status: draft\ndomain: system\n---\n\nBody\n",
            encoding="utf-8",
        )
        (self.root / "doc/AGENTS.md").write_text("# Rules\n", encoding="utf-8")
        self.db_path = build_db(self.root, self.root)

    def test_find_sessions_by_dialogue_substring(self):
        db = open_db(self.db_path)
        self.addCleanup(db.close)
        result = find_sessions(db, "ридми", directory=self.root)
        self.assertEqual(len(result["sessions"]), 1)
        item = result["sessions"][0]
        self.assertEqual(item["id"], "ses_test")
        self.assertEqual(item["match_count"], 1)
        self.assertEqual(item["first_match"]["role"], "user")

    def test_digest_labels_tools_and_phases(self):
        db = open_db(self.db_path)
        self.addCleanup(db.close)
        data = digest_session(db, "ses_test", root=self.root)

        self.assertEqual(data["session"]["message_count"], 4)
        self.assertEqual(data["session"]["tool_call_count"], 9)
        self.assertEqual(data["session"]["tokens"]["input"], 60)
        self.assertEqual(data["session"]["tokens"]["cache_read"], 12)

        skills = {item["id"]: item for item in data["markers"]["skills"]}
        self.assertEqual(skills["kilo-session-audit"]["via"], ["skill-tool"])

        flows = {(item["type"], item["flow"]) for item in data["markers"]["flows"]}
        self.assertIn(("feature", "standard-implementation"), flows)
        self.assertEqual(data["markers"]["tasks"][0]["task_key"], "UI-0001")
        self.assertEqual(data["markers"]["stages"][0]["stage"], "stage1")
        self.assertIn("doc/AGENTS.md", {item["path"] for item in data["markers"]["rules"]})
        self.assertIn(
            "SYS-test",
            {item.get("doc_id") for item in data["markers"]["architecture"]},
        )

        cli = {item["command"]: item for item in data["markers"]["cli"]}
        self.assertEqual(cli["task diagnose"]["success"], 1)

        tools = data["stats"]["tools"]
        self.assertEqual(tools["total"], 9)
        self.assertEqual(tools["by_tool"]["bash"]["calls"], 2)
        self.assertEqual(tools["by_tool"]["bash"]["failure"], 1)
        self.assertEqual(tools["by_tool"]["read"]["calls"], 5)

        kinds = {item["kind"] for item in data["anomalies"]}
        self.assertIn("failed_tool", kinds)
        self.assertIn("repeated_read", kinds)

        activities = [item["activity"] for item in data["phases"]]
        self.assertIn("explore", activities)
        self.assertIn("edit", activities)
        self.assertIn("verify", activities)

        self.assertEqual(data["dialog"]["user_messages"][0]["text"], "читай ридми и выполни задачу UI-0001")
        self.assertEqual(data["dialog"]["final_answer"]["text"], "Готово")
        self.assertEqual(data["label_index"]["skill:kilo-session-audit"]["count"], 1)

    def test_events_drill_into_one_message(self):
        db = open_db(self.db_path)
        self.addCleanup(db.close)
        data = session_events(db, "ses_test", message_id="msg_a2")
        self.assertEqual(data["total"], 3)
        self.assertEqual({item["message_id"] for item in data["events"]}, {"msg_a2"})
        tools = [item for item in data["events"] if item["kind"] == "tool"]
        self.assertEqual(tools[0]["tool"], "edit")
        self.assertEqual(tools[1]["outcome"], "failure")

    def test_cli_find_and_digest(self):
        find = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "session",
                "find",
                "--match",
                "ридми",
                "--db",
                str(self.db_path),
                "--all-projects",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(find.returncode, 0, find.stderr)
        payload = json.loads(find.stdout)
        self.assertEqual(payload["data"]["sessions"][0]["id"], "ses_test")

        digest = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "session",
                "digest",
                "ses_test",
                "--db",
                str(self.db_path),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(digest.returncode, 0, digest.stderr)
        payload = json.loads(digest.stdout)
        self.assertEqual(payload["data"]["session"]["id"], "ses_test")
        self.assertIn("markers", payload["data"])

    def test_resolve_db_path_prefers_environment(self):
        previous = os.environ.get("KILO_AUDIT_DB")
        os.environ["KILO_AUDIT_DB"] = "/tmp/custom-kilo.db"
        try:
            self.assertEqual(resolve_db_path(), Path("/tmp/custom-kilo.db"))
        finally:
            if previous is None:
                del os.environ["KILO_AUDIT_DB"]
            else:
                os.environ["KILO_AUDIT_DB"] = previous


if __name__ == "__main__":
    unittest.main()
