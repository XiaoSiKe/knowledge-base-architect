from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    path = ROOT / "scripts" / "validate_style_profile.py"
    spec = importlib.util.spec_from_file_location("style_profile_under_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StyleProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.profile, errors = cls.module.load_json(ROOT / "assets" / "style-profile.template.json")
        assert not errors

    def test_template_is_valid(self):
        self.assertEqual(self.module.validate_profile(self.profile), [])

    def test_profile_requires_default_scope(self):
        profile = copy.deepcopy(self.profile)
        profile["scopes"] = {"zhihu": profile["scopes"]["default"]}
        errors = self.module.validate_profile(profile)
        self.assertTrue(any("包含 default" in error for error in errors))

    def test_unconfirmed_evidence_is_rejected(self):
        profile = copy.deepcopy(self.profile)
        profile["evidence"][0]["confirmed"] = False
        errors = self.module.validate_profile(profile)
        self.assertTrue(any("confirmed" in error for error in errors))

    def test_profile_requires_confirmed_evidence(self):
        profile = copy.deepcopy(self.profile)
        profile["evidence"] = []
        errors = self.module.validate_profile(profile)
        self.assertTrue(any("evidence" in error for error in errors))

    def test_raw_sample_content_is_rejected(self):
        profile = copy.deepcopy(self.profile)
        profile["evidence"][0]["raw_text"] = "不应写入持久档案的完整样本"
        errors = self.module.validate_profile(profile)
        self.assertTrue(any("原始内容字段" in error for error in errors))

    def test_revision_must_be_positive_integer(self):
        profile = copy.deepcopy(self.profile)
        profile["revision"] = 0
        errors = self.module.validate_profile(profile)
        self.assertTrue(any("revision" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
