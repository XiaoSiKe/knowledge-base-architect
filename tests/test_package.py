from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_quality_module():
    path = ROOT / "scripts" / "quality_check.py"
    spec = importlib.util.spec_from_file_location("quality_check", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillPackageTests(unittest.TestCase):
    def test_frontmatter_matches_directory(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        match = re.search(r"^name:\s*([^\n]+)$", text, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1).strip(), ROOT.name)

    def test_all_local_markdown_links_exist(self):
        missing = []
        for path in ROOT.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                candidate = (path.parent / target.split("#", 1)[0]).resolve()
                if not candidate.exists():
                    missing.append(f"{path.relative_to(ROOT)} -> {target}")
        self.assertEqual(missing, [])

    def test_no_scaffold_placeholders(self):
        unfinished = []
        for path in ROOT.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".yaml"}:
                text = path.read_text(encoding="utf-8").lower()
                if "[todo" in text or "lorem ipsum" in text:
                    unfinished.append(str(path.relative_to(ROOT)))
        self.assertEqual(unfinished, [])

    def test_example_passes_quality_check(self):
        module = load_quality_module()
        errors, _warnings = module.audit(ROOT / "examples" / "github-beginner-result.md")
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
