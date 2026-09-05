#!/usr/bin/env python3
"""Validate source packets and required-question coverage."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


SOURCE_TYPES = {"image", "document", "webpage", "note", "transcript", "dataset", "other"}
ITEM_KINDS = {"fact", "opinion", "example", "inference", "step", "term", "risk"}
ITEM_STATUSES = {"clear", "verified", "uncertain", "conflict"}
ITEM_DECISIONS = {"use", "verify", "omit"}
CONFLICT_STATUSES = {"resolved", "unresolved"}


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _unique_id(
    item: Any, prefix: str, seen: set[str], errors: list[str]
) -> str | None:
    if not isinstance(item, dict):
        errors.append(f"{prefix} 必须是对象")
        return None
    item_id = item.get("id")
    if not _nonempty_string(item_id):
        errors.append(f"{prefix}.id 必须是非空字符串")
        return None
    if item_id in seen:
        errors.append(f"{prefix}.id 重复：{item_id}")
        return None
    seen.add(item_id)
    return item_id


def validate_packet(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["根节点必须是 JSON 对象"]
    if data.get("schema_version") != 1:
        errors.append("schema_version 必须为 1")
    if not _nonempty_string(data.get("packet_id")):
        errors.append("packet_id 必须是非空字符串")

    questions = data.get("questions")
    question_ids: set[str] = set()
    if not isinstance(questions, list) or not questions:
        errors.append("questions 必须是非空数组")
    else:
        for index, question in enumerate(questions):
            prefix = f"questions[{index}]"
            question_id = _unique_id(question, prefix, question_ids, errors)
            if question_id is None or not isinstance(question, dict):
                continue
            if not _nonempty_string(question.get("question")):
                errors.append(f"{prefix}.question 必须是非空字符串")
            if not isinstance(question.get("required"), bool):
                errors.append(f"{prefix}.required 必须是布尔值")

    sources = data.get("sources")
    source_ids: set[str] = set()
    if not isinstance(sources, list) or not sources:
        errors.append("sources 必须是非空数组")
    else:
        for index, source in enumerate(sources):
            prefix = f"sources[{index}]"
            source_id = _unique_id(source, prefix, source_ids, errors)
            if source_id is None or not isinstance(source, dict):
                continue
            if source.get("type") not in SOURCE_TYPES:
                errors.append(f"{prefix}.type 不受支持")
            for field in ("title", "location"):
                if not _nonempty_string(source.get(field)):
                    errors.append(f"{prefix}.{field} 必须是非空字符串")
            captured_at = source.get("captured_at")
            if not _nonempty_string(captured_at):
                errors.append(f"{prefix}.captured_at 必须是 ISO 日期字符串")
            else:
                try:
                    date.fromisoformat(captured_at)
                except ValueError:
                    errors.append(f"{prefix}.captured_at 必须使用 YYYY-MM-DD")

    items = data.get("items")
    item_ids: set[str] = set()
    if not isinstance(items, list) or not items:
        errors.append("items 必须是非空数组")
    else:
        for index, item in enumerate(items):
            prefix = f"items[{index}]"
            item_id = _unique_id(item, prefix, item_ids, errors)
            if item_id is None or not isinstance(item, dict):
                continue
            if item.get("source_id") not in source_ids:
                errors.append(f"{prefix}.source_id 指向不存在的来源")
            for field in ("locator", "summary"):
                if not _nonempty_string(item.get(field)):
                    errors.append(f"{prefix}.{field} 必须是非空字符串")
            if item.get("kind") not in ITEM_KINDS:
                errors.append(f"{prefix}.kind 不受支持")
            if item.get("status") not in ITEM_STATUSES:
                errors.append(f"{prefix}.status 不受支持")
            if item.get("decision") not in ITEM_DECISIONS:
                errors.append(f"{prefix}.decision 不受支持")
            linked_questions = item.get("question_ids")
            if not isinstance(linked_questions, list) or not linked_questions:
                errors.append(f"{prefix}.question_ids 必须是非空数组")
            else:
                for question_id in linked_questions:
                    if question_id not in question_ids:
                        errors.append(f"{prefix}.question_ids 指向不存在的问题：{question_id}")

    conflicts = data.get("conflicts")
    conflict_ids: set[str] = set()
    if not isinstance(conflicts, list):
        errors.append("conflicts 必须是数组")
    else:
        for index, conflict in enumerate(conflicts):
            prefix = f"conflicts[{index}]"
            conflict_id = _unique_id(conflict, prefix, conflict_ids, errors)
            if conflict_id is None or not isinstance(conflict, dict):
                continue
            linked_items = conflict.get("item_ids")
            if not isinstance(linked_items, list) or len(linked_items) < 2:
                errors.append(f"{prefix}.item_ids 至少包含两个信息项")
            else:
                for item_id in linked_items:
                    if item_id not in item_ids:
                        errors.append(f"{prefix}.item_ids 指向不存在的信息项：{item_id}")
            status = conflict.get("status")
            if status not in CONFLICT_STATUSES:
                errors.append(f"{prefix}.status 不受支持")
            resolution = conflict.get("resolution")
            if status == "resolved" and not _nonempty_string(resolution):
                errors.append(f"{prefix}.resolution 在 resolved 状态下不能为空")
            if status == "unresolved" and resolution not in (None, ""):
                errors.append(f"{prefix}.resolution 在 unresolved 状态下应为空")

    return errors


def coverage_gaps(data: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    usable_by_question: dict[str, int] = {}
    for item in data.get("items", []):
        if item.get("decision") != "use" or item.get("status") not in {"clear", "verified"}:
            continue
        for question_id in item.get("question_ids", []):
            usable_by_question[question_id] = usable_by_question.get(question_id, 0) + 1

    for question in data.get("questions", []):
        if question.get("required") and not usable_by_question.get(question.get("id"), 0):
            gaps.append(f"必答问题没有可用证据：{question.get('id')}")

    for conflict in data.get("conflicts", []):
        if conflict.get("status") == "unresolved":
            gaps.append(f"存在未解决冲突：{conflict.get('id')}")
    return gaps


def load_json(path: Path) -> tuple[Any | None, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except FileNotFoundError:
        return None, ["文件不存在"]
    except json.JSONDecodeError as error:
        return None, [f"JSON 无效：第 {error.lineno} 行第 {error.colno} 列"]


def main() -> int:
    parser = argparse.ArgumentParser(description="验证长资料来源包")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--coverage", action="store_true", help="同时检查必答问题和冲突")
    args = parser.parse_args()

    failed = False
    for path in args.paths:
        data, load_errors = load_json(path)
        errors = load_errors if load_errors else validate_packet(data)
        gaps = [] if errors or not args.coverage else coverage_gaps(data)
        print(f"{path}: {len(errors)} errors, {len(gaps)} coverage gaps")
        for error in errors:
            print(f"  ERROR: {error}")
        for gap in gaps:
            print(f"  GAP: {gap}")
        failed = failed or bool(errors or gaps)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
