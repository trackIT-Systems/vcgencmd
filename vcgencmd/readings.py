# SPDX-FileCopyrightText: 2026 Jonas Höchst <hoechst@trackit.systems>
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from . import vcgencmd


class PmicUnavailableError(Exception):
    pass


@dataclass
class ReadingGroup:
    name: str
    label: str
    unit: Optional[str]
    values: Dict[str, Any]


@dataclass
class Selection:
    """Telemetry group selection for the CLI.

    An empty ``groups`` dict means select every group and every source.
    Each key maps to ``None`` (all sources in the group) or a list of
    specific source names.
    """

    groups: Dict[str, Optional[List[str]]] = field(default_factory=dict)

    def wants_group(self, name: str) -> bool:
        if not self.groups:
            return True
        return name in self.groups

    def sources_for(self, name: str, all_sources: List[str]) -> List[str]:
        if not self.groups:
            return list(all_sources)
        selected = self.groups.get(name)
        if selected is None:
            return list(all_sources)
        return list(selected)

    def pmic_explicit(self) -> bool:
        return "pmic" in self.groups


@dataclass(frozen=True)
class GroupSpec:
    name: str
    label: str
    unit: Optional[str]
    sources: Callable[[], List[str]]
    read: Callable[..., Any]
    batched: bool = False


GROUPS: Dict[str, GroupSpec] = {
    "clocks": GroupSpec(
        name="clocks",
        label="Clock Frequencies",
        unit="Hz",
        sources=vcgencmd.frequency_sources,
        read=vcgencmd.measure_clock,
    ),
    "voltages": GroupSpec(
        name="voltages",
        label="Voltages",
        unit="V",
        sources=vcgencmd.voltage_sources,
        read=vcgencmd.measure_volts,
    ),
    "temperature": GroupSpec(
        name="temperature",
        label="Temperatures",
        unit="C",
        sources=lambda: ["soc"],
        read=lambda _src=None: vcgencmd.measure_temp(),
    ),
    "codecs": GroupSpec(
        name="codecs",
        label="Codecs Enabled",
        unit=None,
        sources=vcgencmd.codec_sources,
        read=vcgencmd.codec_enabled,
    ),
    "memory": GroupSpec(
        name="memory",
        label="Memory Allocation",
        unit="bytes",
        sources=vcgencmd.memory_sources,
        read=vcgencmd.get_mem,
    ),
    "throttled": GroupSpec(
        name="throttled",
        label="Throttled Status",
        unit=None,
        sources=vcgencmd.get_throttled_sources,
        read=vcgencmd.get_throttled,
        batched=True,
    ),
    "pmic": GroupSpec(
        name="pmic",
        label="PMIC",
        unit=None,
        sources=vcgencmd.pmic_sources,
        read=vcgencmd.measure_pmic_adc,
        batched=True,
    ),
}

GROUP_ORDER = [
    "clocks",
    "voltages",
    "temperature",
    "codecs",
    "memory",
    "throttled",
    "pmic",
]


def _collect_batched_throttled(spec: GroupSpec, sources: List[str]) -> ReadingGroup:
    readings = vcgencmd.get_throttled()
    values = {src: readings[src] for src in sources}
    return ReadingGroup(spec.name, spec.label, spec.unit, values)


def _collect_batched_pmic(spec: GroupSpec, sources: List[str]) -> ReadingGroup:
    from .vcgencmd import __kPmicAliases

    try:
        readings = vcgencmd.pmic_read_all()
    except Exception as exc:
        raise PmicUnavailableError(str(exc)) from exc

    values = {}
    for src in sources:
        canonical = __kPmicAliases.get(src, src)
        if canonical not in readings:
            raise PmicUnavailableError("unknown output for '{0}'".format(src))
        values[src] = readings[canonical]

    return ReadingGroup(spec.name, spec.label, spec.unit, values)


def _collect_simple(spec: GroupSpec, sources: List[str]) -> ReadingGroup:
    values = {}
    for src in sources:
        if spec.name == "temperature":
            values["soc"] = spec.read()
        else:
            values[src] = spec.read(src)
    return ReadingGroup(spec.name, spec.label, spec.unit, values)


def collect(selection: Selection) -> List[ReadingGroup]:
    results: List[ReadingGroup] = []

    for name in GROUP_ORDER:
        if not selection.wants_group(name):
            continue

        spec = GROUPS[name]
        sources = selection.sources_for(name, spec.sources())

        if not sources:
            continue

        if spec.batched and name == "throttled":
            results.append(_collect_batched_throttled(spec, sources))
        elif spec.batched and name == "pmic":
            try:
                results.append(_collect_batched_pmic(spec, sources))
            except PmicUnavailableError:
                if selection.pmic_explicit():
                    raise
        else:
            results.append(_collect_simple(spec, sources))

    return results
