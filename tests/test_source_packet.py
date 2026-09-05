from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    path = ROOT / "scripts" / "validate_source_packet.py"
    spec = importlib.util.spec_from_file_location("source_packet_under_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SourcePacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.packet, errors = cls.module.load_json(ROOT / "assets" / "source-packet.template.json")
        assert not errors

    def test_template_is_valid_and_covers_required_questions(self):
        self.assertEqual(self.module.validate_packet(self.packet), [])
        self.assertEqual(self.module.coverage_gaps(self.packet), [])

    def test_missing_source_reference_is_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["items"][0]["source_id"] = "missing-source"
        errors = self.module.validate_packet(packet)
        self.assertTrue(any("不存在的来源" in error for error in errors))

    def test_missing_question_reference_is_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["items"][0]["question_ids"] = ["missing-question"]
        errors = self.module.validate_packet(packet)
        self.assertTrue(any("不存在的问题" in error for error in errors))

    def test_uncertain_item_does_not_cover_required_question(self):
        packet = copy.deepcopy(self.packet)
        packet["items"][0]["status"] = "uncertain"
        gaps = self.module.coverage_gaps(packet)
        self.assertTrue(any("必答问题" in gap for gap in gaps))

    def test_unresolved_conflict_is_a_coverage_gap(self):
        packet = copy.deepcopy(self.packet)
        second_item = copy.deepcopy(packet["items"][0])
        second_item["id"] = "i2"
        second_item["status"] = "conflict"
        packet["items"].append(second_item)
        packet["conflicts"] = [
            {
                "id": "c1",
                "item_ids": ["i1", "i2"],
                "status": "unresolved",
                "resolution": "",
            }
        ]
        self.assertEqual(self.module.validate_packet(packet), [])
        gaps = self.module.coverage_gaps(packet)
        self.assertTrue(any("未解决冲突" in gap for gap in gaps))


if __name__ == "__main__":
    unittest.main()
