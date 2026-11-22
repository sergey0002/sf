import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arch import ArchitectureStore


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

    def test_parses_and_generates_deterministic_index(self):
        root = self.make_root()
        store = ArchitectureStore(root)
        index, errors = store.build_index()
        self.assertEqual(errors, [])
        self.assertIn("DOC_SAMPLE", [item["id"] for item in index["documents"]])
        store.write_index(index)
        self.assertEqual(store.validate(), [])

    def test_rejects_duplicate_yaml_keys(self):
        root = self.make_root()
        file = root / "doc/architecture/sample.md"
        file.write_text("---\nid: DOC-sample\ntype: view\ntype: flow\ntitle: Sample\nsummary: Example\nstatus: draft\ndomain: system\n---\n", encoding="utf-8")
        _, errors = ArchitectureStore(root).load_documents()
        self.assertTrue(any("duplicate key" in error for error in errors))

    def test_rejects_broken_local_link(self):
        root = self.make_root(link="missing.md")
        errors = ArchitectureStore(root).validate(check_index=False)
        self.assertTrue(any("broken local link" in error for error in errors))

    def test_rejects_unknown_related_id(self):
        root = self.make_root(related=["DOC-missing"])
        errors = ArchitectureStore(root).validate(check_index=False)
        self.assertTrue(any("unresolved related id" in error for error in errors))

    def test_index_check_detects_stale_or_missing_index(self):
        root = self.make_root()
        self.assertTrue(any("missing" in err for err in ArchitectureStore(root).validate()))


if __name__ == "__main__":
    unittest.main()
