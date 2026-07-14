# SPDX-FileCopyrightText: 2026 Jonas Höchst <hoechst@trackit.systems>
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .readings import ReadingGroup

CSV_HEADER = ["timestamp", "group", "key", "value", "unit"]


def format_timestamp(when: Optional[datetime] = None) -> str:
    if when is None:
        when = datetime.now().astimezone()
    return when.isoformat()


def _unit_for(group: ReadingGroup, key: str) -> Optional[str]:
    if group.unit is not None:
        return group.unit
    if group.name == "pmic":
        if key.endswith("_V"):
            return "V"
        if key.endswith("_A"):
            return "A"
    return None


def flatten_groups(groups: List[ReadingGroup]) -> List[Tuple[str, str, Any, Optional[str]]]:
    rows: List[Tuple[str, str, Any, Optional[str]]] = []

    for group in groups:
        for key, value in group.values.items():
            rows.append((group.name, key, value, _unit_for(group, key)))

    return rows


def readings_to_dict(groups: List[ReadingGroup]) -> Dict[str, Any]:
    return {group.name: dict(group.values) for group in groups}


def format_header(fmt: str) -> str:
    if fmt == "csv":
        return ",".join(CSV_HEADER)
    return ""


def _format_grouped_text(
    label: str,
    keys: List[str],
    values: Dict[str, Any],
    unit: Optional[str],
) -> List[str]:
    if not keys:
        return []

    suffix = " ({0})".format(unit) if unit else ""
    lines = ["{0}{1}:".format(label, suffix)]
    max_len = max(len(key) for key in keys)
    for key in keys:
        lines.append("  {0}{1}: {2}".format(
            key, " " * (max_len - len(key)), values[key]))
    return lines


def _format_text_body(groups: List[ReadingGroup]) -> str:
    sections: List[str] = []

    for group in groups:
        label = "PMIC" if group.name == "pmic" else group.label
        unit = None if group.name == "pmic" else group.unit
        keys = sorted(group.values.keys())
        sections.extend(_format_grouped_text(label, keys, group.values, unit))

    return "\n".join(sections)


def format_sample(
    fmt: str,
    groups: List[ReadingGroup],
    timestamp: str,
    *,
    include_header: bool = False,
    streaming: bool = False,
) -> str:
    if fmt == "text":
        body = _format_text_body(groups)
        if streaming:
            return "timestamp: {0}\n{1}".format(timestamp, body)
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

    raise ValueError("unsupported format: {0}".format(fmt))


def format_once(fmt: str, groups: List[ReadingGroup], timestamp: Optional[str] = None) -> str:
    ts = timestamp or format_timestamp()
    if fmt == "csv":
        return format_sample(fmt, groups, ts, include_header=True, streaming=False)
    return format_sample(fmt, groups, ts, include_header=False, streaming=False)
