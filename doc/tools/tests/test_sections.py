import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arch.sections import (  # noqa: E402
    anchor_exists,
    find_section,
    parse_sections,
    section_map,
    slugify,
    split_frontmatter,
)


BODY = """# Title {#top}

Intro line.

## Checks {#checks}

CHECK-SENTINEL

### Nested

NESTED-SENTINEL

## Neighbor

NEIGHBOR-SENTINEL

```text
## Fake {#fake}
FAKE-SENTINEL
```

## Закрытие задачи

CYRILLIC-SENTINEL
"""


class SectionParsingTests(unittest.TestCase):
    def test_parses_headings_outside_fences_with_ranges(self):
        sections = parse_sections(BODY)
        self.assertEqual([item.anchor for item in sections],
                         ["top", "checks", "nested", "neighbor", "закрытие-задачи"])
        checks = find_section(sections, "checks")[0]
        self.assertIsNotNone(checks)
        self.assertTrue(checks.stable)
        self.assertEqual(checks.heading_path, ("Title", "Checks"))
        self.assertIn("CHECK-SENTINEL", checks.text)
        self.assertIn("NESTED-SENTINEL", checks.text)
        self.assertNotIn("NEIGHBOR-SENTINEL", checks.text)
        nested = find_section(sections, "nested")[0]
        self.assertNotIn("NEIGHBOR-SENTINEL", nested.text)

    def test_ignores_anchors_inside_code_fences(self):
        sections = parse_sections(BODY)
        self.assertFalse(anchor_exists(sections, "fake"))
        self.assertNotIn("FAKE-SENTINEL", "".join(item.text for item in sections if item.anchor == "checks"))

    def test_explicit_anchor_precedence_and_slug_fallback(self):
        sections = parse_sections(BODY)
        self.assertEqual(find_section(sections, "checks")[0].title, "Checks")
        self.assertEqual(find_section(sections, "закрытие-задачи")[0].anchor_kind, "slug")
        self.assertFalse(find_section(sections, "закрытие-задачи")[0].stable)
        self.assertIsNone(find_section(sections, "missing")[0])

    def test_duplicate_explicit_anchors_are_ambiguous(self):
        body = "## One {#same}\nA\n\n## Two {#same}\nB\n"
        section, problem = find_section(parse_sections(body), "same")
        self.assertIsNone(section)
        self.assertEqual(problem, "ambiguous")
        _, duplicates = section_map(body)
        self.assertEqual(duplicates, ["same"])

    def test_slugify_is_deterministic_for_russian_and_punctuation(self):
        self.assertEqual(slugify("Закрытие задачи"), "закрытие-задачи")
        self.assertEqual(slugify("A / B (C)"), "a-b-c")
        self.assertEqual(slugify("!!!"), "section")

    def test_split_frontmatter_reports_body_offset(self):
        text = "---\nid: X\n---\n\n# Title\n"
        frontmatter, body, offset = split_frontmatter(text)
        self.assertEqual(frontmatter, "id: X")
        self.assertEqual(body, "\n# Title\n")
        self.assertEqual(offset, 3)


if __name__ == "__main__":
    unittest.main()
