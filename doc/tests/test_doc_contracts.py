import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "doc/tools/arch/__main__.py"


def _run(root, *args):
    return subprocess.run(
        [sys.executable, str(CLI), "--root", str(root), *args],
        text=True, capture_output=True, check=False,
    )


def _doc(doc_id, title, status="accepted", summary="Fixture document", body="", **extra):
    fields = {
        "id": doc_id, "type": "integration", "title": title, "summary": summary,
        "status": status, "domain": "system",
    }
    fields.update(extra)
    frontmatter = yaml.safe_dump(fields, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{frontmatter}\n---\n{body}"


class DocContractFixture(unittest.TestCase):
    def make_root(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        architecture = root / "doc/architecture"
        (architecture / "schemas").mkdir(parents=True)
        for name in ("document.schema.json", "index.schema.json"):
            shutil.copyfile(ROOT / "doc/architecture/schemas" / name, architecture / "schemas" / name)
        for relative in ("doc/tasks", "doc/config/task-conf", "doc/skills", "doc/config", "data"):
            (root / relative).mkdir(parents=True, exist_ok=True)
        config = {
            "doc_root": "doc",
            "roots": {
                "architecture": "doc/architecture",
                "tasks": "doc/tasks",
                "schemas": "doc/architecture/schemas",
                "task_conf": "doc/config/task-conf",
                "skills": "doc/skills",
                "reference": "data",
                "index": "index.json",
                "config": "doc/config",
            },
            "project": {"document_types": ["integration"]},
        }
        (root / "doc/config/paths.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
        self.write_doc(root, "rule.md", _doc(
            "RULE-close", "Close rule", body=(
                "# Close rule {#top}\n\n"
                "## Checks {#checks}\n\nCHECK-SENTINEL\nThe close rule requires evidence.\n\n"
                "### Nested detail\n\nNESTED-SENTINEL\n\n"
                "## Neighbor\n\nNEIGHBOR-SENTINEL\n\n"
                "```text\n## Fake {#fake}\nFAKE-SENTINEL\n```\n"
            ), aliases=["закрытие"],
        ))
        self.write_doc(root, "other.md", _doc(
            "OTHER", "Other document", body=(
                "# Other\n\n## Links {#links}\n\n"
                "[ok](rule.md#checks)\n\n[self](#links)\n\n"
                "Mentions RULE-close and закрытие.\n"
            ),
        ))
        self.write_doc(root, "draft.md", _doc(
            "DRAFT-one", "Draft document", status="draft",
            body="# Draft\n\nDRAFT-SENTINEL\n",
        ))
        self.write_doc(root, "archived.md", _doc(
            "ARCHIVED-one", "Archived document", status="superseded",
            body="# Archived\n\nARCHIVED-SENTINEL\n",
        ))
        (root / "data/ref.md").write_text(_doc(
            "REF-one", "Reference page", body="# Reference\n\nREFERENCE-SENTINEL\n",
        ), encoding="utf-8")
        self.write_task(root)
        return root

    def write_doc(self, root, name, content):
        path = root / "doc/architecture" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_task(self, root, *, missing_ref=False, passing=False):
        task = {
            "task_key": "UI-9000",
            "acceptance_policy": "case-coverage-v1",
            "acceptance_criteria": ["AC-1: Close requires evidence."],
            "related_docs": ["RULE-close"],
            "project_context_refs": ["doc/architecture/rule.md#checks"],
            "related_tests": [{"test_id": "t1", "location": "check.sh", "command": "true"}],
        }
        if missing_ref:
            task["project_context_refs"].append("doc/architecture/missing.md")
        directory = root / "doc/tasks/UI-9000"
        (directory / "stage1").mkdir(parents=True, exist_ok=True)
        (directory / "task.json").write_text(json.dumps(task, ensure_ascii=False), encoding="utf-8")
        (directory / "stage1/plan.md").write_text("# Plan\n", encoding="utf-8")
        check = root / "check.sh"
        check.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        snapshot = [{"path": "check.sh", "sha256": hashlib.sha256(check.read_bytes()).hexdigest()}]
        verification = {
            "task_key": "UI-9000",
            "stage_id": "stage1",
            "planned_checks": [{"id": "CASE-1", "covers": ["AC-1"], "expected": "Close requires evidence."}],
            "checks": [],
            "snapshot_files": snapshot if passing else [],
        }
        if passing:
            verification["checks"] = [{
                "command": "true", "exit_code": 0, "cases": ["CASE-1"],
                "result": "Command exited with status 0.",
            }]
            verification["status"] = "passed"
            verification["checked_revision"] = "sha256:fixture"
        (directory / "stage1/verification.json").write_text(
            json.dumps(verification, ensure_ascii=False), encoding="utf-8",
        )
        return directory


class AddressableSectionTests(DocContractFixture):
    def test_read_returns_exact_section_and_survives_move_and_rename(self):
        root = self.make_root()
        before = _run(root, "docs", "read", "RULE-close#checks", "--json")
        self.assertEqual(before.returncode, 0, before.stderr)
        first = json.loads(before.stdout)["data"]
        self.assertEqual(first["path"], "doc/architecture/rule.md")
        self.assertEqual(first["anchor_kind"], "explicit")
        self.assertTrue(first["stable"])
        self.assertIn("CHECK-SENTINEL", first["content"])
        self.assertIn("NESTED-SENTINEL", first["content"])
        self.assertNotIn("NEIGHBOR-SENTINEL", first["content"])

        moved = root / "doc/architecture/moved/rule.md"
        moved.parent.mkdir()
        moved.write_text(_doc(
            "RULE-close", "Renamed close rule", body=(
                "# Renamed close rule\n\n## Checks {#checks}\n\nCHECK-SENTINEL\n"
                "The close rule requires evidence.\n\n## Neighbor\n\nNEIGHBOR-SENTINEL\n"
            ), aliases=["закрытие"],
        ), encoding="utf-8")
        (root / "doc/architecture/rule.md").unlink()
        after = _run(root, "docs", "read", "RULE-close#checks", "--json")
        self.assertEqual(after.returncode, 0, after.stderr)
        second = json.loads(after.stdout)["data"]
        self.assertEqual(second["path"], "doc/architecture/moved/rule.md")
        self.assertEqual(second["anchor"], "checks")
        self.assertNotEqual(second["sha256"], first["sha256"])
        self.assertNotIn("NEIGHBOR-SENTINEL", second["content"])

    def test_read_rejects_missing_ambiguous_and_oversized_sections(self):
        root = self.make_root()
        missing = _run(root, "docs", "read", "RULE-close#fake", "--json")
        self.assertEqual(missing.returncode, 1)
        self.assertIn("SECTION-NOT-FOUND", missing.stderr)
        self.assertEqual(missing.stdout, "")

        oversized = _run(root, "docs", "read", "RULE-close#checks", "--max-bytes", "10", "--json")
        self.assertEqual(oversized.returncode, 1)
        self.assertIn("SECTION-TOO-LARGE", oversized.stderr)
        self.assertEqual(oversized.stdout, "")

        self.write_doc(root, "dup.md", _doc(
            "DUP-one", "Duplicate anchors", body="## One {#same}\nA\n\n## Two {#same}\nB\n",
        ))
        ambiguous = _run(root, "docs", "read", "DUP-one#same", "--json")
        self.assertEqual(ambiguous.returncode, 1)
        self.assertIn("SECTION-AMBIGUOUS", ambiguous.stderr)

    def test_read_without_anchor_is_an_argument_error(self):
        root = self.make_root()
        result = _run(root, "docs", "read", "RULE-close", "--json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("read requires a section anchor", result.stderr)


class SearchTests(DocContractFixture):
    def test_exact_id_alias_limit_and_empty_result(self):
        root = self.make_root()
        exact = _run(root, "docs", "search", "RULE-close", "--json")
        self.assertEqual(exact.returncode, 0, exact.stderr)
        hits = json.loads(exact.stdout)["data"]["hits"]
        self.assertEqual(hits[0]["id"], "RULE-close")
        self.assertEqual(hits[0]["match"], "id")

        alias = _run(root, "docs", "search", "закрытие", "--json")
        self.assertEqual(alias.returncode, 0, alias.stderr)
        self.assertEqual(json.loads(alias.stdout)["data"]["hits"][0]["id"], "RULE-close")

        limited = _run(root, "docs", "search", "SENTINEL", "--limit", "1", "--json")
        self.assertEqual(limited.returncode, 0, limited.stderr)
        data = json.loads(limited.stdout)["data"]
        self.assertEqual(len(data["hits"]), 1)
        self.assertGreaterEqual(data["total_matched"], 1)

        empty = _run(root, "docs", "search", "no-such-term-anywhere", "--json")
        self.assertEqual(empty.returncode, 0, empty.stderr)
        self.assertEqual(json.loads(empty.stdout)["data"]["hits"], [])

    def test_archived_is_excluded_and_reference_needs_explicit_scope(self):
        root = self.make_root()
        archived = _run(root, "docs", "search", "ARCHIVED-SENTINEL", "--json")
        self.assertEqual(json.loads(archived.stdout)["data"]["hits"], [])
        included = _run(root, "docs", "search", "ARCHIVED-SENTINEL", "--include-archived", "--json")
        self.assertEqual(json.loads(included.stdout)["data"]["hits"][0]["id"], "ARCHIVED-one")

        reference = _run(root, "docs", "search", "REFERENCE-SENTINEL", "--json")
        self.assertEqual(json.loads(reference.stdout)["data"]["hits"], [])
        scoped = _run(root, "docs", "search", "REFERENCE-SENTINEL", "--scope", "reference", "--json")
        hits = json.loads(scoped.stdout)["data"]["hits"]
        self.assertEqual(hits[0]["source"], "reference")

    def test_draft_is_marked_but_searchable(self):
        root = self.make_root()
        result = _run(root, "docs", "search", "DRAFT-SENTINEL", "--json")
        hit = json.loads(result.stdout)["data"]["hits"][0]
        self.assertEqual(hit["id"], "DRAFT-one")
        self.assertEqual(hit["status"], "draft")


class CheckLinksTests(DocContractFixture):
    def test_reports_broken_anchor_link_and_escape(self):
        root = self.make_root()
        self.write_doc(root, "broken.md", _doc(
            "BROKEN-one", "Broken links", body=(
                "# Broken\n\n[bad](rule.md#missing-anchor)\n\n"
                "[escape](../../../../etc/passwd)\n\n"
                "```text\n[fake](missing.md)\n```\n"
            ),
        ))
        result = _run(root, "docs", "check-links", "--json")
        self.assertEqual(result.returncode, 1)
        incidents = json.loads(result.stdout)["data"]["incidents"]
        codes = {item["code"] for item in incidents}
        self.assertIn("DOC-ANCHOR", codes)
        self.assertIn("DOC-LINK", codes)
        messages = " ".join(item["message"] for item in incidents)
        self.assertIn("missing-anchor", messages)
        self.assertIn("escapes project root", messages)
        self.assertNotIn("fake", messages)

    def test_accepts_existing_anchor_and_slug_fallback(self):
        root = self.make_root()
        self.write_doc(root, "links.md", _doc(
            "LINKS-one", "Good links", body=(
                "# Links\n\n[stable](rule.md#checks)\n\n[slug](rule.md#neighbor)\n\n"
                "[self](#links)\n"
            ),
        ))
        result = _run(root, "docs", "check-links", "--json")
        self.assertEqual(result.returncode, 0, result.stdout)


class ContextTests(DocContractFixture):
    def test_context_uses_declared_links_and_reports_gaps(self):
        root = self.make_root()
        self.write_task(root, missing_ref=True)
        result = _run(root, "docs", "context", "--task", "UI-9000", "--case", "CASE-1", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)["data"]
        self.assertFalse(data["complete"])
        by_ref = {item["ref"]: item for item in data["items"]}
        rule = by_ref["RULE-close"]
        self.assertEqual(rule["anchor"], "checks")
        self.assertEqual(rule["declared_by"], ["project_context_refs", "related_docs"])
        self.assertEqual(rule["authority"], "contract")
        self.assertEqual(by_ref["doc/architecture/missing.md"]["state"], "missing")
        case = by_ref["CASE-1"]
        self.assertEqual(case["state"], "not_run")
        self.assertEqual(case["acceptance"], {"AC-1": "Close requires evidence."})
        self.assertEqual(case["evidence"]["state"], "not_run")

    def test_context_marks_passing_evidence_and_ignores_unrelated_text(self):
        root = self.make_root()
        self.write_task(root, passing=True)
        self.write_doc(root, "noise.md", _doc(
            "NOISE-one", "Noise", body="# Noise\n\nCHECK-SENTINEL close evidence\n",
        ))
        result = _run(root, "docs", "context", "--task", "UI-9000", "--case", "CASE-1", "--json")
        data = json.loads(result.stdout)["data"]
        self.assertTrue(data["complete"])
        self.assertNotIn("NOISE-one", [item.get("doc_id") for item in data["items"]])
        case = next(item for item in data["items"] if item["ref"] == "CASE-1")
        self.assertEqual(case["evidence"]["state"], "passed")
        self.assertEqual(case["evidence"]["snapshot_state"], "current")

    def test_context_snapshot_returns_only_delta(self):
        root = self.make_root()
        self.write_task(root, passing=True)
        first = _run(root, "docs", "context", "--task", "UI-9000", "--case", "CASE-1", "--json")
        self.assertEqual(first.returncode, 0, first.stderr)
        snapshot = root / "snapshot.json"
        snapshot.write_text(first.stdout, encoding="utf-8")

        rule = root / "doc/architecture/rule.md"
        rule.write_text(rule.read_text(encoding="utf-8").replace("CHECK-SENTINEL", "CHECK-CHANGED"),
                        encoding="utf-8")
        second = _run(root, "docs", "context", "--task", "UI-9000", "--case", "CASE-1",
                      "--since-snapshot", str(snapshot), "--json")
        self.assertEqual(second.returncode, 0, second.stderr)
        data = json.loads(second.stdout)["data"]
        self.assertIn("document:RULE-close", data["delta"]["changed"])
        self.assertEqual([item["ref"] for item in data["items"]], ["RULE-close"])

    def test_context_reports_unplanned_case_and_trims_to_budget(self):
        root = self.make_root()
        self.write_task(root, passing=True)
        missing = _run(root, "docs", "context", "--task", "UI-9000", "--case", "CASE-404", "--json")
        data = json.loads(missing.stdout)["data"]
        self.assertFalse(data["complete"])
        case = next(item for item in data["items"] if item["ref"] == "CASE-404")
        self.assertEqual(case["state"], "missing")

        trimmed = _run(root, "docs", "context", "--task", "UI-9000", "--case", "CASE-1",
                       "--max-bytes", "300", "--json")
        self.assertEqual(trimmed.returncode, 0, trimmed.stderr)
        payload = json.loads(trimmed.stdout)["data"]
        self.assertFalse(payload["complete"])
        self.assertTrue(payload["omitted"])

    def test_context_marks_stale_evidence_snapshot(self):
        root = self.make_root()
        self.write_task(root, passing=True)
        (root / "check.sh").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        result = _run(root, "docs", "context", "--task", "UI-9000", "--case", "CASE-1", "--json")
        data = json.loads(result.stdout)["data"]
        case = next(item for item in data["items"] if item["ref"] == "CASE-1")
        self.assertEqual(case["evidence"]["state"], "passed")
        self.assertEqual(case["evidence"]["snapshot_state"], "stale")
        self.assertEqual(case["evidence"]["stale_files"], ["check.sh"])

    def test_context_rejects_invalid_snapshot(self):
        root = self.make_root()
        snapshot = root / "snapshot.json"
        snapshot.write_text("{}", encoding="utf-8")
        result = _run(root, "docs", "context", "--task", "UI-9000",
                      "--since-snapshot", str(snapshot), "--json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid snapshot", result.stderr)


class ImpactTests(DocContractFixture):
    def _git(self, root, *args):
        return subprocess.run(
            ["git", "-C", str(root), "-c", "user.email=test@example.invalid",
             "-c", "user.name=Test", *args],
            text=True, capture_output=True, check=False,
        )

    def test_impact_reports_changed_section_and_declared_consumers(self):
        root = self.make_root()
        self.assertEqual(self._git(root, "init", "-q").returncode, 0)
        self.assertEqual(self._git(root, "add", "-A").returncode, 0)
        self.assertEqual(self._git(root, "commit", "-q", "-m", "base").returncode, 0)

        rule = root / "doc/architecture/rule.md"
        rule.write_text(
            rule.read_text(encoding="utf-8").replace("CHECK-SENTINEL", "CHECK-CHANGED"),
            encoding="utf-8",
        )
        self.write_doc(root, "new.md", _doc(
            "NEW-one", "New document", body="# New\n\n## Added {#added}\n\nNEW-SENTINEL\n",
        ))
        result = _run(root, "docs", "impact", "--since", "HEAD", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)["data"]
        changed = {item["path"]: item for item in data["changed_sections"]}
        self.assertIn("doc/architecture/rule.md", changed)
        anchors = [entry["anchor"] for entry in changed["doc/architecture/rule.md"]["changed"]]
        self.assertIn("checks", anchors)
        self.assertNotIn("neighbor", anchors)
        new_anchors = [entry["anchor"] for entry in changed["doc/architecture/new.md"]["added"]]
        self.assertIn("added", new_anchors)

        affected = {(item["kind"], item["id"], item["via"]) for item in data["affected"]}
        self.assertIn(("task", "UI-9000", "related_docs"), affected)
        self.assertIn(("document", "OTHER", "link"), affected)
        self.assertIn("NEW-one", data["unverified_coverage"])
        self.assertNotIn("RULE-close", data["unverified_coverage"])

        new_file = next(item for item in data["changed_files"]
                        if item["path"] == "doc/architecture/new.md")
        self.assertEqual(new_file["status"], "added")
        self.assertFalse(new_file["tracked"])

    def test_impact_rejects_unknown_revision(self):
        root = self.make_root()
        self.assertEqual(self._git(root, "init", "-q").returncode, 0)
        result = _run(root, "docs", "impact", "--since", "does-not-exist", "--json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown Git revision", result.stderr)


class CompatibilityTests(DocContractFixture):
    def test_existing_document_commands_still_work(self):
        root = self.make_root()
        self.assertEqual(_run(root, "list", "--json").returncode, 0)
        self.assertEqual(_run(root, "show", "RULE-close").returncode, 0)
        tree = _run(root, "docs", "tree")
        self.assertEqual(tree.returncode, 0, tree.stderr)
        self.assertEqual(json.loads(tree.stdout)["data"]["architecture_root"], "doc/architecture")
        self.assertEqual(_run(root, "index", "build").returncode, 0)


if __name__ == "__main__":
    unittest.main()
