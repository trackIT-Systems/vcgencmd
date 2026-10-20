# SPDX-FileCopyrightText: 2026 Jonas Höchst <hoechst@trackit.systems>
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any

from .readings import ReadingGroup

CSV_HEADER = ["timestamp", "group", "key", "value", "unit"]


def format_timestamp(when: datetime | None = None) -> str:
    if when is None:
        when = datetime.now().astimezone()
    return when.isoformat()


def _unit_for(group: ReadingGroup, key: str) -> str | None:
    if group.unit is not None:
        return group.unit
    if group.name == "pmic":
        if key.endswith("_V"):
            return "V"
        if key.endswith("_A"):
            return "A"
    return None


def flatten_groups(groups: list[ReadingGroup]) -> list[tuple[str, str, Any, str | None]]:
    rows: list[tuple[str, str, Any, str | None]] = []

    for group in groups:
        for key, value in group.values.items():
            rows.append((group.name, key, value, _unit_for(group, key)))

    return rows


def readings_to_dict(groups: list[ReadingGroup]) -> dict[str, Any]:
    return {group.name: dict(group.values) for group in groups}


def format_header(fmt: str) -> str:
    if fmt == "csv":
        return ",".join(CSV_HEADER)
    return ""


def _format_grouped_text(
    label: str,
    keys: list[str],
    values: dict[str, Any],
    unit: str | None,
) -> list[str]:
    if not keys:
        return []

    suffix = f" ({unit})" if unit else ""
    lines = [f"{label}{suffix}:"]
    max_len = max(len(key) for key in keys)
    for key in keys:
        lines.append(f"  {key}{' ' * (max_len - len(key))}: {values[key]}")
    return lines


def _format_text_body(groups: list[ReadingGroup]) -> str:
    sections: list[str] = []

    for group in groups:
        label = "PMIC" if group.name == "pmic" else group.label
        unit = None if group.name == "pmic" else group.unit
        keys = sorted(group.values.keys())
        sections.extend(_format_grouped_text(label, keys, group.values, unit))

    return "\n".join(sections)


def format_sample(
    fmt: str,
    groups: list[ReadingGroup],
    timestamp: str,
    *,
    include_header: bool = False,
    streaming: bool = False,
) -> str:
    if fmt == "text":
        body = _format_text_body(groups)
        if streaming:
            return f"timestamp: {timestamp}\n{body}"
        return body

    if fmt == "json":
        payload = readings_to_dict(groups)
        if streaming:
            line = {"timestamp": timestamp, "readings": payload}
            return json.dumps(line, separators=(",", ":"))

        return json.dumps(payload, indent=2)

    if fmt == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        if include_header:
            writer.writerow(CSV_HEADER)
        for group_name, key, value, unit in flatten_groups(groups):
            writer.writerow([timestamp, group_name, key, value, unit or ""])
        return buffer.getvalue().rstrip("\n")

    raise ValueError(f"unsupported format: {fmt}")


def format_once(fmt: str, groups: list[ReadingGroup], timestamp: str | None = None) -> str:
    ts = timestamp or format_timestamp()
    if fmt == "csv":
        return format_sample(fmt, groups, ts, include_header=True, streaming=False)
    return format_sample(fmt, groups, ts, include_header=False, streaming=False)
