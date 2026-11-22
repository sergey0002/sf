import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arch import ArchitectureStore
from arch.cli.commands.registry import SimpleCommandRegistry
from arch.fs_atomic import atomic_write_text
from arch.project_config import DEFAULT_ROOTS, load_project_config


class ArchitectureStoreTests(unittest.TestCase):
    def make_root(self, related=None, link="ok.md"):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        docs = root / "doc" / "architecture"
        (docs / "schemas").mkdir(parents=True)
        (docs / "schemas" / "document.schema.json").write_text(Path(__file__).parents[2].joinpath("architecture/schemas/document.schema.json").read_text(), encoding="utf-8")
        (docs / "schemas" / "index.schema.json").write_text(Path(__file__).parents[2].joinpath("architecture/schemas/index.schema.json").read_text(), encoding="utf-8")
        (docs / "ok.md").write_text("---\nid: DOC_TARGET\ntype: note\ntitle: Target\nsummary: Target page\nstatus: draft\ndomain: system\n---\ntarget\n", encoding="utf-8")
        rel = json.dumps(related if related is not None else [])
        (docs / "sample.md").write_text(
            "---\nid: DOC_SAMPLE\ntype: view\ntitle: Sample\nsummary: Example\nstatus: draft\ndomain: system\nrelated: " + rel + "\n---\n\n[Target](" + link + ")\n",
            encoding="utf-8",
        )
        return root

    def make_project_config(self, root):
        for key, relative in DEFAULT_ROOTS.items():
            if key not in {"index", "reference"}:
                (root / relative).mkdir(parents=True, exist_ok=True)
        (root / "doc/config/paths.yaml").write_text("roots: {}\n", encoding="utf-8")
        config, errors = load_project_config(root)
        self.assertEqual(errors, [])
        return config

    def test_parses_and_generates_deterministic_index(self):
        root = self.make_root()
        project_config = self.make_project_config(root)
        store = ArchitectureStore(project_config)
        index, errors = store.build_index()
        self.assertEqual(errors, [])
        self.assertIn("DOC_SAMPLE", [item["id"] for item in index["documents"]])
        store.write_index(index)
        self.assertEqual(store.validate(), [])

    def test_rejects_duplicate_yaml_keys(self):
        root = self.make_root()
        project_config = self.make_project_config(root)
        file = root / "doc/architecture/sample.md"
        file.write_text("---\nid: DOC-sample\ntype: view\ntype: flow\ntitle: Sample\nsummary: Example\nstatus: draft\ndomain: system\n---\n", encoding="utf-8")
        _, errors = ArchitectureStore(project_config).load_documents()
        self.assertTrue(any("duplicate key" in error for error in errors))

    def test_rejects_broken_local_link(self):
        root = self.make_root(link="missing.md")
        project_config = self.make_project_config(root)
        errors = ArchitectureStore(project_config).validate(check_index=False)
        self.assertTrue(any("broken local link" in error for error in errors))

    def test_rejects_unknown_related_id(self):
        root = self.make_root(related=["DOC-missing"])
        project_config = self.make_project_config(root)
        errors = ArchitectureStore(project_config).validate(check_index=False)
        self.assertTrue(any("unresolved related id" in error for error in errors))

    def test_index_check_detects_stale_or_missing_index(self):
        root = self.make_root()
        project_config = self.make_project_config(root)
        self.assertTrue(any("missing" in err for err in ArchitectureStore(project_config).validate()))


class CliInfrastructureTests(unittest.TestCase):
    def test_atomic_write_replaces_content_and_leaves_no_temp_file(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        target = Path(temp.name) / "task.json"
        atomic_write_text(target, "first\n")
        atomic_write_text(target, "second\n")
        self.assertEqual(target.read_text(encoding="utf-8"), "second\n")
        leftovers = [p.name for p in target.parent.iterdir() if p.name.startswith(".task.json.")]
        self.assertEqual(leftovers, [])

    def test_registry_rejects_duplicate_command_names(self):
        class First:
            name = "duplicate"

        class Second:
            name = "duplicate"

        registry = SimpleCommandRegistry()
        registry.register(First)
        with self.assertRaises(ValueError):
            registry.register(Second)
        self.assertEqual(registry.names(), ["duplicate"])


class PackagingContractTests(unittest.TestCase):
    def test_pyproject_uses_single_source_version_and_console_script(self):
        import re

        from arch import __version__

        root = Path(__file__).resolve().parents[3]
        text = (root / "pyproject.toml").read_text(encoding="utf-8")
        self.assertRegex(text, r'(?m)^dynamic\s*=\s*\["version"\]$')
        self.assertIsNone(re.search(r'^version\s*=\s*"', text, re.MULTILINE))
        self.assertRegex(text, r'(?m)^version\s*=\s*\{\s*attr\s*=\s*"arch\.__version__"\s*\}$')
        self.assertTrue(__version__)
        self.assertRegex(text, r'(?m)^arch\s*=\s*"arch\.cli\.app:run"$')
        self.assertIn("PyYAML>=6.0,<7", text)
        self.assertIn("jsonschema>=4.20,<5", text)


if __name__ == "__main__":
    unittest.main()
