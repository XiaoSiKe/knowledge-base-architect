#!/usr/bin/env python3
"""Validate persistent style profiles for knowledge-base-architect."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "schema_version",
    "profile_id",
    "language",
    "revision",
    "updated_at",
    "scopes",
    "evidence",
}
EVIDENCE_FIELDS = {"id", "kind", "reference", "observations", "confirmed"}
RAW_CONTENT_FIELDS = {"raw_text", "full_text", "content", "transcript"}


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_nonempty_string(item) for item in value)


def validate_profile(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["根节点必须是 JSON 对象"]

    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"缺少字段：{', '.join(missing)}")

    if data.get("schema_version") != 1:
        errors.append("schema_version 必须为 1")
    for field in ("profile_id", "language"):
        if not _nonempty_string(data.get(field)):
            errors.append(f"{field} 必须是非空字符串")

    revision = data.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        errors.append("revision 必须是大于等于 1 的整数")

    updated_at = data.get("updated_at")
    if not _nonempty_string(updated_at):
        errors.append("updated_at 必须是 ISO 日期字符串")
    else:
        try:
            date.fromisoformat(updated_at)
        except ValueError:
            errors.append("updated_at 必须使用 YYYY-MM-DD")

    scopes = data.get("scopes")
    if not isinstance(scopes, dict) or not scopes:
        errors.append("scopes 必须是非空对象")
    else:
        if "default" not in scopes:
            errors.append("scopes 必须包含 default")
        for scope_name, preferences in scopes.items():
            if not _nonempty_string(scope_name):
                errors.append("scope 名称必须是非空字符串")
                continue
            if not isinstance(preferences, dict) or not preferences:
                errors.append(f"scopes.{scope_name} 必须是非空对象")
                continue
            for key, value in preferences.items():
                if not _nonempty_string(key):
                    errors.append(f"scopes.{scope_name} 包含无效偏好名称")
                if not (_nonempty_string(value) or _string_list(value)):
                    errors.append(
                        f"scopes.{scope_name}.{key} 必须是非空字符串或非空字符串列表"
                    )

    evidence = data.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("evidence 必须是非空数组")
    else:
        seen_ids: set[str] = set()
        for index, item in enumerate(evidence):
            prefix = f"evidence[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} 必须是对象")
                continue
            missing_evidence = sorted(EVIDENCE_FIELDS - set(item))
            if missing_evidence:
                errors.append(f"{prefix} 缺少字段：{', '.join(missing_evidence)}")
            raw_fields = sorted(RAW_CONTENT_FIELDS & set(item))
            if raw_fields:
                errors.append(f"{prefix} 不得保存原始内容字段：{', '.join(raw_fields)}")
            evidence_id = item.get("id")
            if not _nonempty_string(evidence_id):
                errors.append(f"{prefix}.id 必须是非空字符串")
            elif evidence_id in seen_ids:
                errors.append(f"{prefix}.id 重复：{evidence_id}")
            else:
                seen_ids.add(evidence_id)
            for field in ("kind", "reference"):
                if not _nonempty_string(item.get(field)):
                    errors.append(f"{prefix}.{field} 必须是非空字符串")
            if not _string_list(item.get("observations")):
                errors.append(f"{prefix}.observations 必须是非空字符串列表")
            if item.get("confirmed") is not True:
                errors.append(f"{prefix}.confirmed 必须为 true")

    return errors


def load_json(path: Path) -> tuple[Any | None, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except FileNotFoundError:
        return None, ["文件不存在"]
    except json.JSONDecodeError as error:
        return None, [f"JSON 无效：第 {error.lineno} 行第 {error.colno} 列"]


def main() -> int:
    parser = argparse.ArgumentParser(description="验证持久风格档案")
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    failed = False
    for path in args.paths:
        data, load_errors = load_json(path)
        errors = load_errors if load_errors else validate_profile(data)
        print(f"{path}: {len(errors)} errors")
        for error in errors:
            print(f"  ERROR: {error}")
        failed = failed or bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
